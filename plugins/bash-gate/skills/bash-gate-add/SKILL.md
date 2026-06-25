---
name: bash-gate-add
description: >
  Add a new allow-class (or other extension) to the bash gate hook when a
  permission prompt surfaces that should have been auto-allowed. Takes the
  prompting Bash command (pasted text OR a screenshot), runs
  `bash_gate.py --explain` to diagnose which segment deferred and why,
  identifies the gap category, surfaces ONE recommendation with confidence
  score, asks for explicit approval BEFORE building, then dispatches a
  build subagent to add the class + fixtures + smoke tests. Use when the user
  says "/bash-gate-add", "/bgate-add", "address this prompt", "fix this
  gate", "another gate prompt", "auto-allow this", or "the gate should
  have allowed this".
---

# /bash-gate-add

The bash gate hook lives at `${CLAUDE_PLUGIN_ROOT}/hooks/bash_gate.py` + `${CLAUDE_PLUGIN_ROOT}/hooks/bash_gate.yaml`. Whenever a Claude Code permission prompt surfaces a Bash command that *should* have been auto-allowed, this skill closes the loop: diagnose with `--explain`, recommend ONE precise extension, get approval, dispatch a build sub-agent, and verify the original command now allows.

This is a plugin: the hook, yaml, and stats reader ship under `${CLAUDE_PLUGIN_ROOT}/hooks/`. The user's editable config is `~/.config/bash-gate/config.yaml` (falling back to the shipped `${CLAUDE_PLUGIN_ROOT}/hooks/bash_gate.yaml`). `dev_roots` and most user config should be edited in `~/.config/bash-gate/config.yaml`, NOT the shipped yaml (which `claude plugin update` overwrites).

## The gate model (Phase 2g + the inversion)

Under `defaultMode: bypassPermissions`, CC precedence is **deny > ask > hook**, so a hook `allow` can only ADD friction, never remove it — it CANNOT suppress a settings.json `permissions.ask` prompt. To make auto-approval actually work, the gated verbs were moved OUT of settings.json `ask` into the hook-owned `gated_patterns` list in `bash_gate.yaml`, so the hook is their sole gate. Two danger tiers result:

- **Tier A — always-ask** = settings.json `permissions.ask` (sudo, ssh, security, gpg, ssh-keygen, eval, deploy/release). Deterministic prompt, NEVER auto-approved. Owned by the user; this skill does not edit it.
- **Tier B — gated** = `gated_patterns` in `bash_gate.yaml` (chmod, source/`.`, curl mutations, scp, rsync, kill -9/killall/pkill). These are handed to an **LLM arbiter** (Haiku, ~1s) in `main()`: SAFE → auto-allow; UNSAFE → ask with the arbiter's reasoning surfaced; any failure (disabled, network, ERROR) → **fail CLOSED to ask** (no settings.json backstop remains). Telemetry lands under a nested `arbiter` object in `bash_gate.log.jsonl` (see `bash_gate_stats.py`).

**This skill adds deterministic allow-classes, which take precedence over both tiers and remain the right fix for any *recurring* safe pattern** — instant, free, auditable, no network/API-key dependency. The arbiter is the catch-all for the long tail, not a replacement. When a prompt recurs for a class of command, build the deterministic allow-class here; let the arbiter handle one-offs. Note: `--explain` reflects only the static decision (it never calls the arbiter), so an `overall: DEFER` on a Tier B command may still be auto-approved at runtime by the arbiter — that's expected, and is not a reason to skip adding a deterministic class for a recurring pattern.

## Inputs

One of:
- A screenshot of a Claude Code permission UI prompt. Use the `Read` tool on the image path — the prompted command will be visible in the screenshot.
- A pasted code block or plain text containing the command.
- The motivating command quoted inline in the user's message.

If the input is genuinely ambiguous (multiple commands shown, none clearly the prompted one), ask the user one short question. Otherwise extract and proceed.

## Hard requirements (do NOT skip)

- The "approval gate" at Step 5 is non-negotiable. **Never dispatch the build sub-agent without the user's explicit Yes.** This is the entire reason this skill exists as a separate flow instead of an auto-builder.
- Never modify any file outside `${CLAUDE_PLUGIN_ROOT}/hooks/`, `~/.config/bash-gate/`, and this skill's own directory. In particular: never touch `~/.claude/settings.json`.
- Never use `npx`. Use system `python3` directly.
- The hook MUST continue to never block Bash on internal failure. The `--explain` mode MUST never write to `${CLAUDE_PLUGIN_ROOT}/hooks/bash_gate.log.jsonl`.
- All existing fixtures must still pass after the build.

## Step 1: Extract the command

If the user pasted a code block, take the exact string inside. If they pasted a screenshot path, `Read` the image and extract the verbatim command text shown in the prompt. Preserve quoting, redirects, pipes, and operators exactly.

Set `CMD="<the extracted command>"`. Set `CWD` to the cwd shown in the screenshot if visible, else default to `$(pwd)` in the user's main shell context (ask if unclear — but only if a relative path appears in the command).

