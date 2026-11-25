# Design map: {{exercise}}

Mode: {{practice | learn}}

## 1. Frame

{{One paragraph restating the exercise in plain terms.}}

- **Shape**: {{product | infrastructure component | data pipeline | internal platform}}
- **Customer model**: {{consumer | B2B multi-tenant | internal}}
- **Distinctive part**: {{the one thing that makes this problem hard}}
- **In scope**: {{two or three core capabilities}}
- **Out of scope**: {{what a reasonable person might expect and will not get}}

## 2. Questions

| # | Question | What the answer flips | Answer or default |
|---|---|---|---|
| 1 | {{question}} | {{decision}} | {{answer, or "default: ..."}} |

## 3. Assumptions ledger

| Assumption | Value | Source |
|---|---|---|
| {{e.g. daily active users}} | {{number}} | {{asked | default | derived}} |

## 4. Forks, in the order to resolve them

### Fork 1: {{name}}

- **Why first**: {{reversibility / blast radius / uncertainty, in a sentence}}
- **Options**: {{A}} | {{B}} | {{C}}
- **Tips toward A when**: {{signal}}
- **Tips toward B when**: {{signal}}
- **Cost of choosing wrong**: {{what it takes to undo}}
- **Constrains**: {{later forks and elements}}
- **Your decision**: ______
- **Driven by**: ______
- **Would change if**: ______

{{Learn mode only, before "Your decision":}}
- **Leans**: {{option}}
- **Because**: {{requirement or assumption}}
- **Would flip if**: {{change in requirements}}

{{Repeat for three to five forks.}}

## 5. Element inventory

Mechanisms triggered: {{queue | event stream | background jobs | scheduler | workflow engine | none}}, on {{signal for each}}.
Scale concerns triggered: {{hot keys | fan-out | large payloads | bursts | none}}, on {{signal for each}}.

| Area | Verdict | Why |
|---|---|---|
| A. Framing | {{core}} | {{reason}} |
| B. Product surface | {{core / likely / skip}} | {{reason}} |
| C. Control plane and tenancy | | |
| D. Billing and metering | | |
| E. Data | | |
| F. Interfaces | | |
| G. Async and eventing | | |
| H. Security and compliance | | |
| I. Reliability and scale | | |
| J. Operations | | |
| K. Delivery and rollout | | |
| L. Cost | | |

### {{Area in play}}

| Element | In play because | Answer this | Your answer |
|---|---|---|---|
| {{element}} | {{trigger that fired}} | {{question}} | ______ |

{{Repeat for each core and likely area.}}

## 6. Reversible defaults

Decide these quickly and move on. Each can be changed later without a
migration.

| Decision | Default | Why it can wait |
|---|---|---|
| {{decision}} | {{default}} | {{reason}} |

## 7. Work order

1. Resolve forks 1 to {{n}}, in order.
2. Name the core entities.
3. Sketch the interface, one call per core capability.
4. Draw the simplest end-to-end design that meets the functional requirements.
5. Fill the `core` elements.
6. Deep dives.
7. Fill the `likely` elements.
8. Wrap up: bottlenecks, failure modes, what you would watch in production.

Timebox: {{45-minute split, or "untimed"}}.

## 8. Deep-dive candidates

1. {{The distinctive part}}: {{the question to answer}}
2. {{Second}}: {{question}}
3. {{Third}}: {{question}}

## 9. Self-check

Score yourself 1 to 4 after your attempt, then ask for a review.

| Dimension | Score | Evidence |
|---|---|---|
| Problem navigation | | |
| Requirements and assumptions | | |
| Fork handling | | |
| Solution design | | |
| Completeness | | |
| Technical depth | | |
| Communication | | |
