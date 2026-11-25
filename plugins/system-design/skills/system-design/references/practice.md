# Practice

How the learner uses the map, how much help to give, and how to review an
attempt.

## Principles

1. **Attempt before answer.** Working a problem before seeing a worked solution
   tends to produce better learning than the reverse, provided the learner
   knows enough to make a real attempt. Default to `practice` mode.
2. **Scaffold to the learner.** Someone new to the pattern needs more structure
   and learns little from flailing. That is what `learn` mode is for. Worked
   examples help less as skill grows.
3. **Give questions, withhold decisions.** The map supplies what to ask and
   what must be covered. The learner supplies every choice.
4. **Hints on request, one level at a time.** Help that arrives unasked, or
   that can be clicked straight through to the answer, gets used as a shortcut.
5. **Ask for the reason at each decision.** "Which requirement drives this?"
   and "what would make you change it?" turn a choice into something that
   transfers to the next problem.
6. **Recall beats rereading.** Reading a polished breakdown feels like learning
   and mostly is not. Start a session by recalling, unaided, the pattern from
   the last one.
7. **Feedback is specific and aimed at the weakest point.** Score by dimension
   and choose the next exercise from the lowest.

## Session formats

**Timed solo, 45 minutes.** The closest to an interview.

| Minutes | Work |
|---|---|
| 5 | Requirements: top three functional, three to five quantified qualities |
| 5 | Resolve forks 1 to 3 from the map, out loud or in writing |
| 2 | Core entities |
| 5 | Interface |
| 12 | End-to-end design that satisfies the functional requirements |
| 12 | Two deep dives, the distinctive part first |
| 4 | Wrap up: bottlenecks, what you would do next, what you would monitor |

Calculation happens inside whichever step needs its result. The fork step is
this skill's addition to the usual interview sequence.

**Untimed study.** Work the map top to bottom in a document. Write a short
decision record for each fork: context, decision, consequences. Fill every
`core` and `likely` element. This is the format for the product-around-the-
product areas that a 45-minute session never reaches.

**Kata, with others.** Small teams get the same one-line prompt. One person
plays the customer and keeps time. Any technology is allowed if it can be
defended. Assumptions must be stated. Teams present, and the others ask hard
but fair questions. Unfounded assumptions and not questioning the customer are
the failing marks.

**Variation drill.** After finishing, change one assumption in the ledger
(ten times the scale, add multi-tenancy, require strong consistency) and say
which forks flip. Ten minutes.

## Playing the customer

When the learner asks a clarifying question:

- Answer with a concrete fact and a number, consistent with the ledger.
- If the ledger is silent, pick a plausible value, state it, and add it.
- Do not volunteer requirements that were not asked about.
- Do not reveal which design the answer implies.

Partway through a longer session, one new constraint may be introduced (a
second region, a large customer, a compliance requirement) to see how the
design absorbs change. Say that it is a new constraint.

## Hint ladder

Before each level, ask for the learner's current guess and reasoning. Give the
next level only after they have offered something.

| Level | Content | Example, for queue or event stream |
|---|---|---|
| 1. Point | Name the requirement or assumption that bears on the decision | "Look at how many separate things need to react to an order being placed." |
| 2. Narrow | Reduce to two options and name the trade-off between them | "It is between a work queue and a retained log. One removes the message once handled; the other lets new consumers read history." |
| 3. Tell | State the usual choice for these signals and why, and what would flip it | "Three independent consumers and a need to rebuild a projection point to a log. With a single worker and no replay, a queue would be simpler." |

After a level 3 hint, ask the learner to restate the reasoning in their own
words and note that fork for the variation drill.

## Rubric

Score each dimension 1 to 4. Every score cites something specific in the
attempt.

| Dimension | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| Problem navigation | Starts drawing components | Gathers requirements but does not prioritise | Scopes to a few core requirements and reaches a working design | Also separates routine from hard parts and spends the time on the hard ones |
| Requirements and assumptions | Vague or missing | Listed, unquantified | Quantified and written down | Each one tied to a decision it drives |
| Fork handling | Choices made silently | Options named, choice unexplained | Choice tied to a requirement, cost acknowledged | Also states what would flip it and which later decisions it constrains |
| Solution design | Pieces do not connect | Works on the happy path | Coherent end to end, starts simple, each addition justified | Also handles the stated failure modes and the distinctive part in depth |
| Completeness | Core flow only | Core plus data and interface | Covers every `core` area in the map | Covers `likely` areas too, and says what was deliberately left out |
| Technical depth | Names technologies without reasons | Correct at a surface level | One deep dive holds up under questions | Two or more, raised unprompted, including operational concerns |
| Communication | Hard to follow | Followable with effort | Clear structure, states trade-offs, admits unknowns | Also adjusts cleanly when a constraint changes |

Reading the levels against seniority, roughly: a mid-level answer reaches 3 on
navigation and design with prompting. A senior answer reaches 3 across the
board unprompted and drives its own deep dives. A staff-level answer reaches 4
on navigation, fork handling and depth, and raises production concerns
(failover, multi-region, operability, security) without being asked.

Common ways to lose marks, worth checking in every review:

- Solution before requirements.
- A long requirements list instead of a short prioritised one.
- Complexity added early with no requirement behind it.
- Arithmetic whose conclusion is only "it is a lot".
- One component in great detail before the whole exists.
- A single approach presented with no alternative.
- Product names in place of reasons.
- Availability targets with no stated cost of downtime.
- No mention of how the design fails.

## Review format

1. One line: does the design meet the functional requirements end to end?
2. Rubric table: dimension, score, evidence.
3. Three strengths, each specific.
4. Three improvements, each specific and actionable.
5. Fork comparison: for each fork in the map, the learner's choice, the signal
   it should rest on, and whether their stated reason matches. A well-argued
   unusual choice scores as high as the usual one.
6. Elements missed: `core` areas not covered.
7. Next exercise: one that stresses the weakest dimension, and one assumption
   to change for a variation drill.

Do not rewrite the learner's design into a better one. Point at what to
reconsider and let them revise.
