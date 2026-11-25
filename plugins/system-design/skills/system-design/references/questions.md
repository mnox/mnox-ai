# Questions

The aim is three or four questions whose answers change the architecture, and a
written default for everything else.

## The flip test

For a candidate question, write its two most plausible answers.

- If they lead to **different diagrams** (a different store, an added tier, a
  sync path becoming async), ask it.
- If they lead to the **same diagram with different numbers**, assume it.

Supporting checks:

- **Notional design test.** Picture the plainest design that could work: one
  service, one database. If it is not obvious how that design meets a
  requirement, the requirement is architecturally significant.
- **Trade-off point.** A question that pushes two qualities in opposite
  directions (consistency against availability, latency against cost) is worth
  more than one that touches a single quality.
- **Baseline hygiene does not count.** TLS, authentication and encryption at
  rest are assumed. Only ask about security when a workflow needs special
  design, such as running user-submitted code.
- **Extremes need a reason.** "Six nines" with no stated cost of downtime is
  not a requirement. Ask what an hour of downtime costs instead.
- **Ask for facts, derive the rest.** Ask daily users and actions per user.
  Derive requests per second and storage.

## Ranked categories

Ranked by how often the answer changes the design. The ranking and the "flips"
column are a synthesis; the sources list the questions more than they rank
them.

| # | Question | What the answer flips | Default if unanswered |
|---|---|---|---|
| 1 | Which two or three capabilities are the core, and what is out of scope? | Which components exist at all | The simplest useful version; list exclusions as non-goals |
| 2 | Per feature, if forced: correct or available? | Strongly consistent store and transactions, or replicated and eventually consistent | Strong for money, inventory and bookings; eventual for feeds, counts and search |
| 3 | Order of magnitude of users or data, and over what horizon? | One node, or partitioned from the start | Round up to a power of ten; state it |
| 4 | Read to write ratio, and is access skewed toward a few keys? | Caches and replicas, or a write-optimised log; hot-key handling | Read-heavy for consumer products; write-heavy for telemetry and logging |
| 5 | Which user-facing path has a latency target, and what is it? | Precompute or compute on read; sync or async | Interactive reads in the low hundreds of milliseconds; writes may acknowledge and finish later |
| 6 | How much data loss is tolerable? | Acknowledge after replication or a durable log, or best effort | None for user-created records; some for derived data and metrics |
| 7 | What does an hour of downtime cost? | Redundancy, failover and multi-zone spend | Single region, multi-zone, no cross-region failover |
| 8 | Is traffic steady or spiky? | Queue buffering, autoscaling, backpressure | Daily peaks of a few times the average; note any event-driven spikes |
| 9 | One customer or many, and how isolated must they be? | Shared, siloed or mixed tenancy; the whole control plane | Consumer: none. B2B: pooled, with tenant ID on every row |
| 10 | Does each customer configure behaviour, and who does the configuring? | Settings model, config store, admin surfaces, onboarding flow | B2B: yes, by a customer admin, self-service |
| 11 | One region or global? | CDN, multi-region replication, conflict handling, data residency | One region |
| 12 | Any regulatory or contractual obligations? | Residency, audit trail, deletion paths, isolation | None beyond ordinary privacy practice |
| 13 | What are the payloads: size, mutability, retention? | Blob store or database; immutable caching; tiering and expiry | Small structured records kept indefinitely; media immutable and stored as blobs |
| 14 | Client constraints: mobile, offline, low bandwidth? | Push or poll, sync protocol, payload design | Web and mobile on a reasonable connection, no offline mode |
| 15 | Fixed constraints: existing stack, team size, deadline? | Removes options outright | Greenfield, small team, common managed services available |

Real-time needs fall under 5 and 14. Questions 9 and 10 are the ones interview
frameworks leave out and real B2B systems are built around.

## Choosing the few

Walk the table top to bottom and stop at four that pass the flip test. In
practice:

- Question 1 almost always passes.
- Then take the question that touches the **distinctive part** of the problem
  (contention for booking, fan-out for feeds, ordering for messaging).
