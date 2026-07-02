---
name: create-skill
description: Author a Claude Code or cross-host Agent Skill end-to-end — scaffold the directory, write the body against a portable authoring contract, structurally validate, and design-score it. Use when creating a new skill, "make a skill for X", "scaffold a SKILL.md", "write a skill", "turn this into a skill", or improving/grading an existing skill's design. Emits a spec-pure portable skill by default; Claude-only features are opt-in.
---

# Create Skill

## Overview

This skill owns the **whole skill-authoring lifecycle** in one guided flow:
**scaffold → author → validate → judge** (→ optional package). It replaces the
scattered skill-create / skill-creator / skill-judge skills with a single coherent
path, grounded in a portable authoring contract and a design-quality rubric.

Two design commitments shape everything below:

1. **Spec-pure by default.** Output conforms to the open Agent Skills standard — the
   portable core read unmodified by ~30+ hosts. Claude-Code-only affordances
   (`hooks`, `context: fork`, install-path vars, `!`cmd`` injection) are an **opt-in
   adapter**, never smuggled into the portable body. See
   [`references/authoring-contract.md`](../../references/authoring-contract.md).
2. **Validation has two tiers.** A fast deterministic structural gate
   (`validate_skill.py`) and a design-quality judgment (the rubric + a call to
   `util-review`). The original tooling conflated them and silently skipped the
   judgment tier — this skill keeps them separate and runs both.

This skill does **not** re-implement `util-review`'s catalog. For cross-cutting review
(hooks, CLAUDE.md, configs, side effects, security) the judge stage **invokes
util-review**. One catalog, no drift.

## Quick Reference

| Stage | Do | Backed by |
|---|---|---|
| 1. Scaffold | gather name + what/when + type, then run `init_skill.py` | `scripts/init_skill.py` |
| 2. Author | write the body; progressive disclosure; craft the description | `references/authoring-contract.md` |
| 3. Validate | run the deterministic structural gate; fix all errors | `scripts/validate_skill.py` + `references/validate-catalog.md` |
| 4. Judge | score 8 design dimensions; invoke `util-review`; verify-before-report | `references/judge-rubric.md` |
| 5. Package | (optional) zip + place per host | `scripts/package_skill.py` + `authoring-contract.md` §3 |

**Locate the plugin root first** (do this once, then read everything relative to it):

```bash
# This skill lives at <root>/skills/create-skill/. Scripts + references are at the
# plugin root. Self-discover ROOT — don't trust a bare ../../ (it only resolves in
# some layouts) and don't assume an env var is set.
SKILL_DIR="<dir containing this SKILL.md>"
for ROOT in \
  "${CREATE_SKILL_HOME:-}" \
  "${CLAUDE_PLUGIN_ROOT:-}" \
  "$SKILL_DIR/../.." ; do
  [ -n "$ROOT" ] && [ -f "$ROOT/scripts/init_skill.py" ] && break
done
# Now: $ROOT/scripts/*.py and $ROOT/references/*.md
```

All scripts are stdlib-only Python (PEP 723, `requires-python >=3.10`), emit JSON to
stdout, and exit non-zero on failure. Run with `python3`.

## Authoring Lifecycle

Walk the stages in order. Each stage gates the next — don't author before scaffolding,
don't judge before the structural gate is green.

### Stage 1 — Scaffold

Gather the minimum the scaffold needs, then stamp the directory.

