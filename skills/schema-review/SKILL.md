---
name: schema-review
description: "Review database schemas AND in-code data structures for correctness, integrity, performance, scalability, evolvability, simplicity, and design quality. Audits Ecto schemas, Postgres DDL/migrations, dbt models, and application types (Elixir structs/typespecs, TypeScript types). Use when: '/schema-review', 'review this schema', 'review this migration', 'review this data model', 'is this schema sound', 'audit this table design', 'review these types', 'is this over-engineered', 'will this schema scale', 'data structure review', 'check this migration is safe'. Adaptive execution: single-pass for a handful of objects, parallel multi-agent fan-out when the review surface exceeds a few line items. Draft-only — never auto-posts."
---

# Schema / Data-Structures Review

A rigorous, multi-lens review engine for **persistence schemas** (Ecto, Postgres DDL, migrations, dbt models) and **in-code data structures** (Elixir structs/typespecs, TypeScript types, collection choices). It evaluates a target across seven lenses, scores findings by severity and confidence, and produces a draft findings report. It never posts anywhere on its own.

## Context-hygiene contract (read first)

This skill is an orchestration layer. The main thread must stay lean.

- **Do NOT** grep, glob, read large files, or trace the target schema directly in the main context.
- **DO** delegate all reading/analysis to sub-agents. The main thread holds only: the mode decision, sub-agent result summaries, and the final synthesized report.
- The ONE allowed exception: re-reading a specific table/column/type in the main context to **validate a CRITICAL or HIGH finding** before it lands in the report — high-severity claims require main-context verification of the full failure/attack chain.

## Input

Invoke as `/schema-review <target>`. The target may be:

- A migration file or directory (`.exs` Ecto migration, `.sql` DDL, dbt model `.sql`)
- An Ecto schema module, a Postgres `\d`/`pg_dump` schema, a dbt `schema.yml`
- A TypeScript/Elixir file or module defining domain types/structs
- A PR diff (`<owner>/<repo>#<number>` or a local branch — diff against the base)
- A design doc / proposal describing a schema or data model (review at design altitude)
- A directory or "the changes on this branch" (`git diff` vs base)

Derive a `<slug>` from the target (e.g. `attachments-migration`, `orders-schema`). Scratch work goes under `/tmp/schema-review-<slug>/`.

## Step 1 — Classify the target, detect dialect, pick lenses

Identify what kind of artifact the target is, then select the applicable review lenses. Not every lens applies to every target — running irrelevant lenses wastes context.

### 1a. Detect the target SQL dialect (do this BEFORE dispatch)

Determine two things and carry both into every dispatch:

- **Target dialect** — the database the schema is *meant for* in production: Postgres, MySQL, SQLite, Snowflake, or dialect-agnostic (a design doc with no committed engine).
- **Implementation dialect** — what the code in front of you actually uses *right now*.

**When implementation ≠ target dialect, that gap IS a primary review axis.** A canonical case: a SQLite POC whose canonical target is Postgres. Reviewing the SQLite DDL as-if-Postgres produces false positives (SQLite `INTEGER` PK is 64-bit; Postgres `int4` is not) — and missing the gap produces false negatives (the SQLite DDL will silently mistranslate `TEXT`-for-timestamp into a broken Postgres column). Lens agents MUST be told both dialects so they (a) review against the *target* dialect's rules and (b) flag every place the current implementation won't translate cleanly. Surface these as a consolidated "dialect-translation decide-now" list in the report.

| Target type | Applicable lenses |
|---|---|
| Postgres / Ecto migration | `migration-safety`, `relational-postgres`, `pg-scale-sins`, `conventions-and-security` |
| Ecto schema / Postgres DDL / table design | `relational-postgres`, `data-modeling`, `pg-scale-sins`, `simplification-taxonomy`, `conventions-and-security` |
| dbt model / warehouse table | `data-modeling` (dimensional), `simplification-taxonomy`, `conventions-and-security` |
| In-code types / structs (Elixir, TS) | `type-design`, `simplification-taxonomy` |
| Design doc / proposal | `data-modeling`, `simplification-taxonomy`, `relational-postgres`, `pg-scale-sins` (at design altitude) |

