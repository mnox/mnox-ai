# PostgreSQL Diagnostic Toolkit

Copy-paste-ready SQL for diagnosing slow Postgres queries. Replace literal table/column
names where marked. Every snippet here is read-only unless flagged **(MUTATING)**.

## Capturing a plan worth analyzing

Always use `ANALYZE` + `BUFFERS` — plain `EXPLAIN` only shows estimates, and the
estimate-vs-actual gap is the single most diagnostic signal. Add `FORMAT JSON` to feed
`scripts/analyze_plan.py`.

```sql
-- session prep: report real I/O time in BUFFERS
SET track_io_timing = on;

-- the diagnostic form
EXPLAIN (ANALYZE, BUFFERS, VERBOSE, SETTINGS, FORMAT JSON)
SELECT ...;
```

**ANALYZE actually executes the query.** For writes or long-running statements, wrap them:

```sql
BEGIN;
EXPLAIN (ANALYZE, BUFFERS) UPDATE ...;
ROLLBACK;
```

Profile with the **real parameter values**, not the prepared template — plans are
parameter-sensitive.

To pipe straight into the analyzer:

```bash
psql -XqAt -d <db> -c "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) SELECT ..." \
  | uv run scripts/analyze_plan.py --pretty
```

## Finding the offender (aggregate, over time)

`pg_stat_statements` ranks normalized queries. **Order by total time, not mean** — a 5 ms
query run 2M times hurts more than a 2 s query run twice.

```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;  -- needs shared_preload_libraries

SELECT
  round(total_exec_time::numeric, 1)            AS total_ms,
  calls,
  round(mean_exec_time::numeric, 2)             AS mean_ms,
  round(100 * total_exec_time / sum(total_exec_time) OVER (), 1) AS pct_total,
  rows,
  round(100 * shared_blks_hit
        / nullif(shared_blks_hit + shared_blks_read, 0), 1) AS hit_pct,
  query
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;
```

Reset the counters to measure a fresh window: `SELECT pg_stat_statements_reset();`

## Live diagnosis (what's slow RIGHT NOW)

```sql
-- active queries, longest first, with what they're waiting on
SELECT pid,
       now() - query_start          AS duration,
       state,
       wait_event_type, wait_event,
       left(query, 120)             AS query
FROM pg_stat_activity
WHERE state <> 'idle'
ORDER BY duration DESC;
```

A non-null `wait_event_type` means the query is **waiting** (Lock, IO, …), not burning CPU.

### Blocking chains (who blocks whom)

```sql
SELECT blocked.pid          AS blocked_pid,
       left(blocked.query, 80)  AS blocked_query,
       blocking.pid         AS blocking_pid,
       left(blocking.query, 80) AS blocking_query
FROM pg_stat_activity blocked
JOIN pg_stat_activity blocking
  ON blocking.pid = ANY (pg_blocking_pids(blocked.pid))
WHERE blocked.wait_event_type = 'Lock';
```

### Cancel / kill **(MUTATING — incident mode only)**

```sql
SELECT pg_cancel_backend(<pid>);     -- gentle: cancels current query
SELECT pg_terminate_backend(<pid>);  -- hard: drops the whole connection
```

**Never kill a backend running a migration or long write mid-flight** — confirm the query
text first. Mitigate the safe target; if unsure, escalate rather than guess.

## Table / index health

```sql
-- seq-vs-index scan balance, dead tuples (bloat), stats freshness
SELECT relname,
       seq_scan, idx_scan,
       n_live_tup, n_dead_tup,
       last_analyze, last_autoanalyze, last_autovacuum
FROM pg_stat_user_tables
ORDER BY seq_scan DESC;
```

```sql
-- unused indexes (drop candidates — they cost writes for nothing)
SELECT s.relname AS table, s.indexrelname AS index,
       s.idx_scan, pg_size_pretty(pg_relation_size(s.indexrelid)) AS size
FROM pg_stat_user_indexes s
WHERE s.idx_scan = 0
  AND s.indexrelname NOT LIKE '%_pkey'
ORDER BY pg_relation_size(s.indexrelid) DESC;
```

```sql
-- confirm a specific index is actually being used after you add it
SELECT indexrelname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE relname = '<table>';
```

## Reading an EXPLAIN ANALYZE plan by hand

`scripts/analyze_plan.py` automates this, but when reading manually, look in this order:

1. **Estimated vs actual rows** — the lowest node where they diverge by orders of magnitude
   is the root cause. The planner's bad guess there cascades into every choice above it
   (cheap-looking Nested Loop that becomes catastrophic). Fix → `ANALYZE`.
2. **Loops** — when `loops=N`, the displayed time and rows are **per-loop averages**.
   Multiply by N for the true cost. A `0.003 ms` node with `loops=100000` is your hotspot.
3. **Rows Removed by Filter** — high count = scan-then-discard → missing/wrong index or a
   non-sargable predicate (`func(col)`, `col::type`, leading-wildcard `LIKE`).
4. **Buffers: shared hit vs read** — `hit` = cache (fast), `read` = disk (slow). High `read`
   on a hot query = working set doesn't fit cache or a scan is too big.
5. **Sort Method** — `quicksort Memory` good; `external merge Disk` = spilled, raise `work_mem`.
6. **Hash Batches** — `1` good; `>1` = spilled to disk, raise `work_mem`.
7. **Index-Only Scan Heap Fetches** — `>0` means visibility checks hit the heap → `VACUUM`.
8. Then, and only then, the **highest self-time node** = where to spend effort.

## Fix → verify pairs

| Fix | Command | Verify |
|-----|---------|--------|
| Add index | `CREATE INDEX CONCURRENTLY ... ;` **(MUTATING)** | Re-EXPLAIN shows Index/Bitmap Scan; `idx_scan` rises |
| Refresh stats | `ANALYZE <table>;` | Estimates now track actuals in the plan |
| Sharper stats | `ALTER TABLE t ALTER COLUMN c SET STATISTICS 1000; ANALYZE t;` | Estimate gap closes |
| Correlated cols | `CREATE STATISTICS ON (a, b) FROM t; ANALYZE t;` | Multi-col estimate improves |
| Sort/hash spill | `SET work_mem = '256MB';` (session/role) | Sort Method = quicksort Memory; Batches = 1 |
| Confirm join misfire | `SET enable_nestloop = off;` (test only) | Hash Join chosen, time drops → then fix via stats/index |
| Bloat | `VACUUM (ANALYZE) <table>;` **(MUTATING)** | Page count / buffers drop |

`CREATE INDEX CONCURRENTLY` and `VACUUM` are production-safe (no long table lock) but slow;
never run plain `CREATE INDEX` (locks writes) or `VACUUM FULL` (locks everything) on a hot
table without a maintenance window.
