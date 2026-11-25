# Forks

A fork is a decision with real alternatives where choosing wrong is expensive
to undo. This file is a lookup table. The map ranks forks for the specific
problem; it never lists them in this order.

## Catalogue

| # | Fork | Options | Signals that tip it | Cost of choosing wrong |
|---|---|---|---|---|
| 1 | Consistency, per component | Strong, or eventual | Money, inventory, booking limits lean strong; most else can favour availability | Strong: timeouts and refusals during a partition. Eventual: stale reads, double booking |
| 2 | Tenancy | Silo per tenant, shared pool, or a mix | Compliance and noisy neighbours lean silo; many small tenants and cost lean pool | Silo: cost grows with every tenant. Pool: leakage risk and shared blast radius. Moving a tenant between models is a migration |
| 3 | Service boundaries | One deployable, or several services | New or unclear domain leans one; well-understood domain with separate teams leans several | Moving a boundary between services is far harder than moving it inside one codebase |
| 4 | Datastore | Relational, or non-relational (key-value, document, wide-column) | Joins and transactions lean relational; flexible shape, very large volume or very high write rate lean non-relational | Non-relational: joins and invariants move into application code. Relational: sharding becomes your problem |
| 5 | Partition key | Hash or range; by tenant, user, time or entity | Writes exceed one node; the dominant access pattern | Hard to change once live. Hot partitions. Transactions cannot cross partitions |
| 6 | Sync or async | Do the work in the request, or acknowledge and finish later | Work longer than a few seconds, or an acknowledgement is enough, leans async | Sync: timeouts and coupled failures. Async: delay, extra moving parts, status the client must poll for |
| 7 | Queue or event stream | Work queue (message removed when handled), or append-only log (retained, replayable) | Commands, routing and priorities lean queue; replay, several independent consumers, very high ordered volume lean stream | Queue: no replay, one logical consumer. Stream: no per-message priority, ordering only within a partition |
| 8 | Delivery semantics | At most once, at least once with idempotent handlers, or effectively once | Any retry of a mutating call; duplicates that cost money | Double orders and double charges, or silently dropped work |
| 9 | Multi-step coordination | Central orchestrator, or services reacting to each other's events | Ordered steps and central state lean orchestration; independent steps across separate domains lean choreography | Choreography: nobody sees the whole flow, cycles, event storms. Orchestration: a bottleneck and a single point of failure |
| 10 | Workflow state | Durable workflow engine, or hand-rolled state tables and retries | Many steps, must survive a crash mid-sequence, waits of hours or days, human approval, compensation | Hand-rolled: you rebuild scheduling, retries and reconciliation yourself |
| 11 | Cross-service invariants | Keep it in one database, two-phase commit, or saga with compensation | An invariant spans service boundaries | Sagas have no isolation: lost updates, dirty reads, compensations that can themselves fail |
| 12 | Contention | Optimistic versioning, row locks, or a distributed lock or reservation | Many actors competing for one scarce thing | Double allocation, or throughput collapse behind a lock |
| 13 | Client updates | Polling, long polling, server-sent events, or WebSockets | One-way push leans server-sent events; frequent two-way leans WebSockets; otherwise start with polling | WebSockets: a stateful connection tier to scale and drain. Polling: wasted requests and lag |
| 14 | Fan-out | On write, on read, or hybrid | Read-heavy with bounded followers leans write; a few very large audiences lean read or hybrid | Write: one post becomes millions of writes. Read: slow, expensive reads |
| 15 | Caching | Read-through or cache-aside, write-through, write-behind, refresh ahead | Read-heavy, slow-changing data and a stated tolerance for staleness | Stale data, stampedes on expiry; write-behind can lose data |
| 16 | Processing | Batch, or stream | Unbounded data whose value decays quickly leans stream | Stream brings windowing, late events and harder recovery |
| 17 | State model | Current state (CRUD), separate read and write models, or event sourcing | Reads and writes that scale or evolve very differently; a need for audit and replay | A large jump in complexity; replay is awkward once external systems are involved |
| 18 | Availability topology | Single region, active and standby, or active in several regions | Tolerance for downtime and data loss; where users are | Data loss on failover, or conflict resolution everywhere |
| 19 | Large payloads | Through the application, or direct to blob storage with signed URLs | Video, images or documents in the request path | Application servers become the bottleneck |
| 20 | Configuration model | Hard-coded behaviour, per-tenant settings, or customer-defined rules | How much each customer's behaviour differs and who changes it | Too little: one-off forks per customer. Too much: an untestable rules engine |
| 21 | Build or buy | Own it, or use a managed service or vendor | Whether the part is the product's differentiator; team size | Build: you operate it forever. Buy: cost, limits and lock-in |

