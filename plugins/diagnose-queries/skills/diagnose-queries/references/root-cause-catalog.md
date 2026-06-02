# Slow-Query Root-Cause Catalog

Each row: the **signal** you observe → the **root cause** it points to → the **fix** →
how to **verify** the fix worked. The analyzer (`scripts/analyze_plan.py`) emits the
`signal` names in the first column.

## OLTP / PostgreSQL

| Signal (where seen) | Root cause | Fix | Verify |
|---|---|---|---|
| `row_misestimate` — est rows ≠ actual rows by orders of magnitude at the lowest node | Stale/insufficient statistics; correlated columns | `ANALYZE`; raise column STATISTICS; `CREATE STATISTICS` for correlated cols | Estimates track actuals in re-plan |
| `seqscan_high_discard` — Seq Scan with high Rows Removed by Filter on a big table | Missing/selective index | `CREATE INDEX CONCURRENTLY` on filter/join cols | Plan flips to Index/Bitmap Scan; buffers drop |
| `nestloop_high_loops` — Nested Loop with high `loops` over a large inner | Row underestimate made planner pick nested loop | Fix estimate first (ANALYZE/stats); index inner; `enable_nestloop=off` to confirm | Plan switches to Hash/Merge Join; time drops |
| `sort_spill_disk` — `Sort Method: external merge Disk` | `work_mem` too low for the sort volume | Raise `work_mem` (session/role); reduce sorted rows | `Sort Method: quicksort Memory` |
| `hash_spill_batches` — Hash `Batches > 1` | `work_mem` too low for the hash table | Raise `work_mem`; shrink hashed input | `Batches: 1` |
| `io_heavy` — many Shared Read Blocks vs hits | Working set doesn't fit cache, or scan too big | Index to avoid the scan; (last resort) more RAM/`shared_buffers` | `read` blocks drop |
| `ios_heap_fetches` — Index-Only Scan with Heap Fetches > 0 | Visibility map stale | `VACUUM <table>` | Heap Fetches → 0 |
| Non-sargable `Filter` on `func(col)` / `col::type` / `LIKE '%x'` | Predicate can't use a plain index | Rewrite sargable, or add expression index `((lower(col)))` | Index Scan reappears |
| Same statement fast then slow run-to-run | Plan flip / parameter sniffing (generic vs custom plan) | `plan_cache_mode`; ensure good stats; rewrite | Stable plan across params |
| `wait_event_type = 'Lock'` in pg_stat_activity; entries in pg_locks | Lock contention / blocking transaction | Shorten txns; fix lock ordering; cancel offender | Waits clear |
| High `n_dead_tup`; table/index far larger than live rows | Bloat; autovacuum behind | `VACUUM`/`REINDEX CONCURRENTLY`; tune autovacuum | Page count / buffers drop |
| Many sessions in pg_stat_activity; app waits but DB metrics fine | Connection-pool / pooler saturation (see observability ref) | Add/size PgBouncer; release connections faster | Pool wait queue ≈ 0 |

## Application / ORM layer (the most common *real* cause)

| Signal | Root cause | Fix | Verify |
|---|---|---|---|
| Trace shows dozens–hundreds of near-identical short DB spans in one request; one query in `pg_stat_statements` with huge `calls` and tiny mean | **N+1** — query issued per row of a parent result | Eager-load: Ecto `preload:` (in the query, not per-row); Rails `includes`; Django `select_related`/`prefetch_related` | `calls` collapses to ~1; span count drops |
| Wide rows, `SELECT *`, slow serialization | Over-fetching columns | Project only needed columns (`select:`) | Bytes/row + app time drop |
| `Repo.*` / AR call inside `Enum.map` / loop | Queries inside a loop | Batch into one `WHERE id IN (^ids)` | One query replaces N |
| Deep `OFFSET` pagination slowing on later pages | Offset re-scans skipped rows | Keyset/cursor pagination | Latency flat across pages |

**Ecto note:** Ecto never lazy-loads — accessing an unpreloaded assoc returns
`%Ecto.Association.NotLoaded{}`, not a query. So Ecto N+1 is always an *explicit* mistake
(missing `preload:`, or `Repo.preload`/`Repo.all` inside a comprehension), not silent.

## OLAP / Snowflake + dbt

Different failure modes — it's about **data scanned, memory, and pruning**, not indexes.
Tool is the **Query Profile**, not EXPLAIN.

| Signal (in Query Profile) | Root cause | Fix | Verify |
|---|---|---|---|
| `Bytes spilled to local storage` > 0 | Query exceeds warehouse memory | Size up the warehouse (more RAM/SSD per step); reduce data per step | Spill → 0 |
| `Bytes spilled to remote storage` > 0 | Severe memory shortfall (10x+ slowdown) | Size up warehouse; batch; project fewer columns; filter earlier | Remote spill → 0 |
| `Partitions scanned ≈ Partitions total` | Pruning failed — no clustering on the filter column, or non-sargable filter | `cluster_by` the filter column; push `WHERE` earlier/sargable | Partitions scanned ≪ total |
| Large `TableScan` / `Join` operator dominating time | Exploding join, row fan-out, over-projection | Project needed columns only; filter before join; fix join keys | Operator % of time drops |
| Hot `view` re-computed on every downstream read | Materialization choice | Convert dbt model `view` → `table` (+ `cluster_by`) or `incremental` | Recompute cost removed |

**dbt materialization is a first-class lever:** `view` (no storage, recomputes every read)
→ `table` (fast reads, full rebuild each run) → `incremental` (MERGE only new/changed rows).
Incremental gotcha: the MERGE can scan the whole target unless the partition/cluster column
is in the join predicate (enables dynamic pruning).
