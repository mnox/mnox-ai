# Curriculum Meta — How the Adaptive Loop Works

This file defines the rules the agent uses to convert answers into
adaptations of future modules. It is both documentation and the
authoritative instruction file the agent reads before assessing
responses.

## The Assessment Record Schema

Each Understanding Check question produces one JSONL row in
`assessments/responses.jsonl`:

```json
{
  "timestamp": "2026-04-17T14:22:00Z",
  "module": "03-<module-slug>",
  "question_id": "q2",
  "question": "<the Understanding Check question as written in the module>",
  "response": "<learner's raw answer, verbatim — no edits, no cleanup>",
  "assessment": {
    "understanding_level": 3,
    "rubric": {
      "conceptual_accuracy": 3,
      "vocabulary_fluency": 2,
      "ability_to_apply": 3,
      "confidence_calibration": "appropriately_uncertain"
    },
    "strengths": ["<one or more specific strengths surfaced in the answer>"],
    "gaps": ["<concepts the learner has not yet connected>"],
    "misconceptions": ["<specific false beliefs displayed, if any>"],
    "notes": "<free-form observations about evidence, hedging, vocabulary>"
  },
  "adaptation": {
    "revisit_before_next_module": ["<topic phrases the next-module writer can search against>"],
    "accelerate": [],
    "emphasize_in_next_module": [],
    "followup_question": "<a sharper or diagnostic version of the question, or null>"
  }
}
```

### Understanding Level Rubric (0-5)

| Level | Meaning |
|-------|---------|
| 0 | No engagement or complete misunderstanding |
| 1 | Recognizes the words but cannot explain them |
| 2 | Can parrot a definition; no working mental model |
| 3 | Working mental model; can explain in own words; some rough edges |
| 4 | Can apply to novel scenarios; can spot errors in others' explanations |
| 5 | Can teach it; connects it to adjacent concepts unprompted |

Target for progression: **level 3 or higher** on all questions in a
module before advancing.

## Adaptation Rules

1. **Before a new module** is presented to the learner, the agent reads
   the last N entries in `responses.jsonl` (where N = questions in prior
   module + rolling 10).
2. The agent identifies the top 3 **open gaps** — gaps flagged for
   `revisit_before_next_module` that have not yet been resolved by a later
   answer scoring ≥3.
3. The agent rewrites or prefixes the upcoming module with a short
   `<!-- bridge:auto -->` section that re-hits those gaps using a fresh
   angle (new example, new analogy, concrete code).
4. If a gap persists across **two** modules, the agent pauses the
   curriculum and inserts a remediation mini-module before continuing.
5. If `accelerate` is flagged consistently (≥3 instances), the agent
   compresses the next module's ELI5/Core and expands the Deep Dive.
6. Misconceptions are logged in `assessments/misconceptions.md` with a
   counter. Recurring misconceptions get named and explicitly refuted in
   later modules.

## How Questions Evolve

Each module ships with a **default** Understanding Check. The agent
replaces or augments it based on prior assessments:

- **If prior responses show weak vocabulary** → add definitional recall
  questions.
- **If prior responses show strong recall but weak application** →
  replace recall with scenario questions.
- **If prior responses show misconceptions** → insert a "trap" question
  designed to surface whether the misconception persists.
- **If prior responses show mastery** → escalate to synthesis questions
  spanning multiple modules.

## Rules for the Agent When Assessing

1. **Never grade harshly**. The goal is signal, not score.
2. **Always identify at least one strength**, even in a weak answer.
   Strengths anchor learning.
3. **Distinguish "does not know" from "cannot articulate"**. A probing
   follow-up resolves the ambiguity. Flag uncertainty explicitly in
   `notes`.
4. **Calibrate confidence**. If the learner hedges appropriately, note
   it as a strength (epistemic humility). If they assert a wrong thing
   confidently, flag the overconfidence.
5. **Preserve the verbatim response**. Paraphrasing loses signal. The
   raw `response` field is the training data.
6. **Never fabricate** a level-3 when the evidence is level-1. Stale
   signal pollutes every downstream adaptation.

## Cross-Module Synthesis

After every 3 modules, the agent generates a **synthesis question** that
spans them, written to `assessments/synthesis_prompts.md`. The learner
answers at their pace; the response goes into the same JSONL with
`module: "synthesis-<n>"`.

## Re-Entry Protocol

When a new session starts and the learner wants to resume:

1. The agent reads the user's memory and this curriculum's
   `assessments/progress.md`, `responses.jsonl`, and `misconceptions.md`.
2. The agent summarizes: "Here's where you are: last module complete =
   X, open gaps = Y, next module = Z. Shall I prep Z with the bridge
   section for those gaps?"
3. The learner confirms. The agent proceeds.

## Files the Agent Writes

- `assessments/responses.jsonl` — appended per question (never rewritten).
- `assessments/misconceptions.md` — running ledger of recurring
  misconceptions.
- `assessments/synthesis_prompts.md` — cross-module prompts.
- `assessments/progress.md` — rewritten by `compute_progress.py` from the
  JSONL.

## Files the Agent Does Not Touch Without Permission

- Module files (`modules/*.md`) — the agent may propose edits but the
  learner confirms. Exception: a generated `<!-- bridge:auto -->` prefix
  section at module start is auto-inserted and clearly delimited so it
  can be rolled back cleanly.
