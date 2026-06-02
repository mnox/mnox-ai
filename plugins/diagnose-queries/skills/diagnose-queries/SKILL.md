---
name: diagnose-queries
description: Use when a database query or query-backed endpoint is slow — this query is slow, the page takes forever, DB is pegged, find the slow queries, why is this endpoint slow, N+1 suspicion, query timeouts, high p99 latency, EXPLAIN or plan analysis, a slow Snowflake/dbt model, or a query that used to be fast. Routes to one of five diagnostic modes (analyze a known query, locate an unknown offender, triage a live incident, audit proactively, or chase a regression), runs the right toolkit (EXPLAIN ANALYZE, pg_stat_statements, pg_stat_activity, APM/DBM tracing, Snowflake Query Profile), and produces a root-caused fix with before/after verification.
---

# Diagnose Slow Queries

## Overview

A diagnostic playbook for slow database queries across Postgres (OLTP), the application/ORM
layer (N+1), and Snowflake/dbt (OLAP). It routes the request into one of five entry-point
modes, runs the matching procedure, and lands on a root cause with a verified fix — never a
guessed index.

## Quick Reference

| You're in this situation | Mode | Jump to |
|---|---|---|
| "Here's the SQL — make it fast" (have the statement) | **A · Known query** | the shared analyze subroutine |
| "Endpoint/page is slow, don't know which query" | **B · Locate offender** | observability funnel, then Mode A |
| "Production DB is pegged RIGHT NOW" | **C · Live incident** | mitigate-first, then RCA later |
| "Find the worst queries before they hurt" | **D · Proactive audit** | rank by total time |
| "It used to be fast — what changed?" | **E · Regression/drift** | diff against the past |

| Resource | Use for |
|---|---|
| `scripts/analyze_plan.py` | Parse `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` → ranked bottleneck findings |
| `references/postgres-toolkit.md` | Copy-paste SQL: capture plans, pg_stat_statements, live/lock queries, fix→verify pairs |
| `references/root-cause-catalog.md` | Signal → root cause → fix → verify, for OLTP, ORM, and Snowflake |
| `references/observability-funnel.md` | Trace → DBM → query: locating an unknown offender; the "app is slow" decision tree |

## Routing

Infer the mode from the request. The five modes map onto two axes: **time pressure**
(incident or not) and **whether the offending query is already known**.

- A concrete SQL statement or a plan was provided → **Mode A**.
- "Slow endpoint / page / request" with no specific query named → **Mode B** (which usually
  terminates by handing a query to Mode A).
- Words like "down", "pegged", "on fire", "everything is slow right now", timeouts in prod →
  **Mode C**. When in doubt between B and C, **time pressure wins**: treat as C.
- "Audit", "find the worst", "proactive", "before it hurts" → **Mode D**.
- "Used to be fast", "got slower", "since the deploy/migration", "degraded" → **Mode E**.

If genuinely ambiguous after reading the request, ask which mode applies (one question, the
five modes as options). Otherwise commit to the inferred mode and say which one.

Before diagnosing, know the engine: **Postgres** (default — full toolkit applies),
**Snowflake/dbt** (use the OLAP rows of the catalog + Query Profile, not EXPLAIN/indexes), or
ORM-level. If APM/DBM tracing is available (Datadog DBM, pganalyze, or similar), use it to
locate slow queries rather than guessing which statement is the offender.

---

## Mode A · Known query (the shared analyze subroutine)

Modes B and E end here. Goal: a root cause and a verified fix for one specific statement.

1. **Capture the plan with evidence.** Run `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` with the
   **real parameter values** (plans are param-sensitive). For writes/long queries, wrap in
   `BEGIN; ... ROLLBACK;`. See `references/postgres-toolkit.md`.
2. **Run the analyzer.** Pipe the JSON into `python3 scripts/analyze_plan.py --pretty` (or save
   to a file and pass the path). It ranks the bottleneck signals — row misestimates, seq-scan
   discards, nested-loop blowups, sort/hash spills, I/O-heavy nodes.
3. **Map signal → root cause → fix** via `references/root-cause-catalog.md`. Fix the *lowest*
   misestimating node first — its bad guess cascades upward.
4. **Sanity-check it's worth fixing.** Cross-reference `pg_stat_statements` total time. Don't
   burn effort on a query that runs once; do prioritize a cheap query run 10k×/min.
5. **Apply one fix in a non-prod clone**, re-run `EXPLAIN ANALYZE`, and **verify**: the plan
   actually changed (e.g. Seq Scan → Index Scan), estimates now track actuals, spills gone.
6. **Output:** before/after plans, the diagnosed root cause, the exact fix (index DDL /
   rewritten SQL / `ANALYZE`), and the measured improvement (ms + plan delta).

## Mode B · Locate the offender (unknown query behind a slow path)

1. **Pull the request's trace** (APM / DBM). Read the **time-in-DB vs time-in-app** split —
   see `references/observability-funnel.md`.
2. **Count queries per request first.** This is the fork: one 800 ms query vs 400 × 2 ms
   queries (N+1) are completely different problems.
   - **Swarm of near-identical short queries → N+1.** Fix at the ORM layer (eager-load /
     batch); see the ORM rows of `references/root-cause-catalog.md`. Indexing won't save you.
   - **One dominant query →** extract it and hand to **Mode A**.
3. Correlate by time window in `pg_stat_statements` / DBM top-queries to confirm the offender.
4. **Output:** the offending query *or* the named anti-pattern (N+1), with the DB-time
   breakdown that proves it, then the ORM fix or a Mode-A handoff.

