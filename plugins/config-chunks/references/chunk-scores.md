# Chunk Scores — Universal Starter Library

These are the eight shipped universal chunks in the `config-chunks` starter
library: provider-agnostic, global-altitude engineering-discipline principles
injected into every agent session via the always-on bundle. Each was scored with
the **chunk-review 7-axis rubric** (Universality, Altitude, Not-a-skill,
Non-redundancy, Concision, Impact, Stability — 0–10 each, summed /70). Keep
threshold is **≥ 49/70**, and the verdict is capped at `revise` if Impact ≤ 2 or
Stability ≤ 2. All eight clear `keep`; seven sit within the 2000-char inline body
cap, and `problem-framing` is a `disclosure: pointer` stub (400-char cap) backed
by the `ideation` skill.

The "deletion regression" column is the Impact evidence: the one concrete
behavior that gets visibly worse if the chunk is removed.

| Chunk | Total | Verdict | Body chars |
|---|---|---|---|
| context-hygiene | 64/70 | keep | 1205 |
| problem-framing (pointer) | 61/70 | keep | 371 |
| engineering-mindset | 61/70 | keep | 1394 |
| consultative-partnership | 63/70 | keep | 1184 |
| discovery-pipeline | 62/70 | keep | 1127 |
| code-skepticism | 64/70 | keep | 1104 |
| communication-style | 60/70 | keep | 1069 |
| coding-style | 61/70 | keep | 1081 |

---

## context-hygiene v0.1.0 — 64/70 — keep

| Axis | Score | Note |
|------|-------|------|
| Universality   | 10/10 | Every agent in every session manages a context window. |
| Altitude       | 10/10 | Cross-cutting operating posture; shapes all work. |
| Not-a-skill    | 9/10  | A passive discipline, not an invokable procedure. |
| Non-redundancy | 9/10  | No platform default articulates the coordination-layer framing. |
| Concision      | 9/10  | Tight at 1205 chars; every bullet load-bearing. |
| Impact         | 9/10  | Directly changes delegate-vs-inline and stop-vs-push decisions. |
| Stability      | 8/10  | Durable principle; no versions, tools, or dates. |
| **Total**      | **64/70** | |

**Deletion regression (Impact):** Without it the agent does discovery inline,
bloating the main thread with raw file dumps until reasoning degrades mid-task.
**Rot risk (Stability):** None — no volatile specifics; the principle survives any tool change.

## problem-framing v0.1.0 — 61/70 — keep — `disclosure: pointer` → `ideation` skill

| Axis | Score | Note |
|------|-------|------|
| Universality   | 8/10  | Vague/solution-shaped openers happen to every subscriber; the stub is conditional and cheap. |
| Altitude       | 9/10  | Global interaction policy — frame before you solve, everywhere. |
| Not-a-skill    | 9/10  | Correctly split: always-on stub here, the elicitation *procedure* deferred to the `ideation` skill. |
| Non-redundancy | 9/10  | The only chunk covering elicitation; explicitly carves the "ask to elicit" exception out of consultative-partnership's "don't ask" default. |
| Concision      | 9/10  | 371-char pointer body — the imperative rule only. |
| Impact         | 8/10  | Changes whether the agent interrogates a vague ask or guesses and builds the wrong thing. |
| Stability      | 9/10  | Durable; the only volatile dependency is the `ideation` skill slug, shipped alongside. |
| **Total**      | **61/70** | |

**Deletion regression (Impact):** Without it the agent takes "I want X" literally,
builds the stated solution instead of the real need, and the non-engineer never
learns to separate the two.
**Rot risk (Stability):** Low — the `skill: ideation` reference is the only thing
that can dangle; it ships in the same plugin, so they version together.

## engineering-mindset v0.1.0 — 61/70 — keep

| Axis | Score | Note |
|------|-------|------|
| Universality   | 8/10  | Embodiment applies in every session; the teach-the-why edge peaks for non-technical operators. |
| Altitude       | 10/10 | Cross-cutting reasoning posture; shapes how every problem is approached. |
| Not-a-skill    | 9/10  | A passive way of reasoning, not an invokable procedure. |
| Non-redundancy | 8/10  | Distinct from code-skepticism — that's about existing code; this is about reasoning about the problem itself. |
| Concision      | 9/10  | 1394 chars; four facets under one frame, each load-bearing. |
| Impact         | 8/10  | Shifts the agent to system-altitude reasoning and surfaces it so the user levels up. |
| Stability      | 9/10  | Timeless engineering judgment; no tools, versions, or dates. |
| **Total**      | **61/70** | |

