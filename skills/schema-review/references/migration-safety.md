# Lens: Schema Evolution & Migration Safety

Zero-downtime / online-DDL safety. Applies to any migration that runs against a live, populated table.

## Principles

- **Never run blocking DDL on a live table without `lock_timeout`.** Set a short `lock_timeout` (e.g. <2s) + retry, so a queued `ACCESS EXCLUSIVE` lock can't collapse the connection pool.
- `ACCESS EXCLUSIVE` conflicts with `ACCESS SHARE` (held by every plain `SELECT`). Queued DDL behind a long read stalls all traffic.
- **Expand first, contract later — across separate deploys.** The schema must stay compatible with the N-1 app version throughout rollout.
- **Decouple migration from backfill.** Never backfill in the same transaction as the DDL; never backfill in one long transaction. Batch (≤ ~10k rows), throttle, watch replication lag.
- Indexes and unique constraints → build `CONCURRENTLY` (Ecto: `@disable_ddl_transaction true` + `algorithm: :concurrently`; cannot run in a txn).
- FK and CHECK constraints → add `NOT VALID`, then `VALIDATE CONSTRAINT` in a **separate** migration (`VALIDATE` takes only `SHARE UPDATE EXCLUSIVE`).
- Column type changes have **no** safe single-statement path on a live table — use full expand-contract (add new col → dual-write → backfill → switch reads → drop old).
- `SET NOT NULL`: add `CHECK (col IS NOT NULL) NOT VALID` → `VALIDATE` → then `SET NOT NULL` (metadata-only on PG12+).
- App code must stop reading a column **before** it's dropped (ORMs cache attributes); drop in a later migration.
- PG11+ adds a column with a **constant** default instantly; a **volatile** default (`gen_random_uuid()`, `now()`) still rewrites the whole table.
- Migrations are atomic PRs — no app code, no tests, nothing else mixed in (a common migration-hygiene policy).

## Review checklist (detectable in a migration)

| Signal | Severity |
|---|---|
| `ALTER COLUMN ... TYPE` (non-trivial cast) on a populated table | 🔴 CRITICAL (full rewrite under ACCESS EXCLUSIVE) |
| `ADD COLUMN ... NOT NULL DEFAULT <volatile>` | 🔴 CRITICAL (table rewrite) |
| `ADD CONSTRAINT ... FOREIGN KEY` without `NOT VALID` | 🔴 CRITICAL (blocks writes on both tables during scan) |
| Any lock-acquiring DDL with no `lock_timeout` on a high-traffic table | 🔴 CRITICAL |
| Raw `execute("...")` containing DDL | 🔴 CRITICAL — flag for manual review (can't auto-analyze) |
| `CREATE INDEX` without `CONCURRENTLY` on a production table | 🟠 HIGH |
| `ADD ... UNIQUE` / unique constraint built inline (non-concurrent) | 🟠 HIGH |
| `SET NOT NULL` without a prior validated CHECK | 🟠 HIGH |
| `TRUNCATE` / `VACUUM FULL` / `CLUSTER` / non-concurrent `REINDEX` in a migration | 🟠 HIGH |
| `ADD CONSTRAINT ... CHECK` without `NOT VALID` | 🟠 HIGH |
| `RENAME COLUMN` / `RENAME TABLE` on an in-use object | 🟡 MEDIUM (breaks N-1 app) |
| `DROP COLUMN` without a prior code-deploy that stopped reading it | 🟡 MEDIUM |
| Backfill `UPDATE` in one transaction / not batched | 🟡 MEDIUM |
| `ADD CONSTRAINT ... NOT VALID` present but `VALIDATE` never follows | 🟡 MEDIUM (incomplete pattern) |
| Missing `lock_timeout` (advisory, no data-loss risk) | 🔵 LOW |

## Unsafe-operation catalog → safe alternative

| Unsafe | Why | Safe alternative |
|---|---|---|
| `ALTER COLUMN TYPE` | Full rewrite, ACCESS EXCLUSIVE | Expand-contract: new col → dual-write → backfill → switch reads → drop old |
| `ADD COLUMN NOT NULL DEFAULT <volatile>` | Per-row evaluation → rewrite | Nullable col → batch backfill → `CHECK NOT NULL NOT VALID` → VALIDATE → SET NOT NULL |
| `ADD FOREIGN KEY` (immediate) | Full scan, both tables locked | `... FOREIGN KEY ... NOT VALID` → deploy → `VALIDATE CONSTRAINT` next migration |
| `ADD CHECK` (immediate) | Full scan under ACCESS EXCLUSIVE | `... CHECK ... NOT VALID` → `VALIDATE CONSTRAINT` |
| `CREATE INDEX` (non-concurrent) | Blocks writes | `CREATE INDEX CONCURRENTLY` + `disable_ddl_transaction` |
| `ADD UNIQUE` (inline) | Builds blocking unique index | `CREATE UNIQUE INDEX CONCURRENTLY` → `ADD CONSTRAINT ... USING INDEX` |
| `SET NOT NULL` (direct) | Pre-PG12 full scan | `CHECK (col IS NOT NULL) NOT VALID` → VALIDATE → SET NOT NULL |
| `RENAME` column/table | Breaks N-1 app | Add new name → dual-write → migrate reads → drop old |
| `DROP COLUMN` (no code deploy first) | Stale ORM attribute cache | Stop reading in code → deploy → drop later |
| Backfill in one txn | Holds row locks table-wide | `disable_ddl_transaction`, batch ≤10k, sleep between |
| `TRUNCATE`/`VACUUM FULL`/`CLUSTER` | ACCESS EXCLUSIVE full lock | Batched `DELETE`; plain `VACUUM`; `REINDEX CONCURRENTLY` |

## Severity quick map

- 🔴 CRITICAL: `ALTER COLUMN TYPE` on large table; `NOT NULL DEFAULT <volatile>`; FK without `NOT VALID`; lock-acquiring DDL with no `lock_timeout` on hot table; unreviewed raw `execute` DDL
- 🟠 HIGH: non-concurrent `CREATE INDEX`/unique; `SET NOT NULL` without validated CHECK; `TRUNCATE`/`VACUUM FULL` in migration; `CHECK` without `NOT VALID`
- 🟡 MEDIUM: `RENAME` without expand-contract; `DROP COLUMN` without prior code deploy; un-batched backfill; `NOT VALID` with missing `VALIDATE`
- 🔵 LOW: missing `lock_timeout` advisory; non-concurrent index on a tiny/new table; demonstrably read-only `execute`

## Sources

- [strong_migrations (ankane) — the canonical unsafe-op catalog](https://github.com/ankane/strong_migrations)
- [Ecto.Migration — HexDocs](https://hexdocs.pm/ecto_sql/Ecto.Migration.html)
- [PostgreSQL — Explicit Locking](https://www.postgresql.org/docs/current/explicit-locking.html)
- [Xata — schema changes & the Postgres lock queue](https://xata.io/blog/migrations-and-exclusive-locks)
- [PostgresAI — zero-downtime migrations: lock_timeout & retries](https://postgres.ai/blog/20210923-zero-downtime-postgres-schema-migrations-lock-timeout-and-retries)
- [GoCardless — zero-downtime Postgres migrations, the hard parts](https://gocardless.com/blog/zero-downtime-postgres-migrations-the-hard-parts/)
- [Prisma — expand-and-contract pattern](https://www.prisma.io/dataguide/types/relational/expand-and-contract-pattern)
