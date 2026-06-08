---
name: curriculum
description: Use when the user wants to learn a topic deeply — asks for a curriculum, learning path, self-study plan, study guide, syllabus, or says teach me X. Generates a structured, adaptive curriculum directory of markdown modules (ELI5 → Core Concepts → Deep Dive → Supporting Material → Understanding Check) plus an append-only JSONL assessment log that adapts future modules to the learner's answers. Tailors depth and emphasis to the learner's long-term goal.
---

# Curriculum

## Overview

Generate a structured, adaptive learning curriculum for any topic the user wants to master. Each curriculum produces a directory of markdown modules with a uniform spine, plus an assessment-loop substrate (`curriculum-meta.md`, `responses.jsonl`, `progress.md`, `misconceptions.md`) that lets the agent adapt later modules to the learner's answers.

The skill has four workflows: **Create** a new curriculum, **Assess** the learner's Understanding Check answers, **Prepare** the next module with gap-remediation bridges, and **Resume** a paused curriculum in a later session.

## Quick Reference

| Scenario | Workflow | Primary script |
|----------|----------|----------------|
| User asks for a new curriculum on topic X | Create (below) | `scripts/scaffold.py` |
| User pastes answers to an Understanding Check | Assess (below) | `scripts/append_assessment.py` + `scripts/compute_progress.py` |
| User says "ready for the next module" | Prepare (below) | — (reads JSONL, edits next module) |
| User returns after a gap: "where was I?" | Resume (below) | — (reads MEMORY.md + progress.md) |

| File in a generated curriculum | Purpose |
|---|---|
| `README.md` | Curriculum map, module table, how to use |
| `curriculum-meta.md` | Adaptation rules + JSONL schema (copied from `assets/`) |
| `modules/00-orientation.md` | Motivation, goal framing, prerequisites |
| `modules/NN-*.md` | Each module follows the 5-part spine |
| `assessments/responses.jsonl` | Append-only log of (question, answer, assessment) rows |
| `assessments/progress.md` | Per-module status table (rewritten by `compute_progress.py`) |
| `assessments/misconceptions.md` | Running ledger of recurring misconceptions |

## Workflow: Create a new curriculum

### Step 1 — Gather Inputs

Ask these questions using the host's structured clarification mechanism when
available; otherwise ask concise plain-text questions:

1. **Topic**: what is the subject? (free text)
2. **Long-term goal**: what is the user ultimately trying to be able to *do* with this knowledge? The goal reframes every module.
3. **Emphasis areas**: which sub-topics need the deepest coverage? (multi-select or free text)
4. **Starting level**: beginner / intermediate / advanced.
5. **Output directory**: absolute path where the curriculum will be written (e.g., `./<topic>-learning` or any directory the user chooses). Default: propose `./<kebab-topic>-learning` in the current working directory.
6. **Approximate module count**: 8–12 is the default range; allow override.

If the user has already stated some of these in the prompt, skip those questions — do not re-ask.

### Step 2 — Design and propose the outline

Before writing any files, design the module list and present it for approval. Follow the guide in `references/curriculum-design.md`.

Core principles:

- **Order**: foundations → tools → application/synthesis. Never invert.
- **Shape**: `00-orientation` is always present (motivation + goal framing). A final `NN-synthesis` module is always present (end-to-end integration). The middle modules deliver the substance.
- **Emphasis weight**: devote 2–3 modules to each user-emphasized area. Bare topics get one module.
- **Goal tie-in**: every module includes an explicit connection to the user's long-term goal. This is not decoration — it is the load-bearing mental scaffolding.
- **Understanding Check** questions escalate from recall → application → synthesis across the curriculum. The final module always includes at least one cross-module synthesis question.

Present the proposed outline as a numbered list: `NN — title — one-line summary — flywheel/goal role`. Ask for approval or edits. **Do not proceed to scaffolding until the user approves.**

### Step 3 — Scaffold the directory

