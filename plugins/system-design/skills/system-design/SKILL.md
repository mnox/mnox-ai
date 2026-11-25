---
name: system-design
description: Turn a one-line system design exercise ("design a notification system") into a practice map instead of a finished answer. Asks only the few clarifying questions whose answers change the architecture, assumes sensible defaults for the rest, ranks the biggest hard-to-reverse forks in the road to the top with their options and tipping signals, and inventories every element the design will need (onboarding, settings and per-customer configuration, admin tooling, tenancy, billing, queues, event streams, background jobs, workflows, real-time, scale hot spots, security, operations, rollout) with a verdict on each. The learner then works the design themselves, with hints on request and a rubric review at the end. Can also produce the full requirements-clarification question set by category (scope, domain rules, personas, correctness, scale, growth and PLG, configurability, stack, sneaky unknowns), and render a hoverable 10,000-foot HTML diagram with forks, constraints and open questions marked on the boxes they affect. Use when the user says "/system-design", "system design practice", "scaffold a system design for X", "what should I be asking about this design", "what are the big decisions in designing X", "mock system design", "what questions should I ask before designing X", "diagram the unknowns", or wants to prepare for a system design interview or architecture kata. Not for producing a finished architecture, an ADR, or a production design doc.
---

# System Design

## Overview

Given as little as one sentence, produce a **design map**: the questions worth
asking, the decisions that must be made first, and an outline of everything the
design has to cover. The map is a scaffold for the learner to design against. It
is not the design.

Three rules shape everything below:

1. **Ask little.** Only ask a question if its plausible answers lead to
   different diagrams. Everything else becomes a written assumption.
2. **Forks first.** The decisions that are hard to reverse and constrain the
   most other decisions go at the top, before any component is named.
3. **Withhold the answer.** In practice mode the map names options and what
   tips the choice. It does not pick. The learner picks.

## Quick Reference

| The user says | Do | Read first |
|---|---|---|
| "design X", "scaffold X", "/system-design X" | Map (below) | `references/questions.md`, `references/forks.md`, `references/elements.md` |
| "teach me", "walk me through", "learn mode" | Map in learn mode | same, plus `references/practice.md` |
| "what should I ask", "clarify the requirements", "all the questions" | Clarify (below) | `references/questions.md` |
| "diagram it", "draw the map", "10,000-foot view" | Diagram (below) | `references/diagram.md` |
| "hint", "I'm stuck on fork 2" | Hint ladder | `references/practice.md` |
| asks a clarifying question mid-practice | Answer as the customer, with a number | the map's assumptions ledger |
| "review my design", pastes an attempt | Review | `references/practice.md` |

| Mode | Forks show | Elements show |
|---|---|---|
| `practice` (default) | options, tipping signals, cost of choosing wrong | verdict, why it is in play, a question to answer |
| `learn` | the above, plus which way this problem leans, why, and what would flip it | the above, plus one line on the usual approach |

Pick `learn` when the user asks to be taught, says they are new to the topic,
or asks for it. Otherwise use `practice`. A learner who can already attempt the
problem learns more by attempting it first.

## Workflow: Map

### Step 1: Read the prompt and classify it

From the user's sentence alone, infer and write down:

- **Shape**: product (user-facing flows), infrastructure component (rate
  limiter, cache, queue), data pipeline, or internal platform.
- **Customer model**: consumer, B2B multi-tenant, or internal. B2B pulls in the
  whole control-plane area of `references/elements.md`.
- **The distinctive part**: the one thing that makes this problem this problem
  (fan-out for a feed, contention for ticketing, ordering for chat). Name it.
  It is nearly always the first deep dive.

Do not ask the user to confirm the classification. State it in the map so they
can correct it.

### Step 2: Choose the questions

Load `references/questions.md`. Walk the ranked categories and keep a question
only if it passes the **flip test**: write the two most plausible answers; if
both lead to the same diagram, it is a detail, so assume it.