**Deletion regression (Impact):** Without it the agent answers at task-altitude —
solving the literal ask without naming the system, the decomposition, or the
tradeoff — and the non-engineer stays an order-taker instead of learning to reason
like a staff engineer.
**Rot risk (Stability):** None — describes durable engineering judgment, not any stack or tool.

## consultative-partnership v0.1.0 — 63/70 — keep

| Axis | Score | Note |
|------|-------|------|
| Universality   | 10/10 | Any human-facing agent benefits from load reduction. |
| Altitude       | 10/10 | Global escalation/recommendation policy. |
| Not-a-skill    | 9/10  | Always-on posture for how to surface decisions. |
| Non-redundancy | 9/10  | The structured-guess format is novel and concrete. |
| Concision      | 9/10  | 1184 chars; no padding. |
| Impact         | 9/10  | Kills a/b/c menus and buried guesses — concrete do/don'ts. |
| Stability      | 7/10  | Durable behavioral invariant. |
| **Total**      | **63/70** | |

**Deletion regression (Impact):** Without it the agent dumps a/b/c choice menus
on the human and buries unflagged guesses in confident prose.
**Rot risk (Stability):** None — describes a durable collaboration stance.

## discovery-pipeline v0.1.0 — 62/70 — keep

| Axis | Score | Note |
|------|-------|------|
| Universality   | 9/10  | Source ladder generalizes to any toolset. |
| Altitude       | 10/10 | Global "how to find an answer" policy. |
| Not-a-skill    | 8/10  | Ordered list, but it's an always-applied posture, not a one-off procedure. |
| Non-redundancy | 9/10  | Cheapest-first ordering + verify-before-assert is non-obvious. |
| Concision      | 9/10  | 1127 chars; the ladder is dense but earns it. |
| Impact         | 9/10  | Changes whether the agent greps first or looks it up first. |
| Stability      | 8/10  | Deliberately tool-agnostic, named by capability not product. |
| **Total**      | **62/70** | |

**Deletion regression (Impact):** Without it the agent jumps straight to broad
code search and asserts from recall instead of verifying against ground truth.
**Rot risk (Stability):** None — sources named generically, not by proprietary tool.

## code-skepticism v0.1.0 — 64/70 — keep

| Axis | Score | Note |
|------|-------|------|
| Universality   | 10/10 | Applies to any change in any codebase. |
| Altitude       | 10/10 | Foundational stance toward existing code. |
| Not-a-skill    | 9/10  | A reasoning posture, nothing to invoke. |
| Non-redundancy | 9/10  | Requirements-as-ground-truth framing is distinctive. |
| Concision      | 9/10  | 1104 chars; named failure mode at the end adds leverage. |
| Impact         | 9/10  | Stops blind pattern-cloning; forces requirement-first reasoning. |
| Stability      | 8/10  | Timeless engineering principle. |
| **Total**      | **64/70** | |

**Deletion regression (Impact):** Without it the agent clones a broken nearby
pattern and calls the duplication "consistency."
**Rot risk (Stability):** None — durable invariant about code vs. correctness.

## communication-style v0.1.0 — 60/70 — keep

| Axis | Score | Note |
|------|-------|------|
| Universality   | 9/10  | Every agent produces output for a reader. |
| Altitude       | 9/10  | Global output-shaping convention. |
| Not-a-skill    | 9/10  | Pure passive posture. |
| Non-redundancy | 8/10  | Altitude + canonical-vocabulary points are non-default. |
| Concision      | 9/10  | 1069 chars; tightest of the set. |
| Impact         | 8/10  | Changes lead-with-takeaway and depth-to-stakes behavior. |
| Stability      | 8/10  | Durable communication discipline. |
| **Total**      | **60/70** | |

**Deletion regression (Impact):** Without it the agent writes essays for routine
confirmations and buries recommendations under preamble and recap.
**Rot risk (Stability):** None — no volatile specifics.

## coding-style v0.1.0 — 61/70 — keep

| Axis | Score | Note |
|------|-------|------|
| Universality   | 9/10  | Applies wherever code is written, language-agnostic. |
| Altitude       | 9/10  | Global code-quality convention. |
| Not-a-skill    | 9/10  | Always-on style posture, not a procedure. |
| Non-redundancy | 8/10  | The no-`any`-escape and no-back-compat rules add teeth beyond defaults. |
| Concision      | 9/10  | 1081 chars; each bullet a distinct rule. |
| Impact         | 9/10  | Concrete do/don't: never reach for an `any` escape hatch. |
| Stability      | 8/10  | Durable; `any` is illustrative of a language-general anti-pattern. |
| **Total**      | **61/70** | |

**Deletion regression (Impact):** Without it the agent silences the type checker
with an `any`-escape and bolts on back-compat shims that calcify mistakes.
**Rot risk (Stability):** None — principles outlast any specific language or type system.
