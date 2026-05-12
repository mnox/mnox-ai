# Curriculum Design Guide

How to break a topic into modules before writing any content. Load this
file during Step 2 of the Create workflow.

## The three-phase shape

Every curriculum is structured as:

```
Phase 1 — Foundations      (vocabulary, primitives, mental models)
Phase 2 — Tools            (the machinery for working the primitives)
Phase 3 — Application      (integration, end-to-end, the goal)
```

Allocate roughly:

- 20–30% of modules to Phase 1
- 40–50% to Phase 2
- 20–40% to Phase 3

Never invert this order. Learners cannot apply what they cannot name.
Tempting as it is to "get to the practical stuff fast," front-loading
Phase 3 produces fluent pattern-matchers who cannot explain themselves
and cannot generalize.

## The canonical module slots

| # | Slot | Always-present? |
|---|------|------------------|
| 00 | Orientation — motivation, goal framing, prerequisites | Yes |
| 01–NN | Phase 1–3 content modules | Varies |
| Last | Synthesis / Capstone — end-to-end integration | Yes |

Every curriculum has `00-orientation`. Every curriculum has a final
synthesis module. What lives between is determined by topic and emphasis.

## Using the user's emphasis

Emphasized areas get 2–3 modules each. Non-emphasized but necessary
prerequisites get 1 module. Nice-to-have but skippable topics become
Supporting Material links, not modules.

Example: if the user asks for a curriculum on "the Spanish language"
and emphasizes "conversational fluency for travel," the curriculum might
split as:

- Phase 1: 01 Pronunciation & Sound Inventory, 02 Core Grammar Spine
- Phase 2: 03 High-Frequency Verbs, 04 Tenses for Daily Use,
  05 Pronouns & Connectors
- Phase 3 (emphasis): 06 Travel Survival Phrases, 07 Restaurants & Markets,
  08 Directions & Transit, 09 Cultural Register & Politeness
- 10 Synthesis

Vs the same Spanish curriculum with "reading Latin American literature"
as emphasis:

- Phase 1–2 the same through 05
- Phase 3: 06 Literary Past Tenses, 07 Regional Vocabulary,
  08 Idiom & Figurative Language, 09 Close Reading Practice
- 10 Synthesis

Same subject, different shape, because emphasis differs. The same
pattern holds for any topic — woodworking with "hand tools" vs "power
tools" emphasis, distributed systems with "consensus" vs "data
pipelines" emphasis, drawing with "figures" vs "landscapes" emphasis.

## Goal tie-in as outline driver

Before drafting the module list, write a **one-sentence goal statement**
from the user's stated long-term goal. Every module must serve that
sentence.

If a module's place cannot be defended by pointing to the goal sentence,
cut it or merge it.

Examples across domains:

- Goal: "play jazz standards by ear at a jam session" → cut modules on
  music theory notation; keep modules on ear training, common
  progressions, comping patterns, and improvisation vocabulary.
- Goal: "pass the bar exam in <state>" → cut modules on legal history;
  keep modules on the tested subjects, issue-spotting drills, and timed
  essay practice.
- Goal: "ship a personal finance app that I'd actually use" → cut
  modules on enterprise architecture; keep modules on local storage,
  data syncing, charting, and a deployable mobile shell.
- Goal: "build self-improving AI agent flywheels" → cut modules on
  generative modeling; keep modules on classification, evaluation, and
  feedback loops.
- Goal: "run a sub-3-hour marathon in 18 months" → cut modules on
  ultra-distance training; keep modules on aerobic base, threshold
  workouts, fueling, and taper protocols.

## Outline format to propose

Present to the user in this exact structure for approval:

```markdown
Proposed outline — <topic>

Goal: <the one-sentence goal you derived>
Emphasis: <the user-stated emphasis areas>
Starting level: <beginner/intermediate/advanced>
Planned module count: <N>

| # | Module | Role |
|---|--------|------|
| 00 | Orientation | Frame the goal, preview the flywheel/pipeline/system |
| 01 | ... | ... |
| 02 | ... | ... |
| ... | ... | ... |
| NN | Synthesis / Capstone | End-to-end integration |

Weighting rationale:
- <emphasis area A>: modules NN, NN (why these get deep treatment)
- <emphasis area B>: modules NN (why)

Prerequisites the learner should already have:
- <bullet>
- <bullet>

Open question: <any choice you want the user to weigh in on — e.g., "include
a numerical-methods foundation module or assume comfort with it?">
```

Wait for approval. Accept edits. Iterate. Only then proceed to scaffold.

## Depth calibration

Match module density to the starting level:

- **Beginner**: longer ELI5, shorter Deep Dive. More scaffolding, more
  examples, more spaced repetition across modules. Don't assume vocabulary.
- **Intermediate**: standard template balance. Assume undergrad-level
  prerequisites in the parent field. Introduce jargon the first time,
  then use it.
- **Advanced**: terse ELI5 (they already get the frame), dense Deep Dive
  with edge cases and recent research. Assume they'll chase the Supporting
  Material on their own.

## When to add a remediation mini-module mid-stream

Only if the prepare-next-module workflow detects a persistent gap across
two modules. Add as `NNa-remediation-<slug>.md` (note the `a` suffix to
preserve the index of the original NN module). Update the `README.md`
module map to include it. Ask the user before inserting.

## When to recommend a second curriculum

If design surfaces that the user's goal implies two large, weakly-
related bodies of knowledge, say so and offer two curricula instead of
one bloated 20-module artifact.

Example: a user wants to learn "statistics + distributed systems for a
data engineering role." These are two distinct fields with different
mental models. Two curricula, possibly cross-referencing each other,
serves the user better than a single curriculum trying to be both.

## Anti-patterns

1. **The encyclopedia**: 25+ modules because "the topic is big." Cut
   until the path is traversable in weeks, not years.
2. **The rushed synthesis**: skipping foundations to "get to the cool
   stuff." Produces learners who can imitate but not reason.
3. **The equal-weight curriculum**: N modules, each the same size,
   ignoring what the learner actually needs to go deep on.
4. **The goal-less path**: no tie to a concrete goal. Becomes a tour,
   not a curriculum.
5. **Silent design decisions**: writing files without showing the
   outline first. The user can't redirect what they can't see.