Forks 20 and 21 are not drawn from the researched catalogues. They are here
because product-shaped problems reach them early.

Other trade-offs that show up as details more often than as forks: vertical or
horizontal scaling, normalised or denormalised data, REST or GraphQL or RPC,
stateful or stateless services.

## Dependency order

A fork higher in a chain constrains the ones below it. In the map, never rank a
fork above one it depends on.

- **Consistency (1) → datastore (4) → partition key (5).** Transactions do not
  cross partitions, so the key has to keep together whatever must change
  together.
- **Tenancy (2) → partition key (5)** and deployment topology. In a pooled
  model the tenant ID is the natural key.
- **Service boundaries (3) → cross-service invariants (11) → coordination (9,
  10).** A database per service is what makes sagas necessary.
- **Sync or async (6) → queue or stream (7) → delivery semantics (8).**
  At-least-once delivery forces idempotent consumers. Ordering needs a
  partition key, which loops back to 5 and to hot keys.
- **Read to write ratio → caching (15), fan-out (14), state model (17).** All
  three assume eventual consistency is acceptable on that path, so they sit
  below 1.
- **Client updates (13) → a stateful connection tier → publish and subscribe**,
  which reuses the broker chosen in 7.
- **Configuration model (20) → tenancy (2) and datastore (4)** when settings
  are read on every request.

A workable default sequence: 1 and 2, then 3, then 4 and 5, then 6 to 8, then 9
to 11, then the rest. The first three links of the list above are stated in the
sources. The remainder is synthesis.

## Ranking for a specific problem

Score each live fork High, Medium or Low on three things.

- **Reversibility.** One-way doors get decided slowly and first. Two-way doors
  get a default and a note. A change that needs a data migration, a new
  partition key, or a break in a public contract is one-way.
- **Blast radius.** Count the forks below it in the dependency chains.
- **Uncertainty.** How far the stated requirements are from settling it. A fork
  the prompt already decides is not a fork; it is an assumption.

Defer anything reversible until the moment that not deciding would remove an
option. Surface only the forks whose moment is now.

A fork earns a place in the top five if it is High on reversibility and at
least Medium on one other. If more than five qualify, the scope is too wide:
cut scope before cutting forks.

## Triggers

Use these in Step 4 to say which mechanisms the design needs, and on what
signal.

**Queue.** Work that takes more than a few seconds. Bursty input that needs a
buffer. Producers and consumers that must scale or fail independently. Commands
that must not be lost. Bring retries, a dead-letter path and backpressure with
it. Not for a path with a strict synchronous latency target.

**Event stream.** A need to replay or re-read history. Several independent
consumers of the same facts. High-volume ordered data such as telemetry or
change capture. Event sourcing.

**Background jobs.** A request whose work outlives the request: encoding,
report generation, bulk import and export. Return a job ID and expose status.

**Scheduler.** Anything that happens because of time, not a request: reminders,
digests, expiry, billing cycles, retention sweeps, retries with delay. Ask how
many timers exist at once and how precisely they must fire. This trigger is a
practical addition and was not confirmed in the sources.

**Workflow engine.** Several steps across services that must survive a crash.
Waits of hours or days. Human approval. Compensation on failure. A lot of state
and a lot of failure handling. Not needed for simple fire-and-forget flows.

**Hot key or skew.** Keys by date or first letter. One celebrity, one tenant or
one item taking most of the traffic. A per-partition throughput ceiling. The
usual fixes (hashing, key suffixes, splitting the heavy tenant out) trade
simple writes for scatter-gather reads. Shard when the arithmetic says so, not
before.

**Transactional outbox.** A service that must update its database and publish
an event about it, where losing either is unacceptable.

**Idempotency keys.** Any client or consumer that retries a call with side
effects.

**Connection tier.** Server-initiated updates to many clients at once.

## Learn-mode entries

In learn mode each fork also gets:

- **Leans**: which option this problem's signals point to.
- **Because**: the requirement or assumption doing the pointing.
- **Would flip if**: the change in requirements that reverses it.

Phrase the lean as a reading of the signals. The learner should still be able
to disagree and defend it.