## Mode C · Live incident (DB pegged right now)

**Mitigate first, diagnose later. Success = service restored, not query optimized.**

1. **Snapshot** `pg_stat_activity` — what's running, by whom, for how long, waiting on what
   (`references/postgres-toolkit.md`).
2. **Find the blocking chain** (`pg_blocking_pids`) — identify the head-of-line blocker.
3. **Decide kill vs wait.** `pg_cancel_backend(pid)` (gentle) → `pg_terminate_backend(pid)`
   (hard) **only when safe**. **Never kill a migration or long write mid-flight** — read the
   query text first. If unsure, escalate rather than guess (this is a mutating, hard-to-reverse
   action — get a human if the target isn't obviously safe).
4. **Relieve pressure:** throttle the source, set a `statement_timeout`, fail over to a
   replica, or scale — whatever restores service fastest.
5. **Stop when service is restored.** Capture evidence (plan, pg_stat_activity snapshot,
   timeline) and file a follow-up for real RCA (which becomes Mode A or E later).
6. **Output:** incident timeline, the killed/throttled culprit, restored-service
   confirmation, and the RCA follow-up note.

## Mode D · Proactive audit

1. `pg_stat_statements` ordered by **`total_exec_time`** (frequency × latency), not mean —
   high total is what hurts the system.
2. Scan cache-hit ratio and `seq_scan`-heavy / low-`idx_scan` tables; sweep for **unused
   indexes** (drop candidates — they tax every write) and missing-index candidates.
3. Triage the top-N into **Mode A** individually.
4. **Output:** a ranked hit-list (query, calls, total time, mean, hit %), plus index
   recommendations (add **and** drop), prioritized by blast radius.

## Mode E · Regression / drift ("it used to be fast")

The diagnostic question is **"what changed?"**, not "what's optimal?".

1. **Establish when it changed**; correlate to deploys, migrations, data-volume milestones,
   and last `ANALYZE`/`VACUUM` (`pg_stat_user_tables`).
2. **Compare the current plan to a known-good one** — plan flip? new Seq Scan? estimate drift
   from stale stats? Run the current plan through Mode A's analyzer.
3. Check for a **dropped/disabled index** (migration?), **parameter sniffing**, or
   **autovacuum falling behind**.
4. **Fix the cause of the change** (refresh stats, restore the index, fix autovacuum) — not
   just the symptom.
5. **Output:** the changed variable named ("stats stale since X" / "index dropped in
   migration Y" / "table crossed N rows"), the plan diff, and the targeted fix.

## Common Mistakes

### ❌ `EXPLAIN` without `ANALYZE`

**Problem:** Reading only the planner's estimates.

**Why it's wrong:** The estimate-vs-actual *gap* is the single most diagnostic signal — plain
`EXPLAIN` doesn't have actuals, so you lose it. (Caveat: `ANALYZE` actually runs the query —
wrap writes in `BEGIN; ... ROLLBACK;` and avoid it on prod under load.)

**Fix:** Always `EXPLAIN (ANALYZE, BUFFERS)`; add `FORMAT JSON` to feed `analyze_plan.py`.

### ❌ Adding an index without verifying it's used

**Problem:** Creating an index and declaring victory.

**Why it's wrong:** Wrong column order, low cardinality, or planner cost can leave a new index
unused — dead weight that *also* slows every write.

**Fix:** Re-run `EXPLAIN ANALYZE` and confirm the plan picks it up; check `idx_scan` rises in
`pg_stat_user_indexes`.

### ❌ Optimizing by mean latency, ignoring frequency

**Problem:** Chasing the query with the highest *mean* time.

**Why it's wrong:** A 5 ms query run 2M times dwarfs a 2 s query run twice. Effort spent on a
rarely-run query is wasted.

**Fix:** Always rank by **total** time (`pg_stat_statements.total_exec_time` / DBM total time).

### ❌ Indexing a symptom that's actually N+1

**Problem:** Treating "slow endpoint" as one slow query and adding indexes.

**Why it's wrong:** The endpoint is often 400 *fast* queries (N+1). No index fixes that — the
fix is eager-loading/batching at the ORM layer.

**Fix:** In Mode B, **count queries per request before** analyzing any single one.

### ❌ Diagnosing destructively on prod under load

**Problem:** Running `EXPLAIN ANALYZE` on a heavy write, or killing the wrong backend, during
an incident.

**Why it's wrong:** You can make the incident worse (e.g. terminating a running migration).

**Fix:** Mode C mitigates first and does real RCA on a clone. Read a backend's query text
before cancelling; escalate if the target isn't obviously safe to kill.

## Notes

- **Postgres is the default engine.** For Snowflake/dbt use the OLAP rows of the catalog and
  the Query Profile — indexes and EXPLAIN don't apply; it's about data scanned, memory
  spilling, and partition pruning.
- The analyzer needs `FORMAT JSON` output and real `ANALYZE` numbers; it refuses plain
  `EXPLAIN` and tells you why. It is stdlib-only — runs on the system `python3`.
- Prefer APM/DBM tooling (e.g. Datadog DBM top-queries, pganalyze, trace wait-events) to
  locate slow queries over manually guessing which statement is the offender.
- `CREATE INDEX CONCURRENTLY` / `VACUUM` are prod-safe but slow; plain `CREATE INDEX` and
  `VACUUM FULL` take heavy locks — never on a hot table without a maintenance window.