## Step 2: Diagnose with `--explain`

Run the hook in explain mode. This is read-only — no log writes, no state changes:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/hooks/bash_gate.py --cmd "$CMD" --cwd "$CWD" --explain
```

The output is a segment-by-segment breakdown:
- For each outer `&&`/`||`/`;` segment: classification, candidate allow classes for the verb, `always-ask match` (Tier A), `gated-pattern match` (Tier B), dispatch defer reason, terminal state (`SEG_ALLOW` / `SEG_INERT` / `SEG_CWD_MUTATION` / `SEG_DEFER_DANGEROUS`).
- For pipes: each `|` sub-segment expanded the same way.
- Final line: `overall: ALLOW` or `overall: DEFER (<which segment + why>)`.

If `overall: ALLOW`, the gate already allows this — tell the user the prompt was likely a stale UI or a different command, and stop. No build needed.

## Step 3: Identify the gap category

Read the explain output carefully and pin the failure to exactly ONE category. Heuristics:

| Category | Signal in explain output |
|---|---|
| **Missing allow class** | `no allow class matches verb 'X'` AND a danger match — `gated-pattern match: Bash(X:*)` (Tier B, arbitrated) or `always-ask match: Bash(X:*)` (Tier A). No class covers this verb at all. |
| **Predicate too tight** | `candidate allow classes for verb 'X': <one or more>` AND `dispatch defer reason: <specific predicate failure>` (e.g. `not-a-regular-file`, `recursive-flag-rejected`, `chmod-octal-not-in-allowlist`, `glob-rejected`). A class exists; its predicate excludes this variant. |
| **Safe-root expansion** | dispatch defer reason contains `path-outside-dev-roots(...)` or `relative-path-out-of-scope(...)` AND the path is somewhere the user clearly wants to be writable (e.g. a new repo location, `~/dev/personal/foo`). Fix: extend `dev_roots` in `~/.config/bash-gate/config.yaml`. |
| **Redirect not recognized as safe** | `SEG_DEFER (unsafe-redirect: ...)` for a redirect the user clearly wants stripped (e.g. a new safe path prefix or operator form). |
| **Danger-pattern false positive** | `always-ask match: Bash(...)` (Tier A, settings.json — owned by the user) or `gated-pattern match: Bash(...)` (Tier B, `gated_patterns` in yaml) but the matched pattern is clearly too broad. For Tier A: STOP and surface to the user; don't patch around settings.json from the hook side. For Tier B: a narrowing edit to `gated_patterns` MAY be the fix, but still surface it — broadening/narrowing the danger list is a judgment call for the user. |
| **Architectural gap** | None of the above — the explain output reveals something the hook simply doesn't model. STOP and surface to the user with a writeup; don't speculate. |

## Step 4: Synthesize the recommendation

Pick ONE fix. Commit to ONE recommendation; never hand the user an a/b/c menu — commit to the most principled fix. Reasoning must root in:
- **Safety**: reversibility of the action being auto-allowed (`rm` of git-tracked-clean is reversible via `git checkout`; `rm` of an untracked-non-gitignored file is NOT — recommend against unless there's a tight predicate).
- **Blast radius**: dev-root containment, path traversal rejection, symlink rejection, glob rejection.
- **Predicate tightness**: prefer the narrowest predicate that covers the motivating case + 2-3 obvious variants.

Output the recommendation to the user in this exact shape:

```
DIAGNOSIS
  <1-2 sentences describing which segment deferred and why>

GAP CATEGORY
  <one of: missing-allow-class | predicate-too-tight | safe-root-expansion |
   redirect-not-safe-recognized | danger-pattern-false-positive | architectural-gap>

PROPOSED CHANGE
  YAML (bash_gate.yaml):
    <concrete YAML snippet to add/modify — full class definition or field edit>

  Python (bash_gate.py):
    <concrete sketch: new handler function name + signature + predicate logic in plain English>

SAFETY GUARANTEES
  - <reversibility property of every auto-allowed case>
  - <dev-root containment / path-traversal rejection / glob rejection / symlink rejection>
  - <exclusions: recursive flags, dangerous modes, etc.>

TRADE-OFFS
  - <what this DOES NOT cover>
  - <any false-positive risk>

CONFIDENCE: <1-100> — <one-line justification>