Keep **at most four**. For each, record what the answer flips and the default
that will be assumed if the user does not answer.

Ask them in one round using the host's structured clarification mechanism when
there is one, otherwise as a short numbered list. Always offer "use your
defaults". If the user answered some in their prompt, do not re-ask. If the
user says to just go, skip asking and proceed on defaults.

Never ask for derived numbers (requests per second, storage per year). Ask for
the high-level fact (daily users, items per user) and derive.

### Step 3: Rank the forks

Load `references/forks.md`. For each catalogue fork, check its tipping signals
against the prompt, the answers, and the assumptions. A fork is **live** when
the signals do not settle it, or settle it in a way the learner must be able to
justify.

Score each live fork High / Medium / Low on:

- **Reversibility**: does changing it later mean a data migration, a new
  partition key, or a broken public contract?
- **Blast radius**: how many later forks does it constrain (see the dependency
  order in `references/forks.md`)?
- **Uncertainty**: how far are the requirements from settling it?

Present the top **three to five** as forks, ordered so that a fork never
appears above one it depends on. Everything else goes in a short "reversible
defaults" list: one line each, with the default and the reason it can wait.

Add any fork the catalogue lacks but this problem has. The distinctive part
from Step 1 usually contains one.

### Step 4: Inventory the elements

Load `references/elements.md`. Give **every area** a verdict:

- `core`: the design fails without it
- `likely`: needed for a real system, optional in a 45-minute exercise
- `skip`: not in play, with the reason in a few words

Skipped areas stay in the map. Seeing what was considered and ruled out is half
of what the learner takes away. Within `core` and `likely` areas, list the
individual elements and attach one question the learner must answer about each.
Do not describe how to build them.

Explicitly check the async triggers (queue, event stream, background jobs,
scheduler, workflow engine) and the scale triggers (hot keys, fan-out, large
payloads, bursty traffic) from `references/forks.md`. State which fired and on
what signal.

### Step 5: Write the map

Fill `templates/design-map.md` in this order. The order is the point: decisions
before components.

1. Frame: one-paragraph restatement, classification, in scope, out of scope
2. Questions: asked, answered or defaulted, and what each flips
3. Assumptions ledger: every default, with a number where one applies
4. Forks: ranked
5. Element inventory: every area with a verdict
6. Reversible defaults
7. Work order and timebox
8. Deep-dive candidates: two or three, the distinctive part first
9. Self-check: the rubric from `references/practice.md`

Show the map in the conversation. Offer once to also save it as a worksheet
file with blank answer slots; if the user accepts, ask where, and never write
outside that path.

End by telling the learner the next move: resolve fork 1, then work down.

## Workflow: Clarify

Use when the user wants the full set of questions that would pin down scope,
requirements and constraints, typically to take to a stakeholder or to rehearse
a requirements conversation. The four-question limit does not apply here, and
nothing is assumed on the user's behalf.

1. Classify the prompt as in Map, Step 1.
2. Load `references/questions.md` and follow its **Full clarification**
   section: nine categories, most consequential first; within each, questions
   ordered by how much of the design the answer moves; an ID and a "decides"
   line on every question.
3. State the personas as a hypothesis to confirm, internal staff included, with
   what each expects from the system.
4. End with the five to ask first.

Offer the diagram next. The two are built to be read together: question IDs in
the list are the IDs on the diagram.

## Workflow: Diagram

Use when the user asks for a picture of the system, or after Clarify or Map
when a visual would help. Needs a filesystem and `python3`; without them,
say so and give the map in text.

1. Load `references/diagram.md` and read
   `templates/design-map.example.json`.
2. Lay out the boxes any plausible design would have: people on top, outside
   parties at the bottom, back office grouped in the last column.
3. Mark each box `fork`, `constraint`, `open` or `plain`, and attach the
   question IDs that land on it. Forks carry their options and what tips each.
   Options state signals. They do not recommend.