Once the outline is approved, run:

```bash
python3 <path-to-this-skill>/scripts/scaffold.py --output-dir <absolute_output_dir>
```

This creates the directory structure and copies the topic-agnostic template files (`curriculum-meta.md`, `assessments/misconceptions.md`, empty `assessments/responses.jsonl`, initial `assessments/progress.md`). It does **not** write `README.md` or module files — those are topic-specific and the agent writes them next.

If the script reports `output_dir_exists_nonempty`, ask the user how to proceed (overwrite, pick a new path, abort).

### Step 4 — Write `README.md`

The README must include:

- **North Star** section stating the user's long-term goal in their own language.
- **How this curriculum works** — the 5-part module spine.
- **Module map** — a table with `# | Module | Core Theme | Goal Role`.
- **How to Work a Module** — read → skim links → answer Understanding Check → hand answers to agent for assessment → proceed.
- **Prerequisites** — what the learner needs to already have.
- **Tools you'll want** — any software/libraries that support hands-on work in later modules.

Write it to `<output_dir>/README.md`.

### Step 5 — Write the module files

For each planned module, follow the template in `references/module-template.md`. Every module has:

1. **ELI5** — the concept in plain language, no jargon, 3–6 sentences.
2. **Core Concepts** — the real definitions, mental models, formulas. Dense but readable.
3. **Deep Dive** — the non-obvious stuff. Worked examples, gotchas, tradeoffs. This is the longest section.
4. **Supporting Material** — 4–8 curated links (books, papers, videos, docs, libraries) with a short note on each. Do not pad. Quality over quantity.
5. **Understanding Check** — 5–8 questions. Mix recall, application, and trap/synthesis.

Write files as `<output_dir>/modules/NN-slug.md` with zero-padded two-digit index.

When writing Understanding Check questions, label at least one as `**Trap question.**` and at least one as `**Application.**` or `**Synthesis.**`. Trap questions surface misconceptions; application and synthesis questions test transfer.

### Step 6 — Save a user memory for future sessions

If the user has a memory system available (e.g. a personal memory graph, an auto-memory file, or another persistence layer), save a user-type memory pointing at the curriculum: the output directory, the topic, the user's goal, and a reminder to read `curriculum-meta.md` before assessing. This enables the Resume workflow in later sessions without re-gathering context. If no memory system is available, skip — the curriculum's own files are sufficient to resume from.

### Step 7 — Summarize to the user

In the final message, report: the output directory, the module count, where to start (always `modules/00-orientation.md`), and how to hand answers back for assessment.

---

## Workflow: Assess Understanding Check answers

Invoked when the user pastes answers to an Understanding Check.

### Step 1 — Read the assessment context

Read, in order:

