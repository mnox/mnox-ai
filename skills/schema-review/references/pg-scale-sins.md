# Lens: PostgreSQL Scalability Sins (decide-now-or-suffer)

The landmines that are invisible at small scale and catastrophic at large scale. Flag them NOW — they are brutally expensive to fix once the table is huge and live. Weight severity by **cost-to-fix-later**.

## Principles

- Use `bigint` for PKs and FKs from day one — `int4` (~2.1B) is reachable faster than you think, especially on high INSERT+DELETE churn (the sequence advances on delete too).
- Every UPDATE-heavy table needs its autovacuum tuned off the default 20% scale factor — the default is calibrated for small tables and silently wrong for large ones.
- A stale/abandoned replication slot pins the xmin horizon and lets bloat (and wraparound risk) grow unbounded — monitor slots.
- Long-running transactions are a **systemic** hazard: they block vacuum and accelerate XID consumption.
- Tables expected to grow into the hundreds of millions must have their **partition key chosen before any data exists** — retrofitting partitioning onto a TB-scale live table is multi-week, high-risk work.
- Every index multiplies write amplification linearly; each unnecessary index taxes every write.
- A single frequently-updated row (counter/aggregate) is a write-serialization bottleneck — it cannot scale without a redesign.
- No connection pooler (PgBouncer) is a deploy-time mistake; retrofitting requires app-side coordination.
- `fillfactor < 100` on high-update tables enables HOT updates and cuts index bloat — not premature optimization.

## Review checklist (detectable in schema/migration)

| Signal | Severity |
|---|---|
| `SERIAL` / `INT` / `INT4` PK or FK on any table with unbounded growth | 🔴 CRITICAL → require `bigint` |
| `INT4` PK on a high INSERT+DELETE churn table even if row count stays low | 🔴 CRITICAL (sequence still advances) |
| Large/growing table (time-series or tenant-scoped, →100M+ rows) with no `PARTITION BY` | 🟠 HIGH (require partition-key decision before it lands) |
| UPDATE/DELETE-heavy large table with no per-table `autovacuum_vacuum_scale_factor` override | 🟠 HIGH |
| App connecting directly to Postgres, no pooler | 🟠 HIGH |
| Frequently-updated single counter/aggregate row | 🟠 HIGH (hot-row contention) |
| Replication slot present — confirm it's monitored | 🟠 HIGH (stale slot → unbounded bloat) |
| `fillfactor = 100` (default) on a table with frequent non-indexed-column UPDATEs | 🟡 MEDIUM (set 70–80 for HOT) |
| `text`/`jsonb`/`bytea`/`varchar(>~500)` storing ~1–4KB values on a hot read path | 🟡 MEDIUM (TOAST cliff) |
| > 5 indexes on a write-heavy insert path | 🟡 MEDIUM (write amplification) |
| `PREPARED TRANSACTION` (2PC) usage — confirm `pg_prepared_xacts` is drained | 🟡 MEDIUM (orphaned 2PC blocks vacuum) |

## Named landmines

| # | Name | Signature | At-scale failure | Retrofit cost |
|---|---|---|---|---|
| L1 | **Integer PK exhaustion** | `id serial`/`int4` | `nextval` errors, all inserts fail, table read-only | `ALTER TYPE BIGINT` = ACCESS EXCLUSIVE rewrite; zero-downtime needs shadow-column migration |
| L2 | **MVCC bloat** | high churn + default 20% scale factor; rising `n_dead_tup` | Table grows 2–10× live size; scans traverse dead pages; writes slow | `VACUUM FULL` (full lock) or `pg_repack` (heavy) — a fire drill |
| L3 | **xmin horizon lock** | long txn / stale replication slot / orphan 2PC | Vacuum reclaims zero; bloat unbounded; slot pins horizon forever | App change to bound txns; dropping a slot is lossy (rebuild standby) |
| L4 | **XID wraparound** | `age(datfrozenxid)` → 2.1B | Emergency read-only mode; total write outage until `VACUUM FREEZE` | Offline/maintenance-window freeze; compounded by L2/L3 bloat |
| L5 | **TOAST medium-value cliff** | `text`/`jsonb` typically 1–4KB | Main-table pages bloat; seq scans read far more pages; non-obvious cause | Lower `toast_tuple_target` (new rows only) + repack, or vertical decomposition |
| L6 | **Hot-row contention** | one high-frequency-updated counter/aggregate row | Writers queue on a row lock; throughput ceilings below DB limits | Sharded counters or append+rollup; app change + data migration |
| L7 | **Unpartitioned grow-forever table** | time/tenant data, no `PARTITION BY`, →100M+ | Full scans without pruning; vacuum/analyze drag; retention deletes are slow batches not `DROP PARTITION` | No in-place `ALTER ... PARTITION BY`; full rebuild via logical replication / pg_partman — weeks |
| L8 | **Index write amplification** | >5 indexes on insert-heavy table; unused indexes | 1 logical write → N physical; page-split lock bursts; storage + scan drag | `DROP INDEX CONCURRENTLY` (safe but slow) |

## Severity quick map (weighted by cost-to-fix-later)

- 🔴 CRITICAL: integer PK exhaustion (L1); XID wraparound (L4); stale replication slot variant (L3)
- 🟠 HIGH: MVCC bloat / autovacuum behind (L2); long-txn xmin block (L3); hot-row contention (L6); unpartitioned grow-forever table (L7); no connection pooler
- 🟡 MEDIUM: TOAST medium-value cliff (L5); index write amplification (L8); default fillfactor on update-heavy table; 2PC management
- 🔵 LOW: missing `pg_stat_statements`/observability; isolated B-tree page splits; analyze staleness on static tables

## Sources

- [Crunchy Data — The integer at the end of the universe](https://www.crunchydata.com/blog/the-integer-at-the-end-of-the-universe-integer-overflow-in-postgres)
- [pganalyze — autovacuum, dead tuples & the xmin horizon](https://pganalyze.com/blog/5mins-postgres-autovacuum-dead-tuples-not-yet-removable-postgres-xmin-horizon) · [TOAST performance](https://pganalyze.com/blog/5mins-postgres-TOAST-performance)
- [Crunchy Data — managing transaction ID wraparound](https://www.crunchydata.com/blog/managing-transaction-id-wraparound-in-postgresql)
- [CYBERTEC — why VACUUM won't remove dead rows](https://www.cybertec-postgresql.com/en/reasons-why-vacuum-wont-remove-dead-rows/) · [HOT updates](https://www.cybertec-postgresql.com/en/hot-updates-in-postgresql-for-better-performance/)
- [Citus — debugging autovacuum: 13 tips](https://www.citusdata.com/blog/2022/07/28/debugging-postgres-autovacuum-problems-13-tips/)
- [PostgreSQL — TOAST](https://www.postgresql.org/docs/current/storage-toast.html) · [HOT](https://www.postgresql.org/docs/current/storage-hot.html)
- [AWS — migrating to partitioned tables on Aurora/RDS](https://aws.amazon.com/blogs/database/improve-performance-and-manageability-of-large-postgresql-tables-by-migrating-to-partitioned-tables-on-amazon-aurora-and-amazon-rds/)
- [Tiger Data — why more indexes eventually makes things worse](https://www.tigerdata.com/blog/why-adding-more-indexes-eventually-makes-things-worse)
