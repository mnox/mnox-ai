# Observability Funnel — Finding the Offender Before You Touch a Plan

When the symptom is "the app/endpoint is slow" (not a known SQL statement), never start in
`EXPLAIN`. Funnel from the trace down to the exact normalized query, *then* pull the plan.

## The funnel (APM + Database Monitoring)

1. **Service / endpoint view** — sort endpoints by p95/p99 latency **and** by total time
   (latency × throughput). p50-fine / p99-terrible = tail latency (locks, plan flips, cold
   cache); uniformly slow = structural.
2. **Trace flame graph** — read the **time-in-DB vs time-in-app** split. This is the most
   important fork:
   - Mostly **app time** → not the DB (code, serialization, GC, non-DB N+1). Stop blaming SQL.
   - **Many short DB spans** → N+1 / queries-in-a-loop. Fix at the ORM layer.
   - **One long DB span** → a genuinely slow query. Proceed to the plan.
3. **DBM "Top Queries by total time"** — Database Monitoring tools normalize queries into a
   `query_signature` (hash of the statement with literals obfuscated) and rank the top
   normalized queries by total execution time. Filter on `query_signature`, never raw `query`
   text (which fragments by literal value).
4. **DBM ↔ APM correlation** — trace IDs are injected into DBM samples, so pivot from the slow
   span directly to its query sample: recent explain plan, sampled **wait events**
   (lock/IO/CPU), and historical latency for that signature.

## Signal → meaning

| Signal | Tells you |
|---|---|
| p99 ≫ p95 ≫ p50 | Tail problem — locks, plan instability, cache misses, GC |
| High total time, low per-call | Volume / N+1, not a slow query |
| Time-in-DB low, app time high | Not the DB — app code, serialization, GC |
| Wait events = Lock / row-lock | Contention, not the plan |
| Wait events = IO / buffer | Missing index / table scan / over-fetch → EXPLAIN now |
| Wait events = CPU | Bad plan, expensive sort/join → EXPLAIN ANALYZE |
| Latency up but DB internal metrics pristine | **Connection pool / pooler** (DBM can't see inside PgBouncer) |

## The "app is slow" decision tree

```
"App is slow"
 └─ APM: one endpoint or systemic?
     ├─ Systemic across endpoints
     │    └─ Infra: host CPU/IO, DB CPU, or POOL EXHAUSTION
     │         (latency up + DB metrics normal ⇒ pool/pooler)
     └─ One endpoint
          └─ Trace: time-in-DB vs time-in-app?
              ├─ Mostly APP   ⇒ not the DB (code, serialization, GC)
              ├─ MANY short DB spans ⇒ N+1 / queries-in-loop → fix in ORM
              └─ ONE long DB span ⇒ slow query
                   └─ DBM sample wait events?
                       ├─ Lock     ⇒ contention (long txns, hot rows)
                       ├─ IO/buffer ⇒ missing index / seq scan → EXPLAIN
                       └─ CPU      ⇒ bad plan / sort / join → EXPLAIN ANALYZE
```

## Connection-pool tell

Most DB monitors only see *inside* the database, so a saturated PgBouncer/pool shows up as
**app-side latency with pristine DB metrics**. Watch the pool's **wait queue size** and
**wait time** (should be ~0). A sustained queue means either the pool is too small *or*
queries hold connections too long — which loops back to a query problem.

## Pulling the funnel data

If APM/Database-Monitoring tooling is available (Datadog DBM, pganalyze, New Relic, or
similar), use it to pull the funnel data directly: slow-endpoint traces, DBM
top-queries-by-total-time, wait-event breakdowns, and the query sample's explain plan. This
beats guessing which statement is the offender. Without DBM, fall back to `pg_stat_statements`
(top queries by total time) plus the application's request logs / per-request query counts to
spot N+1.