The seven lenses (each backed by a reference file in `references/`):

1. **`relational-postgres`** — normalization, keys, constraints, indexing, Postgres types, classic relational anti-patterns. → `references/relational-postgres.md`
2. **`migration-safety`** — zero-downtime / online-DDL safety, lock hazards, expand-contract, backfills. → `references/migration-safety.md`
3. **`data-modeling`** — DDD aggregates/boundaries (transactional) + Kimball dimensional / dbt layering (analytics) + data contracts. → `references/data-modeling.md`
4. **`type-design`** — make-illegal-states-unrepresentable, parse-don't-validate, ADTs, primitive obsession, collection/Big-O choice (Elixir + TS). → `references/type-design.md`
5. **`pg-scale-sins`** — int4 PK exhaustion, MVCC bloat, autovacuum/xmin, txid wraparound, TOAST, hot-row contention, partition-too-late. → `references/pg-scale-sins.md`
6. **`simplification-taxonomy`** — over-complication, over-normalization, lookup/junction sprawl, tree/taxonomy modeling, redundancy/drift. → `references/simplification-taxonomy.md`
7. **`conventions-and-security`** — naming/consistency, PII/PHI, tenant isolation (IDOR), audit columns, mass-assignment, documentation. → `references/conventions-and-security.md`

## Step 2 — Choose execution mode

Count the **discrete review objects** in the target (tables, migrations, schema modules, type definitions changed).

- **Single-pass** (default for small targets): the review surface is **a few line items or fewer** — roughly ≤ 3 discrete objects, a single focused migration, or one type module. One sub-agent loads the applicable reference files and walks every relevant checklist in one pass. Cheaper, lower latency, less context.
- **Multi-agent fan-out** (for larger targets): the review surface exceeds a few line items — > 3 objects, multiple tables, a broad PR diff, or a whole schema. Spawn **one sub-agent per applicable lens, in parallel**, each scoped to its reference file. Heavier but thorough; each agent stays expert and shallow-context.

When in doubt, state your object count and the resulting mode in one line, then proceed. If a single-pass review surfaces more complexity than expected, escalate to fan-out.

### Single-pass dispatch

Spawn one `general-purpose` sub-agent (model: sonnet) with this shape:

> You are a schema reviewer. Target: `<target>`. **Target dialect: `<dialect>`. Implementation dialect: `<impl-dialect>`** — review against the TARGET dialect's rules and flag every place the implementation won't translate cleanly. Read the target, then apply EVERY checklist in these reference files: `<absolute paths to the applicable references/*.md>` plus `references/severity-and-output.md`. For each violation, emit a finding in the exact format from `severity-and-output.md` (severity, confidence, location, problem, impact, fix, blocker). Do not invent findings — only flag conditions that actually match the checklists against the real target. Return the findings list as your final message, ordered by severity.

### Multi-agent fan-out dispatch

Spawn the applicable lens agents **in a single message, in parallel** (model: sonnet each). Each agent gets:

> You are the **<lens>** reviewer. Target: `<target>`. **Target dialect: `<dialect>`. Implementation dialect: `<impl-dialect>`** — review against the TARGET dialect and flag implementation-translation gaps. Your sole knowledge source is `references/<lens>.md` (read it) plus the finding format in `references/severity-and-output.md`. Apply only your lens's checklist + anti-patterns to the real target. Emit findings in the standard format. Flag only conditions that actually match — no speculative findings. Return your findings list ordered by severity as your final message.

Each agent returns a capped findings list (not file dumps). The main thread collects them.

## Step 3 — Validate high-severity findings

Before any CRITICAL or HIGH finding enters the report, **verify it in the main context** (the allowed context-hygiene exception): re-read the specific table/column/migration/type and confirm the full failure or attack chain is real, not a checklist false-positive. Demote or drop anything that doesn't survive verification. This is mandatory — unverified high-severity findings are the most expensive kind of false positive.

## Step 4 — Synthesize the report

### 4a. Cross-lens dedup pass (mandatory in fan-out mode)

