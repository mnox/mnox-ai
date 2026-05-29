# Lens: Relational & PostgreSQL Schema Design

Normalization, keys, constraints, indexing, Postgres types, and classic relational anti-patterns.

## Principles

- Normalize to 3NF by default; denormalize only where a **measured** read bottleneck exists and the write/consistency cost is explicitly accepted.
- Every table needs a primary key. Surrogate (`bigint GENERATED ALWAYS AS IDENTITY`, or UUIDv7) for most cases; natural keys only when truly immutable and meaningfully unique.
- Prefer `bigint GENERATED ALWAYS AS IDENTITY` over `SERIAL` (deprecated; `GENERATED ALWAYS` blocks accidental manual overrides and the public-sequence-grant footgun).
- Prefer **UUIDv7 over UUIDv4** when UUIDs are needed — v4 is fully random → B-tree page splits, index bloat, WAL inflation; v7's time prefix restores sequential insert behavior.
- Every nullable column is a question. Default to `NOT NULL`; allow NULL only when absence is semantically meaningful, not "optional for now".
- Declare foreign keys **always**; index the referencing (child) side **always** — an unindexed FK seq-scans the child on every parent DELETE/UPDATE.
- Use `timestamptz`, never bare `timestamp` — bare drops the offset and silently corrupts across timezones.
- Never use `float`/`real`/`double precision` for money — use `numeric(p, s)` or integer cents (`bigint`). Avoid the locale-dependent `money` type too.
- Prefer `text` over `varchar(n)` — identical storage in Postgres; `varchar(n)` only when the length cap is a real business invariant.
- Encode invariants the type system can't with `CHECK` constraints (`price > 0`, valid states); use exclusion constraints for non-overlapping ranges. CHECK expressions must be immutable.
- FK `ON DELETE`: `CASCADE` for owned components, `RESTRICT` for independent/financial/audit entities, `SET NULL` for optional associations. Implicit `NO ACTION` is usually unintentional.
- JSONB for genuinely schemaless/dynamic data; normalized columns for anything queried, filtered, joined, or with a fixed key set. JSONB past TOAST (~2KB) degrades writes and gives the planner poor selectivity.
- Enum **types** freeze on add/remove; for tiny immutable sets use `CHECK (col IN (...))`, for growing sets use an FK lookup table.
- Index selection: B-tree default; GIN for full-text/JSONB-containment/array-membership; GiST for ranges/geo; BRIN only when physical order correlates with the column (`pg_stats.correlation ≈ 1`, e.g. append-only timestamps).
- Composite index column order: equality predicates first, highest-selectivity first, range/sort columns last.
- Every index taxes every write. Audit unused indexes (`pg_stat_user_indexes.idx_scan = 0`).

## Review checklist (detectable conditions)

**Keys & identity**
- Table with no primary key → 🔴 CRITICAL
- `SERIAL`/`BIGSERIAL` in use → 🔵 LOW (deprecation; prefer `GENERATED ALWAYS AS IDENTITY`)
- `uuid` PK defaulting to `gen_random_uuid()` (v4) on a high-write table → 🟡 MEDIUM (index bloat)
- Natural key on a mutable attribute (e.g. `email` as PK) → 🟠 HIGH

**Referential integrity**
- FK column without a covering index on the child table → 🟠 HIGH
- FK with implicit `NO ACTION` on a domain-owned child → 🟡 MEDIUM (likely unintentional)
- `ON DELETE CASCADE` on a financial / audit / ledger table → 🟠 HIGH

**Constraints & nullability**
- Money/currency typed `float`/`real`/`double precision` → 🔴 CRITICAL
- Money typed Postgres `money` → 🟡 MEDIUM
- `timestamp` (no tz) on a `*_at`/`occurred_at` column → 🟠 HIGH
- Logically-required column declared nullable with no rationale → 🟡 MEDIUM
- Finite-set column (status/type/role) with no CHECK and no FK lookup → 🟡 MEDIUM
- `varchar(n)` with an arbitrary round cap (255/500) and no business invariant → 🔵 LOW