1. `<output_dir>/curriculum-meta.md` — the rubric, schema, and assessment rules. The rules in this file are authoritative.
2. `<output_dir>/assessments/responses.jsonl` (tail ≤ 50 lines) — recent history for trend analysis.
3. `<output_dir>/assessments/misconceptions.md` — any recurring misconceptions to watch for.
4. `<output_dir>/modules/NN-*.md` — the module the user is answering for (locate by module name in the user's message, or ask).

### Step 2 — Assess per the rubric

For each answer, follow the rules in `references/assessment-rubric.md` (and `curriculum-meta.md`, which is the shipped canonical copy in the curriculum):

- Assign an **understanding level 0–5** per the rubric.
- Identify **at least one strength** per answer.
- Identify **gaps**, **misconceptions**, and **confidence calibration** (appropriately uncertain / overconfident / underconfident).
- **Preserve the verbatim response.** Never paraphrase into the record.
- **Never fabricate** a higher level than the evidence supports.

### Step 3 — Append one row per question to the JSONL

For each question, build a JSON object matching the schema in `curriculum-meta.md` and pipe to:

```bash
echo '<single-line-json>' | python3 <path-to-this-skill>/scripts/append_assessment.py --curriculum-dir <output_dir>
```

The script validates the schema and appends one line to `assessments/responses.jsonl`. On validation failure, fix the JSON and retry; do not bypass validation.

### Step 4 — Update progress and misconceptions

Run:

```bash
python3 <path-to-this-skill>/scripts/compute_progress.py --curriculum-dir <output_dir>
```

This rewrites `assessments/progress.md` with per-module status and average understanding level.

If the assessment surfaced a new misconception or reinforced a recurring one, update `assessments/misconceptions.md` directly (increment counter or add row). The script does not touch this file.

### Step 5 — Summarize to the user

Report: per-question level, the top 1–3 strengths, the top 1–3 gaps, any misconceptions to watch, and whether to advance to the next module or revisit anything first. Be concise. If overall understanding level on the module is ≥ 3 across all questions, recommend advancing. Otherwise, recommend specific remediation.

---

## Workflow: Prepare the next module

Invoked when the user says "ready for the next module," "prep module N," or similar.

### Step 1 — Identify open gaps

Read `curriculum-meta.md` and the tail of `responses.jsonl`. Collect gaps flagged `revisit_before_next_module` that have not been resolved (no later level-≥3 answer on a related question).

### Step 2 — Inject a Bridge section

If there are 1+ open gaps that relate to the upcoming module's topic, edit the next module file to prefix a **Bridge** section:

```markdown
<!-- bridge:auto -->
## Bridge from prior modules

Before diving in, a targeted recap on [gap topic], because prior answers showed [specific gap]:

[2–4 sentence explanation using a different angle / analogy / example than what the learner has already seen.]

[Optional: 1 pointer back to the specific section of the prior module that covered this.]
<!-- /bridge:auto -->
```

The `<!-- bridge:auto -->` markers matter — they let a future run detect, update, or remove the bridge cleanly. Do not nest bridges. If one already exists in the module, replace its contents rather than stacking.

### Step 3 — If a gap has persisted across two modules

Do not prepare the next module. Instead, propose a **remediation mini-module** (`modules/NNa-remediation-<slug>.md`) that focuses narrowly on the persistent gap with fresh examples, and add it to the module map in `README.md`. Ask the user for approval before writing.

### Step 4 — If `accelerate` flags are consistent

If the recent assessments show ≥3 `accelerate` flags, compress the upcoming module's ELI5 + Core Concepts sections and expand the Deep Dive. Note the change briefly in the final summary to the user.

---

## Workflow: Resume a curriculum

Invoked when the user references a curriculum in a later session ("where was I on the X curriculum?", "continue", etc.).

### Step 1 — Locate the curriculum

Check the user's memory (`MEMORY.md`) for a curriculum-pointer memory. If present, it has the output directory. If not, ask the user for the path.

### Step 2 — Summarize state

Read `assessments/progress.md`, tail of `assessments/responses.jsonl`, and `assessments/misconceptions.md`. Report:

- Last module completed (highest module with average level ≥3 across all questions).
- Open gaps flagged for revisit.
- Recurring misconceptions.
- The recommended next step: continue to next module / revisit a specific section / remediate a persistent gap.

Ask the user to confirm the next step before acting.

---

## Supporting files

- `scripts/scaffold.py` — initializes the output directory with template files.
- `scripts/append_assessment.py` — validates and appends one JSONL row to `assessments/responses.jsonl`.
- `scripts/compute_progress.py` — recomputes `assessments/progress.md` from the JSONL log.
- `references/curriculum-design.md` — module-design principles; load before Step 2 of Create.
- `references/module-template.md` — the 5-part module spine with section-by-section guidance.
- `references/assessment-rubric.md` — the 0–5 rubric and the authoritative rules for assessing answers.
- `assets/curriculum-meta.md` — topic-agnostic adaptation rules and JSONL schema, copied verbatim into each generated curriculum by `scaffold.py`.
- `assets/assessments/misconceptions.md` — empty misconceptions ledger, copied verbatim by `scaffold.py`.

## Common Mistakes

### ❌ Writing modules before the outline is approved

**Problem:** Jumping into file creation after Step 1 without presenting the proposed outline and waiting for the user's OK.

**Why it's wrong:** Curriculum structure is the single most consequential choice. Writing modules before the outline is approved wastes tokens and frustrates the user if the module breakdown is off.

**Fix:** Always complete Step 2 (design and propose outline) and wait for explicit approval before Step 3 (scaffold). If the user edits the outline, incorporate and re-confirm.

### ❌ Paraphrasing the learner's answer into the JSONL

**Problem:** Writing a "cleaned up" version of the learner's answer in the `response` field of an assessment row.

**Why it's wrong:** The verbatim response is the training data. Paraphrasing loses signal — specifically the signal about vocabulary, confidence calibration, and hesitation — which is exactly what later adaptation needs.

**Fix:** Copy the user's response unchanged into the `response` field. Put the analysis in `assessment.notes`, not in the response text.

### ❌ Inflating understanding level to seem encouraging

**Problem:** Assigning level 3 to an answer that only merits level 1 because "the learner tried."

**Why it's wrong:** Stale signal pollutes every downstream adaptation. If the learner's gaps are under-reported, the curriculum stops bridging them, and the misconception compounds.

**Fix:** Grade per the rubric in `references/assessment-rubric.md`. Every answer must get at least one explicit strength called out — that's the encouragement channel. Level is for truth.

### ❌ Omitting the goal tie-in from each module

**Problem:** Writing a generic textbook chapter without re-connecting to the learner's long-term goal.

**Why it's wrong:** The goal is the reason this curriculum exists and not a generic one. Without the tie-in, modules feel like noise, momentum dies, and the learner has to do the integration work alone.

**Fix:** Every module's Overview or Core Concepts section explicitly names how the content serves the user's goal. The final **Synthesis** module revisits the goal and maps the prior modules onto it.

### ❌ Adding a Bridge without the `<!-- bridge:auto -->` markers

**Problem:** Inserting a gap-remediation intro at the top of a module as plain prose indistinguishable from the author's original content.

**Why it's wrong:** Without markers, the next Prepare run can't detect, update, or remove the bridge. Bridges accumulate, diverge, and eventually contradict later-module content.

**Fix:** Always delimit bridges with `<!-- bridge:auto -->` / `<!-- /bridge:auto -->`. When replacing, remove the old delimited block and write a new one — never stack.

### ❌ Creating module files without zero-padded indices

**Problem:** Naming files `modules/1-foo.md`, `modules/10-bar.md`, etc.

**Why it's wrong:** Lexicographic sort breaks at the 10-module boundary; `10-bar.md` sorts before `2-baz.md`. The module map becomes unreadable in `ls` output and mispagates through any tool that sorts by name.

**Fix:** Always zero-pad to two digits: `modules/00-orientation.md`, `modules/01-foundations.md`, …, `modules/10-synthesis.md`. If the curriculum exceeds 99 modules (unlikely), switch to three digits and keep it consistent.

## Notes

- **Output directories are user-owned.** The skill writes into paths the user specified. Do not write outside those paths (no temp files in the user's home, no edits to other projects).
- **Do not overwrite existing curricula silently.** `scripts/scaffold.py` exits with a non-zero code if the output directory exists and is non-empty. Respect that — ask the user before overriding.
- **Redact before LLM-judging user answers.** Responses may contain PII, credentials, or sensitive context. The skill does not send responses to third-party services, but if the user asks the skill to delegate assessment to another tool or MCP, check the data first.
- **Memory is optional but recommended.** Step 6 saves a memory pointer so later sessions can Resume without the user re-explaining. If the user opts out, skip.
- **The skill is agent-agnostic.** Prose never references specific agent names. All template language uses "the agent" or passive voice.