**Requirements to elicit (ask only what you can't infer):**
- **Name** — kebab-case, ≤64 chars, no `claude`/`anthropic`, and it **must equal the
  directory name**. Pick a verb-first, distinctive name.
- **What + when** — the one-sentence description seed. This is the highest-leverage
  decision; see [Stage 2 / the description](#the-description).
- **Type** — which archetype (drives body shape):

  | Type | Shape | Example |
  |---|---|---|
  | Technique | a method the model applies | a refactoring pattern |
  | Reference | domain facts the model lacks | a company schema |
  | Process | a phased workflow with checkpoints | a release runbook |
  | Workflow | a deterministic recipe | a fixed build sequence |

**Stamp it:**

```bash
python3 "$ROOT/scripts/init_skill.py" \
  --name <skill-name> \
  --output-dir <parent dir, e.g. ~/.claude/skills or a plugin's skills/> \
  --description "<what + when, third person>"
```

`init_skill.py` **refuses to overwrite a non-empty directory** (exit 2, structured
error) — if it does, ask the user before clobbering. It writes a SKILL.md with
**spec-pure frontmatter** (`name` + `description` only) and the four required section
stubs (Overview / Quick Reference / Main Content / Common Mistakes). Add Claude-only
frontmatter later, deliberately, only if the skill truly needs it.

### Stage 2 — Author

Write the body against [`references/authoring-contract.md`](../../references/authoring-contract.md).
Read it now if you haven't — it is the spec. The load-bearing rules:

- **Knowledge delta is the point.** Write only what the model *doesn't* already know —
  the non-obvious *why*, the project-specific facts, the failure modes you've hit. A
  body that restates general knowledge is "The Tutorial" and scores ≤5 (D1).
- **Progressive disclosure.** L2 body **<500 lines / <5k tokens**. Push detail to
  `references/*.md` (loaded on demand, one level deep, TOC if >100 lines). Don't dump.
- **Degrees of freedom = task fragility.** Prose for open tasks; exact scripts ("run
  exactly this") for fragile/destructive ones.
- **Common Mistakes must be real.** Each ❌ is a specific failure a capable model would
  otherwise commit — not filler. See [Common Mistakes](#common-mistakes) here as a model.
- **Scripts portable.** Stdlib-first, forward slashes, relative paths, no
  `npx`/`brew`/runtime-install assumptions. Don't hinge core behavior on a script
  running — sandboxed hosts degrade to read-only.

<a id="the-description"></a>
**The description** (the single field that decides whether the skill ever fires):
- Third person ("Audits…", never "I/You can…").
- **What + when**, with concrete trigger keywords, **front-loaded** (per-host budgets
  truncate the tail).
- Specific enough to fire at the right moment and *only* then. A generic description is
  "The Invisible Skill."

### Stage 3 — Validate (deterministic gate)

```bash
python3 "$ROOT/scripts/validate_skill.py" --skill-dir <path to the skill dir>
```

Returns `{"success", "errors", "warnings", "checks_run"}`. **Fix every error before
proceeding** — these are mechanical (frontmatter parses, name legal, the four sections
present, no forbidden files, ≤500 lines). The full check list and the tier-2 backlog
are in [`references/validate-catalog.md`](../../references/validate-catalog.md). This
gate decides *well-formed*, not *good* — that's Stage 4.

### Stage 4 — Judge (design quality)

Score the skill against [`references/judge-rubric.md`](../../references/judge-rubric.md):
8 dimensions / 120 points, with **Knowledge Delta (D1, 20pts)** the core. Name any of
the [6 failure patterns](../../references/judge-rubric.md#the-6-failure-patterns) you
see — it's faster than enumerating sub-flaws.

For the cross-cutting concerns this rubric doesn't cover — hooks, CLAUDE.md, configs,
side effects, security, unclosed loops — **invoke `util-review`** on the skill rather
than duplicating its catalog.

**Verify-before-report gate (mandatory):** re-verify every Critical/High finding in the
main context before it ships. Sub-agents over-report; demote or drop what doesn't
survive a re-read. This is the line between a deliverable and noise.

### Stage 5 — Package & place (optional)

```bash
python3 "$ROOT/scripts/package_skill.py" --skill-dir <path>   # → distributable zip
```

For placement, target **`.agents/skills/`** (the broadly-shared convention) or symlink
`.claude/skills/` → `.agents/skills/`. Per-host caveats are in
[`authoring-contract.md` §3](../../references/authoring-contract.md#3-per-host-placement).
**Prove placement with a real host-load** — never trust a copier's identical-bytes
output.

## Common Mistakes

### ❌ Writing the body before nailing the description
The description is the trigger and the highest-leverage field. If you write 400 lines
of body then bolt on a vague description, the skill never fires. Settle the what+when
first (Stage 1), refine it last (Stage 2).

### ❌ Treating the structural gate as "validation done"
`validate_skill.py` passing means *well-formed*, not *good*. A skill can pass all 16
structural checks and still be a zero-knowledge-delta Tutorial. Always run Stage 4.

### ❌ Smuggling Claude-only frontmatter into a "portable" skill
`context: fork`, `hooks`, `` `CLAUDE_PLUGIN_ROOT` ``, `!`cmd`` injection — other hosts
ignore or choke on these. Keep them out of the portable body; add them as a labeled,
opt-in Claude-only adapter only when genuinely needed.

### ❌ Duplicating util-review's catalog into the validate stage
The whole point of this consolidation is to kill drift. For cross-cutting review,
*invoke* util-review — don't copy its check-IDs here and let the two copies diverge.

### ❌ Shipping a 700-line SKILL.md
Over ~500 lines means you skipped progressive disclosure. Split detail into
`references/*.md` (loaded on demand). The body persists in context for the whole
session — every excess line is a permanent tax.

### ❌ Filler Common Mistakes
"Be careful with edge cases" warns nothing. Each ❌ must name a specific failure a
smart model would otherwise commit, with the fix. (Like these.)

## Notes

- **Execution model:** single-pass, sequential, stage-gated. Step order is
  load-bearing — each stage gates the next. The judge stage may fan out a `util-review`
  call but the lifecycle itself is linear.
- **Canonical home:** this skill supersedes claudia's `skill-create` /
  `skill-creator` / `skill-judge`, which now carry deprecation pointers here.
- **Relationship to the review kernel:** a future review-skill archetype (severity
  spine + unified finding contract + verify-gate) may be stamped by this scaffolder;
  it's a follow-on, not a dependency.
