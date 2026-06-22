---
name: chunk-review
description: Score a candidate guidance chunk for inclusion in the always-on agent-instruction bundle (the concatenated context injected into every agent session). Use when reviewing or authoring a chunk before opening a chunk PR, or when asked to "/chunk-review", "score this chunk", "review a guidance chunk", "review this chunk", "is this chunk worth shipping", "should this go in the bundle", or "is this chunk-worthy". Applies a 7-axis rubric (Universality, Altitude, Not-a-skill, Non-redundancy, Concision, Impact, Stability), enforces hard size gates, checks for redundancy against existing chunks, and emits a score plus a keep / revise / cut verdict.
---

# chunk-review

## Overview

A guidance chunk is a block of agent instruction that gets concatenated into an
**always-on context bundle** — injected into *every* agent session for every
subscriber, in every provider that imports the bundle, forever. That is
expensive, permanent real estate: it costs context tokens on every turn and it
competes for the model's attention with every other chunk. This skill is the
quality gate that keeps the bundle lean, high-signal, and genuinely
behavior-changing.

Use it to score a candidate chunk, assign a verdict, and check it against
existing chunks for redundancy **before a chunk PR is opened**.

The 7 axes split into two families:
- **Does it belong here?** — Universality, Altitude, Not-a-skill, Non-redundancy.
- **Does it earn its tokens?** — Concision, Impact, Stability. (These three are
  the always-on-context tax filter: a chunk can be perfectly on-topic and still
  be noise if it changes no behavior, churns constantly, or is bloated.)

## Input

A chunk file (template-conformant — frontmatter + body). Either a path, a paste,
or a diff. If reviewing an authored-but-unsaved chunk, score the proposed content.

## Step 1 — Validate the frontmatter

The chunk MUST have all required keys. Reject outright (score 0, verdict
`cut`) if any are missing or malformed:

- `name` — unique, kebab-case (the dedup key)
- `version` — semver
- `owner` — the owning plugin slug
- `order` — integer sort key
- `summary` — one line

**Optional progressive-disclosure keys:**

- `disclosure` — `inline` (default) or `pointer`. A `pointer` chunk MUST also
  set `skill:`. Its body should be a 1–3 line *rule* only; the heavy how-to
  lives in the named skill (loaded on demand, not in always-on context).
- `skill` — required iff `disclosure: pointer`. Kebab-case skill slug. If the
  named skill isn't installed or shipped alongside this chunk, flag it in the
  recommendation — a pointer to a skill nobody has is dead context.

## Step 1b — Size gate (hard fail / auto-fail)

Strip the frontmatter and measure the body in characters
(`awk 'BEGIN{c=0} c<2 && /^---[[:space:]]*$/{c++; next} c>=2{print}' file | wc -c`).

Hard caps (chunks above these → **auto-fail**, score 0, verdict `cut`, recommend split):

| disclosure | cap (chars) | rationale |
|---|---|---|
| `inline` (default) | **2000** | ~500 tokens of always-on context tax in every session for every subscriber. |
| `pointer` | **400** | A pointer chunk is supposed to be a stub; anything bigger means the rule has crept into the always-on path. |

A chunk in the 75–100% band of its cap is *borderline* — dock the **Concision**
axis and recommend trimming or splitting before merge.

## Step 2 — Score the rubric (0–70)

Seven axes, **0–10 points each**, summed to a total out of **70**. Score each
axis on its own evidence; do not average them. Use the anchors below.

### Axis 1 — Universality
*Is this useful to every subscriber, regardless of team, project, or stack?*
- **10** — Genuinely applies in *every* session for *every* subscriber.
- **5** — Useful to a broad slice, irrelevant to a meaningful minority.
- **0** — Niche; matters to one team, one repo, or one workflow.

### Axis 2 — Altitude
*Does it belong at the always-on / global level, vs. a project-local file or a task?*
- **10** — Cross-cutting policy or convention that should shape work everywhere.
- **5** — Mostly global but leaks project- or stack-specific detail.
- **0** — Belongs in a project-local instructions file, or is really a one-off task.

