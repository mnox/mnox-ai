# Judge Rubric — Skill Design-Quality Scoring

The **judge** stage scores a finished skill on design quality (not just structure —
that's `validate_skill.py`'s job). It answers "is this a *good* skill," not "is this
a *well-formed* skill." Consolidated from the canonical `skill-judge` dimensions.

**Contents**
- [How to score](#how-to-score)
- [The 8 dimensions (120 pts)](#the-8-dimensions-120-points)
- [Grades](#grades)
- [The 6 failure patterns](#the-6-failure-patterns)
- [Verify-before-report gate](#verify-before-report-gate)
- [Relationship to util-review](#relationship-to-util-review)

## How to score

For each dimension: read the criteria, assign a score with a **one-line
justification**, and note a specific improvement if below max. Never inflate a score
because a skill "looks professional" or is well-formatted — formatting is not quality.
A skill that adds no expert knowledge fails regardless of polish.

## The 8 dimensions (120 points)

| # | Dimension | Pts | The question it answers |
|---|---|---|---|
| **D1** | **Knowledge Delta** ⭐ | **20** | Does the skill add genuine expert knowledge the model lacks? *The core dimension.* If the body only restates what a capable model already knows, instant ≤5. |
| D2 | Mindset + Appropriate Procedures | 15 | Does it install the right *approach*, and give exact procedures only where the task is fragile/destructive (low freedom) vs. prose where it's open (high freedom)? |
| D3 | Anti-Pattern Quality | 15 | Are the "Common Mistakes" real, specific failure modes the author has actually hit — not filler? Each ❌ should be one a smart model would otherwise commit. |
| D4 | Specification Compliance (esp. Description) | 15 | Frontmatter valid; **description states what + when in third person, front-loaded**; required sections present; naming legal. The description carries the most weight — it's the trigger. |
| D5 | Progressive Disclosure | 15 | L1 metadata / L2 body (<500 lines, <5k tokens) / L3 references one level deep, each loaded only when needed? Big skills split correctly? |
| D6 | Freedom Calibration | 15 | Degrees of freedom matched to task fragility — not over-specified for open tasks, not under-specified for destructive ones. |
| D7 | Pattern Recognition | 10 | Does it pick the right skill archetype (technique / reference / process / workflow) and follow that shape consistently? |
| D8 | Practical Usability | 15 | Would this actually fire at the right moment and produce the outcome end-to-end? Realistic examples, no orphaned references, closed loops. |

**Max = 120.** Score each, sum, grade.

## Grades

| Total | % | Grade | Meaning |
|---|---|---|---|
| 108–120 | 90+ | A | Ship. Expert-grade. |
| 96–107 | 80–89 | B | Solid; address sub-80% dimensions. |
| 84–95 | 70–79 | C | Usable but leaky — fix D1/D4/D8 first. |
| 72–83 | 60–69 | D | Structural pass, weak knowledge delta. Rework. |
| <72 | <60 | F | Do not ship. Likely a tutorial or a dump. |

## The 6 failure patterns

Name the pattern when you see it — it's faster than enumerating every sub-flaw.

1. **The Tutorial** — teaches the model what it already knows (zero knowledge delta). Fix: cut to the non-obvious *why* / the company-specific facts.
2. **The Dump** — a 900-line SKILL.md that never splits into references. Fix: L2 ≤500 lines, push detail to `references/`.
3. **The Orphan References** — `references/*.md` the body never points to (or points to without "read this"). Fix: add explicit "read X before Y" at the decision point.
4. **The Checkbox Procedure** — steps with no judgment, just ceremony. Fix: replace with the actual reasoning or a script.
5. **The Vague Warning** — "be careful with edge cases" with no specifics. Fix: name the exact edge case and the exact handling.
6. **The Invisible Skill** — a description so generic it never triggers. Fix: front-load distinctive trigger keywords; state *when*.

## Verify-before-report gate

**Mandatory** (promoted to doctrine from schema-review / compliance-review / debut,
which each reinvented it). Before any Critical/High finding ships in the judge
report, **re-verify it in the main context** — sub-agents over-report. Demote or drop
anything that doesn't survive re-reading the actual file. This gate is the line
between a deliverable and noise.

## Relationship to util-review

This rubric scores **design quality**. For the broader Claude-Code-artifact review
(hooks, CLAUDE.md, configs, side effects, security, unclosed loops), the judge stage
**invokes `util-review`** rather than duplicating its check-catalog — one catalog, no
drift. Use this rubric for the skill-specific design dimensions; defer the
cross-cutting checks to util-review.
