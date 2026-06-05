# Foundry work-unit contract

A Foundry **bucket** is a directory of **work-unit** files. A work unit is *any* self-contained
piece of work an autonomous Worker can implement to verifier-green in one isolated worktree — a bug
fix, an improvement, a greenfield module slice, a refactor. A structured finding/bug record is **one
flavor** of work unit; the engine does not require any particular issue schema. The only thing the
engine requires is **this contract**.

The unit files are matched by the profile's `unit_glob` (default `UNIT-*.md`). One file = one unit =
one commit = one `--no-ff` merge onto the bucket. `foundry_tick.sh validate` lints a bucket against
this contract; run it as a preflight before draining.

## Required frontmatter

```yaml
---
id: <UNIQUE-ID>          # e.g. UNIT-007, BUG-12, TASK-03. Filename MUST be <id>.md.
                         # Lex sort of id == execution order (engine claims lowest-lex open first).
title: <one line>        # human label; rides into the merge commit + end-of-run summary
status: open             # lifecycle state (see below)
updated: YYYY-MM-DD      # bumped by the engine on every transition
---
```

The engine **adds** these on `claim` — do not hand-author them: `branch`, `worktree`, `verifier`.

**`status` lifecycle:** `open` → `in-progress` → `agent-code-complete` → `merged`
(terminal forks: `blocked`, `failed`, `review-rejected`, `review-escalated`, `merge-conflict`,
`needs-decision`). Only `open` units are claimed. Set `foundry_skip: true` to keep a unit in the
bucket but out of the auto-loop (e.g. decision-gated work).

## Required body section — `## Acceptance Criteria`

**This is the heart of the contract.** Every claimable unit MUST carry a non-empty
`## Acceptance Criteria` section: the explicit, **observable, falsifiable** conditions that define
"done." It is simultaneously:

- the **Worker's target** — it implements until every criterion is satisfied AND the verifier is green;
- the **Integrator's rubric** — it PASSES only if every criterion is demonstrably met by the diff +
  verifier output, and FAILS naming the unmet one.

Write criteria a reviewer can check **without guessing intent**. Prefer a checklist:

```markdown
## Acceptance Criteria
- [ ] <a concrete, checkable outcome — "X now returns Y for input Z", not "X is better">
- [ ] <a second one>
- [ ] New/changed behavior is covered by a test that genuinely exercises it (verifier stays green)
```

Bad (unfalsifiable): "the engine handles reconciliation correctly."
Good (falsifiable): "`reconcile/1` emits `:ambiguous` with the full candidate list when >1 contact
matches; a test asserts the candidate set for a 2-match fixture."

## Recommended body sections

- **`## Context`** — what/where: enough for the Worker to LOCATE the change (files, symbols, the
  ADR/spec section, the bug's root cause). For a findings unit this is `## Symptom` + `## Root cause`.
- **`## Out of scope`** — explicit non-goals, so the Worker doesn't drift and the Integrator doesn't
  reject in-scope work. Critical when slicing a large plan into units.

## Optional metadata (frontmatter)

Carry whatever's useful; the engine ignores all of it except `foundry_skip` and (advisory)
`depends_on`:

- `repo`, `severity`, `type`, `class`, `scope` — the findings-flavor metadata (still welcome).
- `depends_on: <id>` (or a list) — units this one builds on. **Advisory only** — the engine enforces
  order purely by lex-sorted `id`. `validate` WARNS if a `depends_on` sorts at/after this unit (it
  would be claimed later, and with no auto-retry a stranded dependency cascades). So **number
  dependent units so their ids sort after their dependencies.**
- `foundry_skip: true` — keep in bucket, exclude from the auto-loop.
- `graduated: <ticket>` — once promoted to tracked work.

## Why acceptance criteria are required (not optional)

Without them the Integrator must *infer* intent from prose, which is exactly where false-PASS and
false-FAIL come from. An explicit, falsifiable criteria list turns the review gate from "does this
feel right?" into "is each named condition met?" — the single highest-leverage quality lever in the
loop. A unit with no acceptance criteria is under-specified: `validate` fails it, and a Worker that
somehow claims one routes it to `blocked` (it cannot define "done").