### Axis 3 — Not-a-skill
*Is it always-on guidance, vs. an on-demand procedure?*
- **10** — Must passively shape *every* response; nothing to "invoke."
- **5** — Mostly a posture, but carries procedural how-to that could be deferred.
- **0** — Procedural / step-by-step; should be a skill, loaded when needed.

### Axis 4 — Non-redundancy
*Does it add something platform defaults and existing chunks don't already cover?*
- **10** — Novel; no existing chunk or platform default says this.
- **5** — Partial overlap with an existing chunk; could merge or re-scope.
- **0** — Restates a platform default or duplicates an existing chunk (see Step 3).

### Axis 5 — Concision
*Does every line earn its tokens?*
- **10** — Tight, bounded, no padding; well under its size cap.
- **5** — Serviceable but loose; or in the 75–100% cap band.
- **0** — Rambling, padded, or unbounded; context cost outweighs value.

### Axis 6 — Impact (behavioral leverage)
*Would omitting this chunk visibly degrade agent behavior — or is it low-leverage
noise the model already does, ignores in practice, or treats as decoration?*

High-signal context engineering means finding the *smallest set of high-signal
tokens that maximize the likelihood of the desired behavior*; instructions
change behavior only when they give the model **concrete signals for a desired
output**, not vague restatements of the obvious. A chunk with no behavioral
leverage is pure tax — it dilutes the signal-to-noise ratio of the whole bundle.

- **10** — Directive and consequential. Removing it would produce *visibly worse*
  output (wrong default, skipped check, missed convention). Gives a concrete,
  actionable signal — a real "do/don't" with teeth.
- **5** — Plausibly helpful but soft. Nudges tone or preference; hard to point at
  a behavior that would change if it were deleted.
- **0** — Decorative, obvious, or ignored-in-practice. States what the model
  already does by default, is too vague to act on, or is aspirational fluff.

> Heuristic: write the one-sentence regression you'd expect if this chunk were
> deleted. If you can't name a concrete behavioral regression, it's a 0–3.

### Axis 7 — Stability (durability / low-churn)
*Does this encode a durable invariant, or a volatile specific that will rot?*

Always-on context should carry **durable principles and heuristics**, not
volatile facts. Specifics — names, versions, dates, current-sprint details,
tool flags, people, URLs — go stale silently and cause drift: the bundle keeps
asserting something that is no longer true, and the model follows stale guidance
with full confidence. Durable guidance sits at the "right altitude": specific
enough to steer behavior, general enough to survive change without edits.

- **10** — Durable invariant or principle. Would still be correct a year from now
  with no edits. No version numbers, dates, or named transient specifics.
- **5** — Mostly durable but pinned to something semi-stable (a tool name, a
  current convention) that may shift within a year.
- **0** — Volatile detail with a short shelf life (versions, dates, sprint/quarter
  specifics, a current person/owner, a soon-to-change flag). Will rot and mislead.

> Heuristic: ask "what has to change in the world for this line to become a lie?"
> If the answer is "a routine, frequent event," it's a 0–3 — push the volatile
> part out to a skill, a project-local file, or a lookup, and keep only the
> durable rule here.

## Step 3 — Similarity check

Compare the candidate against every existing chunk in the bundle's `chunks/`
sources:

- Overlapping `name` → **hard conflict** (same dedup key; one silently loses).
  The PR must rename or supersede.
- Chunks covering the same subject → recommend merge, a clear `order`
  separation, or dropping the weaker one.
- Quote the overlapping lines so the author sees the redundancy.

Feed the result into the **Non-redundancy** axis.

## Step 3b — Disclosure fit

Pointer chunks deserve their own check:

- The body MUST be a rule (imperative, always-applies), not a procedure. If it
  reads like "here's how to do X," the procedure belongs entirely in the
  referenced skill and the chunk shouldn't exist inline.