- Then take whichever of 2, 3 and 9 the prompt leaves most open.
- Fewer than four is fine. A well-specified prompt may need one.

Other ways to prioritise, usable as cross-checks:

- **Importance against difficulty.** Rate each quality scenario High, Medium or
  Low on business importance and on difficulty. High on both drives the design.
  Low on both will not change it.
- **Risk.** Phrase the worry as a failure ("a celebrity post stalls the feed
  for everyone") and ask about the ones with the highest likelihood times
  impact.
- **Fewest characteristics.** Choose the smallest set of quality attributes the
  system must be good at, then try to drop one more.

## Full clarification

The four-question limit is for starting a practice session. When the user asks
for the complete set of questions to take to a stakeholder, or wants scope,
constraints and requirements fully clarified, produce the whole set instead.
Nothing is asked interactively and nothing is assumed: the output is the
questions.

Organise by category, most consequential category first. Within a category,
order by how much of the design the answer moves. Give each question an ID (a
category letter and a number) and one line saying what it decides. A question
with no "decides" line is not worth asking.

Use these categories. Rename the second to fit the domain, and drop a category
only when it truly has nothing in it.

| Key | Category | What belongs in it |
|---|---|---|
| S | Scope | Which capabilities are the product, which adjacent features are in or out, the explicit non-goals |
| M | Domain rules and regulation | Who is legally responsible for what, jurisdictions, licences, mandated checks, reporting and retention duties. For payments this is money and licensing; for health, patient data; for marketplaces, liability between the sides |
| P | Personas | The launch customer, each distinct user type, internal staff roles, and what "done" means to each |
| C | Correctness and trust | What is final, what can be undone and by whom, behaviour on retries and partial failure, what must be exact and what may lag, disputes, privacy defaults |
| B | Business and scale | Size now and in three years, peaks, the largest single customer or transaction, financial exposure, the cost of downtime |
| G | Growth and PLG | The growth loop, the activation moment and how little is asked before it, where revenue comes from, incentives, what must be testable as an experiment, upgrade paths |
| K | Configurability | Which rules change without a release and along which dimensions, who changes them and with what approval, what end users set, what business customers customise, whether it is one product or a platform others embed |
| T | Stack and delivery | Mandated technology, vendors already contracted, team size and deadline, build-or-buy stance, what auditors or partners require of the stack itself |
| U | Sneaky unknowns | What surfaces months later: reconciliation with outside records, cut-offs and delayed reversals, abandoned or frozen accounts, a partner changing terms or leaving, retention against deletion, how mistakes in the record are corrected |

Rules for the set:

- Five to seven questions per category. If a category wants more, the lower
  ones are details.
- Every question passes the flip test or exposes a constraint. "What is the
  expected scale?" fails. "Users, transactions per day and volume at launch and
  in three years?" passes.
- Ask about the business fact, not the technical consequence. "Can you pay
  someone who has no account?" not "Do we need a pending-payment state?"
- Personas come with a hypothesis: a short table of each persona and what they
  expect, marked as something to confirm. Include internal staff.
- For the sneaky unknowns, ask what happens at the unhappy edges of the
  domain's real-world process. Every domain has a reconciliation problem, a
  delayed-reversal problem, and a what-if-the-partner-leaves problem.
- Finish with **ask these first**: the five whose answers remove the most
  uncertainty, usually led by scope and by who is responsible for what.

## Writing assumptions

Every default goes in the ledger as something that could be proved wrong.

| Weak | Usable |
|---|---|
| Highly available | A regional outage may take the service down; a zone outage may not |
| Large scale | 10 million daily users, about 100 reads per write |
| Fast | Feed loads in under 300 ms at the 95th percentile |
| Consistent | A booking is never confirmed twice; search may lag by up to 30 seconds |

Say the assumption and move on. Waiting for an answer to a question that fails
the flip test costs more than being corrected later.

## Estimation

Do a calculation only when its result chooses between two designs, and name
both. Examples that qualify: whether the data fits on one node, whether a
ranking structure fits in memory, whether write volume exceeds one partition.
Use powers of ten and round up. If no calculation would change the design, say
so in one line and skip it.
