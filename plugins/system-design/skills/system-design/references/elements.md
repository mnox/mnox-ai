# Elements

Every area below gets a verdict in the map: `core`, `likely`, or `skip` with a
reason. Within areas that are in play, list the elements whose trigger fired
and attach one question for the learner to answer.

The triggers are the test. If a trigger is true for this problem, the element
belongs in the map.

## Two planes

Split the system in two before filling the inventory.

- **Application plane**: what users and clients touch. The product's features,
  its APIs and its data. Tenant isolation is enforced here.
- **Control plane**: what creates, configures, bills, observes and retires
  customers. It delivers no feature a customer asked for, which is why designs
  leave it out and operators end up doing it by hand.

With fewer than about ten customers a documented manual process can stand in
for a control plane. Self-service sign-up needs one from the start. Tenant
self-configuration (users, settings, schedules) is the customer-facing edge of
the control plane.

## Inventory

### A. Framing

| Element | Trigger | Question for the learner |
|---|---|---|
| Goals and non-goals | Always | What could reasonably be in scope that you are choosing to exclude? |
| Constraints | A fixed stack, team, budget or date exists | Which options does each constraint remove? |
| Alternatives considered | Any fork with a real trade-off | What was the runner-up and why did it lose? |
| Open questions and risks | Always | What do you still not know, and what breaks if you guessed wrong? |

### B. Product surface

| Element | Trigger | Question for the learner |
|---|---|---|
| Core flows | Always | What are the two or three end-to-end paths, step by step? |
| Entities | Always | What are the nouns, and who owns each? |
| Users and teams within an account | More than one user per customer | How are users invited, grouped and removed? |
| User-level settings and preferences | Behaviour differs by user (notification choices, locale, quiet hours) | Where are preferences stored and when are they read? |
| Notifications to users | The system tells users something they did not just ask for | Which channels, and what stops a user being flooded? |
| Search and listing | Users must find things | Is search a database query or a separate index, and how fresh? |
| Reporting and analytics for customers | The buyer has to see value or usage | Is this read from the primary store or a separate one? |
| Import, export and integrations | Customers move data in or out; other systems react to events | Bulk or incremental? Webhooks, polling, or both? |
| Support surface | Users can get stuck | What does support need to see and do without an engineer? |
| Accessibility and localisation | Any user interface; more than one language or region | Does this change data shape or only presentation? |

### C. Control plane and tenancy

| Element | Trigger | Question for the learner |
|---|---|---|
| Tenant definition | B2B or any multi-customer system | What exactly is a tenant: a company, a workspace, a project? |
| Tenancy model | More than one tenant | Shared, siloed or mixed, and at which layers? |
| Onboarding | More than a handful of tenants | What gets created when a customer signs up, and is it one repeatable automated process? |
| Trials | Sales needs try before buy | What limits apply, and how does a trial become a paid account? |
| Tenant configuration | Any per-customer variation | Is it a setting, a feature flag, or a customer-defined rule, and where does it live? |
| Tiers and entitlements | Different plans or limits | Where are limits enforced, and what happens at the limit? |
| Tenant lifecycle | Any commercial system | What happens on suspend, reactivate, move, merge and offboard? |
| Operator admin tooling | Operators manage customers | What can staff do, to which tenant, and how is that access bounded and logged? |
| Tenant placement | Shards, cells or regional stamps | How is a tenant assigned, and how is a heavy one moved? |

### D. Billing and metering

| Element | Trigger | Question for the learner |
|---|---|---|
| Pricing unit | A commercial product | What is counted, and does the count match what costs you money? |
| Usage metering | Usage-based price or per-tenant cost visibility | Where is usage recorded, and can it be recomputed if a counter is wrong? |
| Subscription state | An external billing system | How does billing state map to tenant state, with what grace period? |
| Billing events | Webhooks from a payment provider | What happens on a duplicate or out-of-order event? |

### E. Data

| Element | Trigger | Question for the learner |
|---|---|---|
| Stores and shape | Always | Which store holds each entity, keyed how? |
| Access patterns | Always | What are the top reads and writes, and does the key serve them? |
| Partitioning | Data or writes exceed one node | What is the key, and what is the worst hot spot? |
| Caching | Read-heavy, slow-changing data | What is cached, for how long, and what invalidates it? |
| Large objects | Media or documents | Where do bytes live, and how do clients upload and download? |
| Retention, deletion, archival | Offboarding, legal duties, unbounded growth | What is deleted when, and how do you prove it? |
| Backup and recovery | Any durable data | How much can you lose and how long may recovery take? |
| Residency | Regulated or multi-region customers | Which data must stay where? |
| Schema change and backfill | Any system that outlives its first version | How do you change shape without downtime? |

Schema change and backfill is a practical addition. No source consulted lists
it by name.

### F. Interfaces