Proceed?  (Yes / No / Modify)
```

**STOP HERE.** Do NOT proceed to Step 5 until the user responds with an unambiguous "Yes" (or paraphrase: "go", "ship it", "build it"). If they say "Modify", iterate on the proposal and re-surface with a fresh confidence score. If "No", drop it.

## Step 5: Dispatch the build sub-agent

Only after approval. Use the `Task` tool to spawn a sub-agent with this prompt template (parameterized inline — fill `<<...>>` slots from the approved recommendation):

> You are extending the bash gate hook with a new allow class (or predicate extension). Be surgical and conservative.
>
> **Read order (in this order, fully, before editing):**
> 1. `${CLAUDE_PLUGIN_ROOT}/hooks/bash_gate.py`
> 2. `${CLAUDE_PLUGIN_ROOT}/hooks/bash_gate.yaml`
> 3. `${CLAUDE_PLUGIN_ROOT}/hooks/test/run_tests.py`
> 4. A representative subset of `${CLAUDE_PLUGIN_ROOT}/hooks/test/fixtures/*.json` + `.expected` for the verb you're touching.
>
> **The approved change:**
> - Gap category: <<GAP_CATEGORY>>
> - YAML addition / edit:
>   ```yaml
>   <<YAML_SNIPPET>>
>   ```
> - Python handler / predicate change:
>   <<PYTHON_PLAIN_ENGLISH_PLUS_SKETCH>>
>
> **Motivating command (must allow after your change):**
> ```
> <<CMD>>
> ```
> (cwd: `<<CWD>>`)
>
> **Required fixtures** (add new `.json` + `.expected` pairs under `${CLAUDE_PLUGIN_ROOT}/hooks/test/fixtures/`):
> Propose 6-10 fixtures covering BOTH allow and defer cases — at minimum:
> - 1 fixture for the motivating command itself → `allow`
> - 2-3 variants that should also `allow` (different paths/modes/flags within the predicate)
> - 3-5 `defer:<reason-substring>` fixtures probing the predicate's negative space (path traversal, symlinks, globs, paths outside dev roots, forbidden flags, recursive variants, dangerous modes, etc.)
>
> Use `_test_dev_roots` / `_test_setup_files` keys in fixture JSON when the predicate needs filesystem state. Use the existing scratch repo at `/var/tmp/__bash_gate_repo__/` for git-aware predicates (see `_setup_scratch_repo` in `run_tests.py`).
>
> **Hard constraints:**
> - No `npx`. Use `python3` directly.
> - Do NOT edit `~/.claude/settings.json` or anything outside `${CLAUDE_PLUGIN_ROOT}/hooks/`.
> - The hook must NEVER block Bash. All errors degrade to defer.
> - Never use the `:any`-style "trust me" exclusions — every allow path must justify itself via predicate, not by skipping checks.
> - Re-use existing helpers (`_resolve_path_against_cwd`, `_path_under_dev_root`, `_rm_precheck`, `strip_safe_redirects`) before writing new ones.
> - Push forward — no legacy back-compat shims; no comments explaining "why we used to do X".
> - Never use the `:any` type / `# type: ignore` to silence errors.
>
> **Acceptance criteria:**
> 1. `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/test/run_tests.py` reports all tests pass, including your new fixtures AND all existing fixtures + unit tests + explain-mode CLI tests.
> 2. `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/bash_gate.py --cmd "<<CMD>>" --cwd "<<CWD>>" --explain` ends with `overall: ALLOW`.
> 3. The new YAML class (if any) is listed in `bash_gate.yaml` with `log_as` and `allow_reason` populated.
> 4. The handler docstring describes the exact predicate and exclusions.
>
> **Reporting format** (under 400 words, in this order):
> 1. Files touched (paths only)
> 2. New YAML class name (if any) + log_as
> 3. New handler function name + 1-sentence predicate summary
> 4. Fixture count: <N added> covering <M allow / K defer>
> 5. Test totals (X/Y) — including baseline + new
> 6. Output of `--explain` on the motivating command, last 3 lines
> 7. Deviations from this brief (if any)

Dispatch with `subagent_type: general-purpose` (or whichever build-capable model is the local default).

## Step 6: Verify after build

Once the sub-agent reports, run `--explain` again yourself in the main context:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/hooks/bash_gate.py --cmd "$CMD" --cwd "$CWD" --explain
```

Show the user the BEFORE (from Step 2) and AFTER (now) side by side, and confirm `overall: ALLOW`. Also confirm test totals from the sub-agent's report match the actual run by re-executing:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/hooks/test/run_tests.py 2>&1 | tail -3
```

If anything is off (still defers, tests fail, fixture short on coverage), surface it to the user with a concrete recommendation. Do NOT silently re-dispatch the sub-agent — the user owns the retry decision.

## Hard rules

- **Approval gate is mandatory at Step 5.** No exceptions. Even if the change is "obvious", surface the recommendation and wait for Yes.
- **One fix per invocation.** If the explain output reveals multiple distinct gaps, report them all but propose ONE — let the user batch or pick.
- **Stop at architectural-gap or a Tier A always-ask false-positive** (settings.json is user-owned — the fix is NOT a hook extension). A Tier B gated-pattern false-positive MAY be fixable by narrowing `gated_patterns` in yaml, but surface the recommendation first; don't silently edit the danger list.
- **No edits outside `${CLAUDE_PLUGIN_ROOT}/hooks/`, `~/.config/bash-gate/`, and this skill's own directory.**
- **No log writes from `--explain`.** Already enforced in the hook code; verify with the existing test.
- **Re-run `--explain` after build** — proof, not promise.

> Note on `${CLAUDE_PLUGIN_ROOT}`: this variable expands inside the Claude Code harness. When running a raw shell command yourself, substitute the resolved plugin install path.