**Indexes**
- Composite index with a range/LIKE column before an equality column → 🟡 MEDIUM
- BRIN on a low-correlation column (`pg_stats.correlation < 0.5`) → 🟠 HIGH
- > ~5 indexes on a write-heavy table → 🟡 MEDIUM (write-amplification audit)
- Unused index on an established table → 🔵 LOW
- JSONB queried via `@>`/`?` with no GIN index → 🟡 MEDIUM

**Structure**
- Comma/pipe/JSON-array-of-values stuffed in a `text` column → 🔴 CRITICAL (1NF violation)
- Table > ~50 columns → 🟡 MEDIUM (god-table smell)
- > 30% nullable columns on a wide table → 🟡 MEDIUM (nullable sprawl)
- `(entity_type text, entity_id bigint)` polymorphic FK pair → 🟠 HIGH
- `(entity_id, attribute_name text, attribute_value text)` triple → 🔴 CRITICAL (EAV; see simplification lens)
- JSONB column whose app code always reads the same fixed key set → 🟡 MEDIUM (normalize)

## Named anti-patterns

| Name | Detection signature | Why bad |
|---|---|---|
| **EAV** | `(entity_id, attribute_name, attribute_value)` | No type safety, no per-attr constraints, queries require pivots, unindexable |
| **Comma-separated list** | `text` column split in app code / matching `%,%` | 1NF violation; no FK integrity; substring queries; O(n×m) aggregation |
| **Polymorphic FK** | `(commentable_type, commentable_id)` for N parents | Cannot declare a real FK; no referential integrity; UNION/CASE queries |
| **God table / nullable sprawl** | > 50 cols, > 30% nullable, mixed entities | Rows mean different things; ambiguous NULL semantics |
| **Float for money** | `price float`, `amount double precision` | IEEE-754 rounding; silently wrong at scale |
| **UUIDv4 PK at high write** | `id uuid default gen_random_uuid()` hot insert | Random key → page splits, index bloat, WAL inflation |
| **Bare timestamp** | `created_at timestamp` | Drops tz; breaks across UTC/local |
| **Unindexed FK** | FK with no index on child column | Seq scan on every parent DELETE/UPDATE |
| **Missing finite-set constraint** | status/type `text` with no CHECK/FK | DB-level invariant absent; invalid states insertable |

## Severity quick map

- 🔴 CRITICAL: float for money; CSV-in-column (1NF); no PK; EAV on core table
- 🟠 HIGH: unindexed FK; bare `timestamp` for events; mutable natural-key PK; CASCADE on financial/audit; polymorphic FK
- 🟡 MEDIUM: UUIDv4 PK at scale; nullable sprawl / god table; JSONB-without-GIN; JSONB over fixed keys; enum for evolving set; missing CHECK/FK on finite set; over-indexing; BRIN on low correlation
- 🔵 LOW: `SERIAL` usage; arbitrary `varchar(n)`; unused index

## Sources

- [PostgreSQL Docs — Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html) · [Monetary Types](https://www.postgresql.org/docs/current/datatype-money.html)
- [Use The Index, Luke — covering indexes](https://use-the-index-luke.com/sql/clustering/index-only-scan-covering-index) · [composite ordering](https://use-the-index-luke.com/sql/where-clause/the-equals-operator/concatenated-keys)
- [pganalyze — UUID vs serial](https://pganalyze.com/blog/5mins-postgres-uuid-vs-serial-primary-keys) · [GIN](https://pganalyze.com/blog/gin-index) · [BRIN](https://pganalyze.com/blog/5mins-postgres-BRIN-index) · [JSONB/TOAST](https://pganalyze.com/blog/5mins-postgres-jsonb-toast)
- [Karwin — Polymorphic Associations (SQL Antipatterns)](https://www.oreilly.com/library/view/sql-antipatterns/9781680500073/f_0043.html)
- [tapoueh — DB modelization anti-patterns](https://tapoueh.org/blog/2018/03/database-modelization-anti-patterns/)
- [Crunchy Data — Money in Postgres](https://www.crunchydata.com/blog/working-with-money-in-postgres)
- [Finding FKs missing indexes](https://kaveland.no/posts/2025-04-04-finding-missing-indexes-in-pg-catalog/)