- The `skill:` slug must resolve to a skill the subscriber will actually have
  installed (same plugin, or a documented dependency).
- If an inline chunk is over the 75% size band AND its procedural detail could
  auto-load via a skill description, recommend conversion to `pointer` with a
  sibling skill. This also lifts its Concision and Impact scores.

## Step 4 — Verdict

Total the seven axes (out of 70), then map to a verdict. Auto-fail conditions
(missing/malformed frontmatter, or body over its hard size cap) force `cut`
regardless of any partial scoring.

| Verdict | Band | Meaning |
|---|---|---|
| **`keep`** | **≥ 49 / 70** (~70%), no hard conflict | Chunk-worthy. Ship it. |
| **`revise`** | **28–48 / 70** (~40–69%) | Right idea, wrong shape. Fix the weak axes (often the wrong vehicle, redundancy, low Impact, or volatile content) and re-score. Includes "move elsewhere" — project-local file, a skill, a plugin README, or team docs. |
| **`cut`** | **< 28 / 70** (~<40%), or any auto-fail | Should not exist as a chunk. |

Additional hard gates that cap the verdict at `revise` even on a high total:
- **Impact ≤ 2** — low behavioral leverage means it's tax, not signal. Don't
  keep it until you can name the regression its absence would cause.
- **Stability ≤ 2** — volatile content will rot the bundle. Don't keep it until
  the volatile part is pushed out and only the durable rule remains.

## Output format

```
## chunk-review: <name> v<version>  ·  disclosure=<inline|pointer>

**Score: <0-70>**  ·  **Verdict: keep | revise | cut**
**Body size:** <chars> / <cap>  (<inline|pointer>)

| Axis | Score | Note |
|------|-------|------|
| Universality   | x/10 | ... |
| Altitude       | x/10 | ... |
| Not-a-skill    | x/10 | ... |
| Non-redundancy | x/10 | ... |
| Concision      | x/10 | ... |
| Impact         | x/10 | ... |
| Stability      | x/10 | ... |
| **Total**      | **x/70** | |

**Similarity check:** <conflicts / overlaps found, or "clear">
**Disclosure fit:** <pointer-ok / pointer-skill-missing / consider-pointer / n/a inline-ok>
**Deletion regression (Impact):** <one sentence: what gets visibly worse without this chunk, or "none — low leverage">
**Rot risk (Stability):** <what would make this line a lie, or "none — durable">

**Recommendation:** <one paragraph — if not `keep`, name the fix or the right home>
```

Be blunt. The bundle is shared and permanent; a soft review here is a tax on
every subscriber, in every session, forever.

## Grounding

The two newest axes are grounded in current context-engineering practice:

- **Impact** operationalizes the signal-to-noise principle: context is finite and
  precious, so the goal is the *smallest set of high-signal tokens* that change
  behavior — instructions only steer the model when they give *concrete signals
  for a desired output*, not vague or obvious restatements. Adding low-leverage
  text actively worsens output by diluting signal and burying real instructions
  in noise. (Anthropic, *Effective context engineering for AI agents*; Prompt
  Engineering Guide, *Context Engineering*.)

- **Stability** operationalizes durability vs. brittleness: always-on artifacts
  should encode durable instructions at the "right altitude" — *specific enough
  to guide behavior, flexible enough to provide strong heuristics* — and avoid
  brittle, hardcoded specifics that create fragility and maintenance burden.
  Volatile detail causes *context rot* and *version drift*, where the bundle
  keeps asserting stale facts the model then follows confidently. (Anthropic,
  *Effective context engineering for AI agents*; Mizrahi et al., *State of What
  Art? A Call for Multi-Prompt LLM Evaluation*, on prompt brittleness.)

Sources:
- Anthropic — Effective context engineering for AI agents: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Prompt Engineering Guide — Context Engineering: https://www.promptingguide.ai/agents/context-engineering
- Mizrahi et al. — State of What Art? A Call for Multi-Prompt LLM Evaluation (arXiv 2401.00595): https://arxiv.org/html/2401.00595v3
