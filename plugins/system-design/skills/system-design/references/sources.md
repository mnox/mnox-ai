# Sources

The prior art behind this skill, gathered by web research in November 2026.
Each entry says how it was checked: **read** (the page itself was fetched),
**secondary** (book notes, a transcription, or a search summary), or
**not confirmed**.

## Interview delivery frameworks

| Framework | Sequence | Checked |
|---|---|---|
| [Hello Interview delivery framework](https://www.hellointerview.com/learn/system-design/in-a-hurry/delivery) | Requirements → core entities → API → optional data flow → high-level design → deep dives, with a minute budget per step | read |
| [ByteByteGo four-step framework](https://bytebytego.com/courses/system-design-interview/a-framework-for-system-design-interviews) | Understand and scope → high-level design and buy-in → deep dive → wrap up | read |
| [Educative RESHADED](https://www.educative.io/courses/grokking-the-system-design-interview/the-reshaded-approach-for-system-design) | Requirements, estimation, storage schema, high-level design, API, detailed design, evaluation, distinctive component | read |
| [PEDALS](https://lewis-lin-website.pages.dev/posts/pedals-method) | Process requirements, estimate, design the service, articulate the data model, list components, scale | read |
| [system-design-primer](https://github.com/donnemartin/system-design-primer) | Use cases and constraints → high-level design → core components → scale | read |
| [interviewing.io guide](https://interviewing.io/guides/system-design-interview/part-three) | Requirements → data types, API, scale → design, storage first; declines to give time budgets | read |
| [DesignGurus seven steps](https://www.designgurus.io/blog/step-by-step-guide) | Requirements, estimation, interface, data model, high-level design, detailed design, bottlenecks | read |

What they share: scope first, a simple end-to-end design second, depth on
selected parts third, scaling and trade-offs last. Where they differ: whether
estimation is a fixed early step or done only when it changes the design;
whether the API comes before or after the high-level design; when the data
model is fixed.

What none of them has: an explicit step for ranking decisions before drawing,
or any coverage of onboarding, configuration, billing or operator tooling.
Those two gaps are what this skill adds.

The idea of naming the problem's distinctive part comes from RESHADED. The
product versus infrastructure distinction comes from
[Hello Interview](https://www.hellointerview.com/blog/meta-system-vs-product-design).

## Requirements and architectural drivers

| Source | Used for | Checked |
|---|---|---|
| [Hello Interview on requirements](https://www.hellointerview.com/blog/system-design-requirements) | Short prioritised lists; propose a scale; do not ask for derived numbers; quantified qualities | read |
| [interviewing.io part three](https://interviewing.io/guides/system-design/part-three) | Baseline security is not a requirement; unjustified extremes; powers of ten; defaults by domain | read |
| [ATAM overview](https://dmccreary.github.io/atam/faq/) | Utility tree, importance against difficulty, trade-off points | read (third-party course site) |
| [Fairbanks, risk-driven architecture](https://www.methodsandtools.com/archive/agilearchi.html) | Effort proportional to risk; risks as failure scenarios | read |
| [Architecturally significant requirements](https://en.wikipedia.org/wiki/Architecturally_significant_requirements) | Indicators of significance | read |
| Keeling, *Design It!* via [notes](https://danlebrero.com/2022/05/04/design-it-book-summary) | Notional architecture test; constraints as non-negotiable | secondary |
| Richards and Ford, *Fundamentals of Software Architecture* via [notes](https://danlebrero.com/2021/11/17/fundamentals-of-software-architecture-summary/) | Fewest characteristics; least-worst architecture | secondary |
| [SEI Quality Attribute Workshop](https://www.sei.cmu.edu/library/quality-attribute-workshops-qaws-third-edition/) | Prioritised scenarios before architecture | read (landing page only) |

The ranking of question categories and the flip test as named are this skill's
synthesis. No source consulted ranks questions by leverage. No source consulted
covers the multi-tenancy and configurability questions in an interview context.

## Forks and trade-offs

| Source | Used for | Checked |
|---|---|---|
| [system-design-primer](https://github.com/donnemartin/system-design-primer) | Consistency, datastore, caching, availability patterns | read |
| Hello Interview [core concepts](https://www.hellointerview.com/learn/system-design/in-a-hurry/core-concepts), [key technologies](https://www.hellointerview.com/learn/system-design/in-a-hurry/key-technologies), [patterns](https://www.hellointerview.com/learn/system-design/in-a-hurry/patterns) | Contention, real-time updates, long-running tasks, large blobs, queue and stream triggers | read (free pages; deep dives are paywalled) |
| [Azure data partitioning](https://learn.microsoft.com/en-us/azure/well-architected/design-guides/partition-data) | Partition key is hard to change; cross-partition transactions | read |
| [AWS SaaS Lens: silo, pool, bridge](https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/silo-pool-and-bridge-models.html), [Azure tenancy models](https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/considerations/tenancy-models) | Tenancy fork | read |
| [Fowler, MonolithFirst](https://martinfowler.com/bliki/MonolithFirst.html) | Service boundaries | read |
| [AWS reliability pillar, loose coupling](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_prevent_interaction_failure_loosely_coupled_system.html) | Sync or async | read |
| [AWS queue and stream comparison](https://aws.amazon.com/compare/the-difference-between-rabbitmq-and-kafka/), [Azure messaging choices](https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/messaging) | Queue or event stream | read |
| [AWS Builders' Library on idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) | Delivery semantics | read |
| Azure [choreography](https://learn.microsoft.com/en-us/azure/architecture/patterns/choreography) and [saga](https://learn.microsoft.com/en-us/azure/architecture/patterns/saga) patterns | Coordination and cross-service invariants | read |
| [Temporal](https://docs.temporal.io/evaluate/why-temporal) | Workflow engine triggers | read (vendor page) |
| [Azure stream processing](https://learn.microsoft.com/en-us/azure/architecture/data-guide/technology-choices/stream-processing), [ByteByteGo trade-offs](https://bytebytego.com/guides/10-system-design-tradeoffs-you-cannot-ignore/) | Batch or stream; minor trade-offs | read |
| Fowler on [CQRS](https://martinfowler.com/bliki/CQRS.html) and [event-driven](https://martinfowler.com/articles/201701-event-driven.html) | State model | read |
| DynamoDB [key design](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html) and [write sharding](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-sharding.html) | Hot keys | read |
| Fan-out on write or read | Feed fan-out | secondary (search summaries only) |

Ranking by reversibility draws on the
[2015 Amazon shareholder letter](https://www.sec.gov/Archives/edgar/data/1018724/000119312516530910/d168744dex991.htm)
(one-way and two-way doors, read), the
[last responsible moment](https://blog.codinghorror.com/the-last-responsible-moment/)
(secondary), [Fowler on architecture](https://martinfowler.com/architecture/)
(read), and
[Nygard on decision records](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
(read).

Not confirmed: anything from Kleppmann's *Designing Data-Intensive
Applications* (not consulted); the scheduler trigger; build or buy guidance.
The dependency order beyond its first three links, the three-factor score, and
the configuration-model fork are this skill's synthesis.

## Elements and completeness

| Source | Used for | Checked |
|---|---|---|
| [Design Docs at Google](https://www.industrialempathy.com/posts/design-docs-at-google/) | Goals and non-goals, alternatives, cross-cutting concerns | read |
| [Pragmatic Engineer on RFCs and design docs](https://blog.pragmaticengineer.com/rfcs-and-design-docs/) | Template sections across companies; which templates include support, internal tooling, privacy | read |
| [arc42](https://docs.arc42.org/home/) | Twelve-section structure | read |
| [C4 model](https://c4model.com/) | Diagram levels | read |
| Google SRE book: [production readiness review](https://sre.google/sre-book/evolving-sre-engagement-model/), [launch checklist](https://sre.google/sre-book/launch-checklist/) | Reliability, operations and rollout elements | read |
| [Twelve-factor app](https://12factor.net/) | Config and admin processes | read |
| AWS SaaS: [control and application plane](https://docs.aws.amazon.com/whitepapers/latest/saas-architecture-fundamentals/control-plane-vs.-application-plane.html), [core services](https://docs.aws.amazon.com/whitepapers/latest/saas-architecture-fundamentals/core-services.html), [design principles](https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/general-design-principles.html) | Control plane, onboarding, identity, metering | read (first is marked historical by AWS) |
| Azure multi-tenant: [control planes](https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/considerations/control-planes), [tenant lifecycle](https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/considerations/tenant-life-cycle), [checklist](https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/checklist) | Lifecycle, configuration, billing state, isolation | read |
| [EnterpriseReady](https://www.enterpriseready.io/) | Single sign-on, audit logs, roles, change management, reporting, integrations | read |
| Fowler, *Production-Ready Microservices* via a [transcribed checklist](https://gist.github.com/mikaelvesavuori/1715a45914b51de460d2b36d97d75e51) | Production readiness | secondary |

The two sources disagree on one point: AWS places tenant resource provisioning
in the application plane, Azure in the control plane.

Not confirmed in any source: schema migration and backfill, and localisation,
as named checklist items. The "most often forgotten" list is inferred.

## Practice and evaluation

| Source | Used for | Checked |
|---|---|---|
| Hello Interview [introduction](https://www.hellointerview.com/learn/system-design/in-a-hurry/introduction) and [staff-level post](https://www.hellointerview.com/blog/staff-level-system-design) | Assessment dimensions; level expectations | read |
| [interviewing.io guide](https://interviewing.io/guides/system-design-interview) | Communication, decisiveness, generic component names | read |
| Architectural Katas: [about](https://www.architecturalkatas.com/about.html), [rules](https://www.architecturalkatas.com/rules.html) | Kata format | read |
| [SystemDesign.ai](https://github.com/ccd97/SystemDesign.ai) | Customer-with-numbers role; separate reviewer; never give away the solution | read |
| Productive failure (Sinha and Kapur, 2021) | Attempt before instruction | secondary |
| Worked examples and fading (Renkl, Atkinson); expertise reversal | Learn mode; scaffolding by level | secondary |
| On-demand hints (Razzaq and Heffernan); help abuse in tutors | Hint ladder | secondary |
| Guardrailed tutoring (Bastani et al., 2025) | Hints-only help protects unassisted performance | secondary |
| Self-explanation prompts (Atkinson, Renkl, Merrill) | Asking for the reason at each decision | secondary |
| Testing effect (Roediger and Karpicke, 2006); desirable difficulties (Bjork) | Recall before rereading | secondary |
| Deliberate practice (Ericsson) | Targeting the weakest dimension | secondary |

The learning-science entries were taken from summaries and abstracts, not the
papers. They are used here for direction only, and no effect sizes are quoted.
Requiring a guess before each hint level is this skill's inference from the
help-abuse findings. The seven-dimension rubric and its level descriptions are
a synthesis of the assessment sources.