4. Route the edges using the rules in the reference so that no line crosses a
   box.
5. Write the data file next to where the page will go, then run:

   ```bash
   python3 <path-to-this-skill>/scripts/render_map.py --data <map.json> --output <map.html>
   ```

   Fix every error it reports and re-run. Review the warnings.
6. Look at the rendered page if the host can show it. Give the user the full
   path, and open it in their browser if the host can.

Ask where to write the files unless the user already said. Never write outside
that path.

## Workflow: Practice support

While the learner works, stay in the customer's seat.

- **Clarifying questions** get concrete answers with numbers, consistent with
  the assumptions ledger. Add new facts to the ledger.
- **"Which should I pick?"** is handed back: ask what the requirement implies,
  or which cost they would rather pay.
- **Hints** follow the three-level ladder in `references/practice.md`. Ask for
  the learner's current guess before giving the next level.
- When the learner settles a fork, ask what requirement drove the choice and
  what would make them change it. Then name the forks that choice has now
  constrained.

## Workflow: Review

When the learner brings a design, load `references/practice.md` and score it
against the rubric, one level per dimension, each backed by something specific
in their design. Report three strengths, three improvements, and the weakest
dimension. Compare their fork choices to the map's signals. A different choice
that is well argued scores as well as the usual one. Suggest the next exercise
from the weakest dimension.

## Supporting files

- `references/questions.md`: ranked question categories, what each flips, the
  flip test, defaults when unanswered, when estimation is worth doing.
- `references/forks.md`: fork catalogue with options, tipping signals and cost
  of choosing wrong; dependency order; ranking; triggers for queues, streams,
  jobs, workflows and hot keys.
- `references/elements.md`: the element inventory by area, with the trigger
  for each element, including the control plane that designs usually omit.
- `references/practice.md`: modes, timeboxes, hint ladder, rubric, review
  format.
- `references/sources.md`: the prior art this skill is built on, with links
  and notes on how well each claim was verified.
- `references/diagram.md`: what goes on the diagram, box kinds, the data
  format, layout and edge-routing rules.
- `scripts/render_map.py`: validates a diagram data file and renders the page.
- `templates/design-map.md`: the map layout.
- `templates/design-map.html`: the diagram page the script fills.
- `templates/design-map.example.json`: a complete diagram data file.

## Common Mistakes

**Producing the design.** A component diagram with every choice made leaves the
learner nothing to do. In practice mode a fork entry never contains a
recommendation, and an element entry never contains an implementation.

**Asking a checklist.** Ten clarifying questions at the start of a practice
session is an interrogation. More than four means the flip test was not
applied. The full set belongs to the Clarify workflow, where the questions are
the deliverable and each still says what it decides.

**A diagram that answers the question.** Fork boxes show options and signals.
A fork box that names the winner has turned the map into a design.

**Listing forks in catalogue order.** The catalogue is a lookup table. The map
is ranked for this problem, and a chat system and a billing system rank
differently.

**Dropping skipped areas.** An inventory that only lists what is needed hides
the reasoning. Every area appears, with a verdict.

**Leaving out the product around the product.** Onboarding, settings,
per-customer configuration, admin tooling, billing state and audit logs are
absent from most interview frameworks and present in every real system. For a
B2B prompt the control-plane area is `core` or `likely`, not `skip`.

**Vague assumptions.** "Highly available" and "large scale" are not
assumptions. Write a number or a comparison: "search may lag writes by 30
seconds", "10 million daily users, read-heavy at about 100 to 1".

**Scaling arithmetic for its own sake.** Do a calculation only when the result
picks between two designs, and say which two.

## Notes

- The skill is host-neutral. Map, Clarify, practice support and review need no
  tools beyond conversation. Only the diagram needs a filesystem and `python3`.
- The fork catalogue and question ranking are a synthesis of the sources in
  `references/sources.md`. Where a source is silent, the reference says so.
  Treat the catalogue as a starting list and add to it.
