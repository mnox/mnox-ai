# Lens: Data Modeling — DDD (Transactional) + Dimensional (Analytics)

Design-altitude modeling. Two sub-modes: transactional (DDD aggregates/boundaries) and analytics (Kimball dimensional + dbt layering + data contracts). Pick the relevant sub-mode(s) for the target.

## Principles — Transactional / DDD

- An aggregate is a **consistency boundary**, modeled around invariants — not a data container.
- Only the aggregate **root** is referenced from outside; external code never holds refs to internal entities.
- **One transaction = one aggregate.** A use case mutating two aggregates atomically is a modeling error → use eventual consistency + domain events.
- Value objects are identity-free, immutable, structurally equal — embed them in the owner's table, don't give them a row + ID.
- An entity earns its own table only with independent lifecycle + identity (exists without the root, directly queryable).
- A bounded context owns its schema; don't share tables or cross-context FKs — map at integration points.
- Behavior belongs on the model; a pure getter/setter table with all logic in services is the Anemic Domain Model in schema form.
- Domain events are first-class, immutable, append-only — not mutable state columns.
- Ubiquitous language must survive into table/column names; schema contradicting the spoken language signals a broken boundary.

## Principles — Analytics / Dimensional (Kimball + dbt)

- **Declare the grain first.** Every column must be consistent with the declared grain.
- Fact tables = measurements at a grain; dimensions = descriptive context. Never swap.
- Prefer **star over snowflake** — denormalize dimensions; storage is cheap, joins are expensive.
- Every dimension with time-varying attributes needs an explicit **SCD strategy** — choosing none is choosing silent history loss.
- **Surrogate integer keys on all dimensions** — natural keys are attributes, not PKs (prerequisite for SCD Type 2).
- No NULL FK in a fact table — use an "Unknown"/"N/A" surrogate dimension row.
- Document `factType`: additive (summable everywhere), semi-additive (summable across some dims, e.g. balances), non-additive (ratios/percentages — never sum).
- Conformed dimensions are shared across fact tables for consistent drill-across; degenerate dimensions (order #) live in the fact table.
- **dbt layering:** `staging` (1:1 per source, rename/cast only, no joins/aggregates) → `intermediate` (reusable joins/business logic) → `marts` (one model per business entity at its grain). Centralize logic; never repeat a metric definition across models.
- Every mart model carries generic tests: `unique`+`not_null` on PK, `relationships` on FKs, `accepted_values` on enum-likes. Tier-1 marts get enforced **model contracts**.
- **Schema is an API / data contract:** breaking changes (drop, type-narrow, rename) need a versioned deprecation window. A data product with no contract degrades the mesh into chaos.

## Review checklist

**DDD / transactional**
- Aggregate with multiple entry points / no single root → 🟠 HIGH (broken encapsulation)
- Use case mutating two aggregate roots in one transaction → 🔴 CRITICAL (boundary violation, invariant corruption)
- Value object (money, address, date-range) given its own table + ID → 🟡 MEDIUM (over-normalized VO)
- Internal entity reachable only via multi-hop FK, not via root → 🟠 HIGH
- Bounded context sharing a table / cross-context FK → 🟠 HIGH (boundary breach)
- Domain tables that are flat column bags, no invariant enforcement at DB → 🟠 HIGH (anemic, suspect)
- Domain events stored as mutable row updates instead of appended records → 🟡 MEDIUM
- Column/table names contradicting the domain's spoken language → 🟡 MEDIUM (language drift)

**Analytics / dimensional**
- Fact table with no declared grain → 🟠 HIGH
- Fact-table row representing more than one event type → 🔴 CRITICAL (mixed grain → double-counting)
- Dimension with time-varying attrs but no SCD strategy → 🔴 CRITICAL (silent history loss)
- Dimension PK is a natural/business key → 🟠 HIGH (blocks SCD Type 2)
- NULL FK in a fact table → 🔴 CRITICAL (dropped rows on join)
- Ratio/percentage column in a fact with no "do not sum" doc → 🟡 MEDIUM (non-additive misuse)
- Pre-aggregated summary rows mixed with atomic rows in one table → 🟠 HIGH (grain contamination)
- Dimension with 100+ cols spanning unrelated subjects → 🟡 MEDIUM (god dimension)

**dbt**
- `stg_` model containing JOINs / GROUP BYs → 🟡 MEDIUM (staging violation)
- Same business logic computed in > 1 model → 🟠 HIGH (duplicated logic, diverging KPIs)
- Mart model missing `unique`+`not_null` on its PK → 🟠 HIGH (untested grain)
- Missing `relationships` tests on FK columns → 🟡 MEDIUM
- Tier-1 mart (consumed downstream) with no model contract → 🟠 HIGH
- Model names off-convention (`stg_<src>__<entity>` / `int_<purpose>` / `<entity>`) → 🔵 LOW

**Data contracts**
- Consumer-facing data product with no published schema/contract → 🟠 HIGH
- No documented deprecation process for breaking changes → 🟡 MEDIUM

## Named anti-patterns

| Name | Signature | Why bad |
|---|---|---|
| **Mixed grain** | Fact rows of different event types in one table | Double-counts; nearly unfixable post-deploy |
| **Silent SCD overwrite** | Mutable dimension, no validity dates / versioning | Past facts re-label with today's attributes |
| **God dimension** | One dimension, 100+ unrelated cols | Perf + maintainability collapse |
| **Anemic model leakage** | Flat tables, logic only in services, no DB invariants | Invariants only as good as every call path |
| **Transaction boundary crossing** | One txn mutates two aggregate roots | Tight coupling; invariant corruption |
| **Context boundary breach** | Shared table / cross-context FK | Change in one context silently breaks another |
| **Staging contamination** | JOIN/GROUP BY/business logic in `stg_` | Downstream can't reuse staging cleanly |
| **Duplicated transform logic** | Same metric defined in multiple models | Consumers report different numbers |
| **Orphaned fact** | NULL/dangling FK in fact table | Joins silently drop rows |
| **Natural key as warehouse PK** | String business key as dimension PK | Blocks SCD Type 2; slow joins; corrupts history |

## Severity quick map

- 🔴 CRITICAL: mixed grain; silent SCD overwrite; transaction boundary crossing; NULL FK in fact
- 🟠 HIGH: no grain declared; natural-key dimension PK; context boundary breach; anemic w/ no DB invariants; no contract on Tier-1 product; duplicated transform logic; untested mart grain
- 🟡 MEDIUM: god dimension; staging contamination; over-normalized VO; language drift; non-additive undocumented
- 🔵 LOW: missing non-PK tests; model naming deviations; missing "Unknown" surrogate row

## Sources

- [Fowler — DDD_Aggregate](https://martinfowler.com/bliki/DDD_Aggregate.html) · [BoundedContext](https://www.martinfowler.com/bliki/BoundedContext.html) · [AnemicDomainModel](https://martinfowler.com/bliki/AnemicDomainModel.html)
- [Kimball — Keep to the Grain](https://www.kimballgroup.com/2007/07/keep-to-the-grain-in-dimensional-modeling/) · [Grain technique](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/grain/)
- [dbt — How we structure projects](https://docs.getdbt.com/best-practices/how-we-structure/1-guide-overview) · [Staging](https://docs.getdbt.com/best-practices/how-we-structure/2-staging) · [Model contracts](https://docs.getdbt.com/docs/mesh/govern/model-contracts)
- [Red Gate — 5 dimensional modeling mistakes](https://www.red-gate.com/blog/five-common-dimensional-modeling-mistakes-and-how-to-solve-them/)
