# Assessment Rubric and Rules

Authoritative rules for grading Understanding Check answers. Load this
file before running the Assess workflow. The curriculum-meta.md shipped
in every generated curriculum also contains this content (copied from
`assets/curriculum-meta.md`).

## Understanding Level (0–5)

| Level | Meaning | Typical Evidence |
|-------|---------|------------------|
| 0 | No engagement or complete misunderstanding | Empty, off-topic, or directly contradicts the premise |
| 1 | Recognizes the words but cannot explain them | Definitions echoed without comprehension, confidently wrong in key places |
| 2 | Can parrot a definition; no working mental model | Correct-sounding but cannot apply; breaks on novel scenarios |
| 3 | Working mental model; can explain in own words; some rough edges | Fresh phrasing, small errors that don't invalidate the core answer, spot-on examples |
| 4 | Can apply to novel scenarios; spots errors in others' explanations | Correct + extends the question with relevant implications; catches subtle traps |
| 5 | Can teach it; connects to adjacent concepts unprompted | Unprompted links to other modules, new analogies, surfacing non-obvious edge cases |

**Target for progression**: level 3 or higher on *all* questions in a
module before advancing.

## Sub-rubric (assessment.rubric fields)

Each assessment row also records three 0–5 sub-scores plus a calibration
category. All required in the JSONL.

- **conceptual_accuracy** (0–5): how right is the substance?
- **vocabulary_fluency** (0–5): can they use the field's terms correctly?
- **ability_to_apply** (0–5): could they do something with this?
- **confidence_calibration** (enum): one of
  - `appropriately_uncertain` — hedges where hedging is right
  - `overconfident` — asserts wrong things confidently, or confident where
    uncertainty is warranted
  - `underconfident` — hedges on correct answers; doubts that shouldn't exist

Overconfidence and underconfidence are both worth calling out in `notes`.

## Non-negotiable rules

### Preserve the verbatim response

Always copy the learner's response into `response` unchanged. Do not
"clean up," paraphrase, correct, or restructure it. The raw text is the
training data — specifically the signal about vocabulary, hedging, and
structure. Put analysis in `assessment.notes`.

### Always name at least one strength

Every answer — even level 0 — gets at least one entry in `strengths`.
Possible strengths: hedged appropriately, chose a correct example,
asked a clarifying question, recognized the type of problem, used
vocabulary correctly in one place. Strengths anchor future learning;
a curriculum that only surfaces gaps dries up.

### Grade the answer, not the learner

Two independent rules apply at once:

- Do not inflate levels to encourage. Stale signal degrades the whole
  adaptation loop.
- Do not deflate levels out of harshness. Under-reported levels falsely
  trigger remediation and stall the curriculum.

The fix is to describe the evidence. Every row's `notes` field should
say, in one or two sentences, *what specifically* in the learner's
response produced the level.

### Distinguish "does not know" from "cannot articulate"

If the answer is weak but it's unclear whether the learner lacks the
concept or lacks the language, say so in `notes` and propose a
`followup_question` in `adaptation` that disambiguates.

### Never fabricate levels higher than the evidence

If there's no evidence the learner reaches level 3, record level 1 or 2.
Optimism here is noise downstream.

### One row per question

Never bundle two questions into one row. The JSONL becomes unqueryable.
If the learner combined answers into one paragraph, split the paragraph
across rows with the relevant sentences quoted verbatim into each
`response` field.

## What `adaptation` fields mean

Each row carries four adaptation fields used by the prepare-next-module
workflow:

- **revisit_before_next_module** (list of strings): topics to bridge at
  the start of the next module. Use phrases the next-module writer can
  search against.
- **accelerate** (list of strings): areas where mastery is evident and
  the next module can compress. Populating this is as important as
  populating the gaps list.
- **emphasize_in_next_module** (list of strings): topics to lean into
  regardless of whether there's a gap — signals the learner is engaged
  and ready for depth.
- **followup_question** (string or null): a sharper version of the
  current question, or a diagnostic, to ask in the next session. Null if
  none needed.

## What `misconceptions` means

A misconception is a specifically-named false belief the learner
displayed. Not a gap; not "doesn't know" — they know *something* and it's
wrong. Examples across domains:

- "thinks precision and accuracy are synonyms" (statistics)
- "believes the subjunctive mood is just formal indicative" (language)
- "treats DNS TTL as a hard expiry rather than a guideline" (networking)
- "conflates legato with slur" (music)
- "expects compound interest to grow linearly over short windows" (finance)

If the same misconception appears in two different rows, flag it in the
curriculum's `assessments/misconceptions.md` with a counter. On the
third appearance, pause curriculum progress and propose a remediation
mini-module (see `curriculum-design.md`).

## Cross-module synthesis cadence

After every 3 content modules, write a synthesis question spanning them
into `assessments/synthesis_prompts.md` (create the file if it doesn't
exist). Synthesis answers go into the same JSONL with a module value
like `synthesis-3` or `synthesis-6`.

Synthesis rows use the same schema and rubric, with one convention: a
level 4+ score on a synthesis question implies a level-3-minimum on the
constituent modules. A low synthesis score with high per-module scores
means the learner has pieces without integration — flag an integration
exercise for the next-to-next module.

## Anti-patterns in assessment

1. **The flattery grade**: level 3 on a weak answer to avoid discouraging
   the learner.
2. **The harshness grade**: level 1 on a decent answer because it wasn't
   worded the way the agent would word it.
3. **The paraphrase**: editing the learner's response before storing it.
4. **The lumped row**: multi-question answers recorded as one row.
5. **The silent misconception**: spotting a wrong belief but not
   recording it in `misconceptions` or `misconceptions.md`.
6. **The adaptive silence**: skipping `adaptation` fields or populating
   them with empty arrays when they should be informative. Empty is fine
   when genuinely empty — not as a default.