| Element | Trigger | Question for the learner |
|---|---|---|
| External API | Always | What are the calls, and which requirement does each serve? |
| Idempotency | Retried calls with side effects | How does the server recognise a repeat? |
| Pagination and limits | Lists and bulk reads | Cursor or offset, and what is the maximum page? |
| Rate limiting | A public or multi-tenant API | Limited per what, enforced where? |
| Real-time channel | Server-initiated updates | Which transport, and what happens on reconnect? |
| Versioning | External consumers | How does a contract change without breaking them? |
| Third-party dependencies | Any external service | What do you do when it is slow or down? |

### G. Async and eventing

Check every trigger in `forks.md` and record which fired.

| Element | Trigger | Question for the learner |
|---|---|---|
| Queue | Slow work, bursts, independent scaling, must-not-lose commands | What is on it, who consumes it, and what happens to a poison message? |
| Event stream | Replay, several consumers, ordered high volume | What is the event, what is the key, how long is it kept? |
| Background jobs | Work that outlives the request | How does the caller learn the result? |
| Scheduler | Time-driven work | How many timers, how precise, and what if the scheduler is down at fire time? |
| Workflow | Multi-step, long-running, must survive crashes | Where is the state, and what is the compensation for each step? |
| Outbox | A database write and an event that must both happen | How is the event guaranteed to follow the write? |
| Retries and dead letters | Any async consumer | How many attempts, how spaced, and who looks at the failures? |

### H. Security and compliance

| Element | Trigger | Question for the learner |
|---|---|---|
| Identity | Always | Who is the caller, and which tenant do they belong to? |
| Authorisation and roles | More than one role | Where is the check made, and against what? |
| Tenant isolation | Shared resources | What prevents one tenant reading another's data at each layer? |
| Single sign-on | Enterprise buyers | Per-tenant identity provider, and what on deprovisioning? |
| Audit log | Admin actions or compliance | Who did what to what, when, from where; immutable and exportable? |
| Secrets and keys | Stored credentials or customer-supplied keys | Where are they held and how are they rotated? |
| Privacy | Personal data | What is collected, why, and how is a deletion request honoured? |
| Abuse | Open sign-up or user-generated content | What is the cheapest attack, and what stops it? |

### I. Reliability and scale

| Element | Trigger | Question for the learner |
|---|---|---|
| Service objectives | Always | What is promised, measured how? |
| Capacity | Launch or stated growth | Which resource runs out first at ten times the load? |
| Failure modes | Always | For each dependency: what happens when it is slow, and when it is down? |
| Single points of failure | Production use | What one thing takes everything down? |
| Hot spots | Skewed keys, celebrities, large tenants | Where does load concentrate, and what spreads it? |
| Noisy neighbours | Pooled tenants | What stops one tenant degrading the rest? |
| Backpressure and shedding | Bursty input | What is dropped or delayed first? |
| Multi-region | Global users or strict availability | Where do writes go, and how are conflicts resolved? |

### J. Operations

| Element | Trigger | Question for the learner |
|---|---|---|
| Metrics, logs, traces | Always | What three numbers say the system is healthy? |
| Alerts and on-call | Production use | What pages a person, and what do they do? |
| Tenant-aware views | Multi-tenant | Can you see health and cost per customer? |
| Runbooks | Anything that needs a manual step | What is the recovery procedure for the top failure? |
| Routine maintenance | Rotation, cleanup, compaction | What runs on a schedule to keep the system healthy? |

### K. Delivery and rollout

| Element | Trigger | Question for the learner |
|---|---|---|
| Migration from the current state | Replacing or extending something live | How do you get from here to there without a flag day? |
| Staged rollout | Production use | Who gets it first, and what triggers a rollback? |
| Feature flags | Per-customer or gradual release | Who can flip them, and how are stale ones removed? |
| Customer-visible change | Enterprise customers | How much notice, and can a customer control timing? |
| Testing | Always | What is hardest to test, and how will you test it? |
| Deployment options | Customers who will not use a shared cloud | Hosted, customer-hosted, or both? |

### L. Cost

| Element | Trigger | Question for the learner |
|---|---|---|
| Cost drivers | Always, briefly | Which component dominates the bill at scale? |
| Cost per tenant | Shared infrastructure | Does spend follow customer activity, and can you attribute it? |

## Most often forgotten

No source ranks omissions. This list is inferred from what public design-doc
templates leave out and what the multi-tenant guidance warns about.

- The control plane as a whole, because it is not a feature.
- Tenant change over time: suspend, move, merge, split, offboard.
- Drift between billing state and tenant state.
- Enterprise expectations: single sign-on, audit logs, roles, change control.
- Per-tenant observability and cost attribution.
- Offboarding hygiene: deleting data, removing access, keeping commercial
  records.
- Operator tooling and bounded, logged support access.

## Verdict guidance by shape

Starting points. The prompt and answers override them.

| Area | Consumer product | B2B product | Infrastructure component | Data pipeline |
|---|---|---|---|---|
| B. Product surface | core | core | skip | skip |
| C. Control plane | skip or likely | core | likely (client configuration) | likely |
| D. Billing | skip | likely | skip | skip |
| G. Async | by trigger | by trigger | by trigger | core |
| H. Security | likely | core | likely | likely |
| A, E, F, I | core | core | core | core |
| J, K, L | likely | likely | likely | likely |
