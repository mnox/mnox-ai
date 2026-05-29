# Lens: Over-Complication, Taxonomy & Redundancy

The opposite failure mode from under-design: is this schema needlessly complex? Can it be simplified while still enforcing the same invariants? Also covers redundancy / drift. Over-complication is usually 🟡/🔵 **unless** it causes a correctness or perf failure; **redundancy that can drift is elevated** because it lies silently.

## Principles

- **Simplest model that satisfies the actual query patterns and invariants wins.** Optimize for the queries you have, not the ones you imagine.
- Normalize first; **denormalize only after measuring**. Premature denormalization is carried cost with no proven ROI.
- **YAGNI applies to schema.** Any abstraction not serving a current, named requirement is presumed guilty.
- Start with the **adjacency list** for trees; upgrade only when profiling surfaces an actual bottleneck.
- A lookup table earns its keep only when the set is **open and growing**. Closed static enums → `CHECK` or Postgres `ENUM`.
- Derived/redundant data stored **without a documented maintenance strategy is a drift time bomb** — justify every redundancy in writing.
- A 1:1 split with no access-pattern/security justification should be merged.

## Tree / taxonomy decision guide

| Model | Best when | Red flag of over-use |
|---|---|---|
| **Adjacency list** (`parent_id`) | Mixed read/write, moderate depth, CTEs available | Almost never over-used — the correct default |
| **Materialized path / `ltree`** | Prefix/label-path queries, bounded depth (org/file hierarchies) | < 3 levels; paths mutate constantly; FK integrity needed |
| **Nested sets** (lft/rgt) | Read-heavy, subtree queries dominate, writes rare | Any real write load; need direct parent; inserts re-number the tree |
| **Closure table** | Heavy ancestor/descendant queries on large trees | Deep trees (O(n²) rows); insert-heavy; built speculatively before adjacency list hit a limit |

**Default:** adjacency list + `WITH RECURSIVE` until a measured bottleneck forces an upgrade (then usually `ltree` for label paths, closure table for deep ancestor joins). Nested sets are rarely the right call.

## Review checklist

**Over-complication**
- Two tables in a strict 1:1, always queried together, no security/access boundary → 🟡 MEDIUM (merge candidate)
- Closure table / nested sets with no evidence adjacency-list + CTE was tried → 🟡 MEDIUM
- `ltree` for a < 3-level tree or paths with no meaningful label segments → 🟡 MEDIUM
- Junction table for an attribute-less M:N where a simple FK (1:N) suffices → 🟡 MEDIUM
- Lookup table for a ≤5-value documented-static set → 🔵 LOW (use `CHECK`/`ENUM`)
- Lookup/abstraction table with a single concrete row in production → 🟡 MEDIUM (speculative generalization)
- Generic columns (`attribute_1..n`, `value_text`/`value_int`) → 🔴 CRITICAL on a core table (EAV — see relational lens)
- Nested view chains > 3 levels wrapping simple joins → 🟡 MEDIUM
- Table > ~40–50 cols that isn't actual EAV → 🔵 LOW (wide-table smell)

**Redundancy / drift**
- Column derivable from other columns (same/joined table) with no refresh strategy → 🟠 HIGH (silent drift)
- Same fact (count/sum/status) stored in multiple tables with no sync mechanism → 🟠 HIGH
- Denormalized for performance with no comment citing the measured query cost → 🟡 MEDIUM
- Audit/`updated_at` duplicated across parent+child tracking the same event → 🔵 LOW

**Taxonomy-specific**
- Category tree as closure/nested-sets where actual depth is 2–3 → 🟡 MEDIUM (flat `parent_id` suffices)
- Polymorphic tagging as one tag table per entity type instead of `tags(entity_type, entity_id, tag)` → 🟡 MEDIUM
- Structurally-identical separate `category` + `subcategory` tables → 🟡 MEDIUM (self-referencing single table)

## Named anti-patterns

| Name | Signature | Simpler alternative |
|---|---|---|
| **Premature closure table** | Closure table on a 2-level / <1000-node tree, light queries | Adjacency list + CTE |
| **Lookup-table sprawl** | `*_types`/`*_statuses` tables with 2–5 never-grown rows | `ENUM` or `CHECK (col IN (...))` |
| **EAV** | `(entity_id, attribute_name, attribute_value)` | Structured columns; JSONB+`jsonb_path_ops` only if genuinely open-ended |
| **Phantom 1:1 split** | Two tables, shared PK, always joined, no boundary | Merge into one table |
| **Over-modeled M:N** | Attribute-less junction, query is always "all B for A" | `bigint[]` (if no cross-entity queries) or a plain FK |
| **Speculative generalization** | `(entity_type, entity_id)` "for future types" — still one type | Named FK; generalize when the 2nd type actually arrives |
| **Derived column w/o contract** | `total_*`/`count_*`/`cached_*`, no trigger/job/note | Compute on read, or add a named tested refresh job + document |
| **Nested view pyramid** | `view_c`←`view_b`←`view_a` | Materialize the intermediate; flatten the chain |

## Severity quick map

- 🔴 CRITICAL: EAV on a core transactional table (correctness + type safety + perf all lost)
- 🟠 HIGH: derived/redundant columns with no maintenance strategy on high-write tables (silent drift); lookup sprawl causing measured join explosion on hot paths
- 🟡 MEDIUM: premature closure/nested-sets; phantom 1:1 split; speculative generalization for a single current type; over-modeled M:N; nested view pyramid
- 🔵 LOW: lookup table for a tiny static enum; wide table that isn't EAV; duplicated audit columns

**Note:** over-complication that doesn't cause a correctness/perf failure is a smell to *note*, not a blocker. The exception is redundancy without a maintenance contract — it doesn't fail loudly, it slowly lies to you, so it ranks HIGH.

## Sources

- [Karwin — rendering trees with closure tables](https://karwin.com/blog/index.php/2010/03/24/rendering-trees-with-closure-tables/) · [SQL Antipatterns notes](https://tylerhillery.com/notes/sql-antipatterns/)
- [Ackee — hierarchical models in PostgreSQL](https://www.ackee.agency/blog/hierarchical-models-in-postgresql)
- [tapoueh — DB modelization anti-patterns](https://tapoueh.org/blog/2018/03/database-modelization-anti-patterns/)
- [CYBERTEC — EAV in PostgreSQL, don't do it](https://www.cybertec-postgresql.com/en/entity-attribute-value-eav-design-in-postgresql-dont-do-it/)
- [Neon — ltree extension](https://neon.com/docs/extensions/ltree)
- [Fowler — YAGNI](https://martinfowler.com/bliki/Yagni.html)
- [DoltHub — polymorphic associations](https://www.dolthub.com/blog/2024-06-25-polymorphic-associations/)