Lenses overlap by design, so the same object will surface from multiple agents (e.g. an int PK flagged by both `relational-postgres` and `pg-scale-sins`; a missing tenant column flagged by `conventions-and-security`, `relational-postgres`, and `data-modeling`). Before scoring, collapse duplicates:

- **One object/defect → one finding**, citing every lens that flagged it (`_(lens: a, b, c)_`).
- **Take the highest severity** among the duplicates, but treat **multi-lens corroboration as a confidence signal** — a defect three lenses independently caught is rarely a false positive.
- Keep distinct *angles* on the same column separate (e.g. `_raw_record` as a **redundancy/drift** finding vs. `_raw_record` as a **TOAST/bloat** finding are two real findings, not a dup).

### 4b. Score

Compute a schema-health score: start at 100, subtract per the penalty table below.

| Severity | Penalty each | Meaning |
|---|---|---|
| 🔴 CRITICAL | −25 | Data corruption, security exploit, or irreversible/at-scale-fatal decision. Merge blocker. |
| 🟠 HIGH | −12 | Integrity/perf/evolvability defect that must be fixed before merge. |
| 🟡 MEDIUM | −5 | Design drift / compounding debt; fix or defer with a ticket. |
| 🔵 LOW | −2 | Convention/observability gap. Author's discretion. |
| ⚪ NITPICK | 0 | Cosmetic. Noted, not scored. |

Floor the score at 0. Lead the report with: score, mode used, lenses run, and a one-line verdict (e.g. `HARD BLOCK` if any CRITICAL, `REVIEW` if any HIGH, `RISKY` if only MEDIUM, `SAFE` otherwise).

### 4c. WIP / design-phase mode (suppress the punitive score)

If the target is a **design doc, a pre-implementation proposal, or an explicitly work-in-progress POC** — detect via: a design-doc/proposal target type, "not yet started" / "draft" / "WIP" language in the artifact, or an explicit user signal — the 0–100 score is misleading. A sound architecture mid-build will floor at 0 purely on decide-now items, which reads as "broken" when it isn't. In this mode:

- **Suppress the numeric score** (or render it `— (WIP, suppressed)`); the verdict becomes `DESIGN-PHASE — decide-now items` instead of `HARD BLOCK`.
- **Lead with severity counts + the consolidated decide-now list** (especially the dialect-translation table from Step 1a), not a grade.
- Add a one-line context note explaining *why* the score is suppressed, so the harshness isn't mistaken for a failing implementation.

This keeps the signal (what to fix before cutover) without the noise of a punitive grade on intentionally-unfinished work.

Write the report using `templates/findings-report.md` to:
- A PR diff target → `/tmp/schema-review-<repo>-<pr>.md` (draft PR comment; never auto-post)
- Any other target, if you want it durable → offer to save to `./schema-review-<slug>-<YYYY-MM-DD>.md`. Otherwise print to terminal.

## Output discipline

- **Draft-only. Never auto-post** to a PR, issue tracker, or chat. Surface the draft; the user decides.
- Findings state facts and impacts — **never mock or blame prior authors**, even casually.
- Recommendations are imperative and concrete ("Add `CREATE INDEX CONCURRENTLY ...`"), not hedged ("you might consider").
- **No local file paths in anything destined for external comms** — inline the DDL/snippet instead.

## Memory persistence

After a substantive review, OFFER (don't auto-run) to store durable findings to the memory graph via `/mem` — recurring anti-patterns in a repo, a schema-design decision and its rationale, or a confirmed at-scale landmine. Don't store one-off cosmetic nits.

## Failure modes to avoid

- **Don't run all seven lenses blindly** — classify the target first; irrelevant lenses produce noise and burn context.
- **Don't trust the checklist over the code** — a checklist match is a hypothesis; verify CRITICAL/HIGH against the real target before reporting.
- **Don't escalate severity to compensate for low confidence** — lower confidence lowers the severity floor. Label confidence explicitly.
- **Don't review in the main context** — delegate reading to sub-agents; only validation re-reads happen in main.
- **Don't auto-post anything.** Ever. Draft and surface.
- **Don't recommend a rewrite when a targeted fix suffices** — pragmatic, incremental corrections win; surface a structural pivot only when the schema is genuinely wrong for the requirement, and let the user choose.
