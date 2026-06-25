# bash-gate-add — worked examples

Three concrete walkthroughs drawn from real sessions. Each shows the input command, the `--explain` diagnosis, the recommendation surfaced to the user, and a sketch of the post-build result.

---

## Example A — chmod compound across a local tools dir

**Input** (the user pasted a screenshot of the prompt):

```
chmod +x ~/.local/tools/*.sh && ~/.local/tools/status.sh
```

**Step 2 — `--explain` output (abridged):**

```
command: chmod +x ~/.local/tools/*.sh && ~/.local/tools/status.sh
cwd: ~
effective cwd seed: ~
outer segments (2):
  [1] chmod +x ~/.local/tools/*.sh
       candidate allow classes for verb 'chmod': chmod-safe-mode
       ask-pattern match: Bash(chmod:*)
       dispatch defer reason: glob-rejected(word=~/.local/tools/*.sh)
       => SEG_DEFER_DANGEROUS
  [2] ~/.local/tools/status.sh
       no allow class matches verb '~/.local/tools/status.sh'
       ask-pattern match: none
       => SEG_INERT
overall: DEFER (segment 1 is dangerous)
```

**Step 3 — gap category:** `predicate-too-tight`. The `chmod_safe_mode` class explicitly rejects globs (`GLOB_CHARS` check). The intent: chmod **+x** across all `.sh` files in a known dev-root tools dir is a common, low-blast-radius operation.

**Step 4 — recommendation (surfaced to the user):**

```
DIAGNOSIS
  chmod_safe_mode rejects the `*.sh` glob in segment 1, even though every
  match resolves under ~/.claude/ (a configured dev root) and the mode is
  symbolic-+x (no s/t bits).

GAP CATEGORY
  predicate-too-tight

PROPOSED CHANGE
  YAML (bash_gate.yaml): no new class. Add `allow_glob_expansion: true`
  field to the existing chmod-safe-mode rule.

  Python (bash_gate.py): in _classify_chmod_safe_mode, when
  rule.get("allow_glob_expansion") is True AND a positional contains a
  glob char, expand via glob.glob(abs_path) (NOT shell expansion). For
  each expanded match: must be a regular file (no symlinks, no dirs),
  must be under a dev root, must exist. Empty expansion -> defer
  (no-glob-matches). Cap at 50 matches to bound runtime.

SAFETY GUARANTEES
  - All expanded matches re-checked against dev_roots
  - Symlink rejection per match
  - Regular-file-only (no chmod-ing directories or devices)
  - Hard cap of 50 matches per glob
  - Mode validation unchanged (no s/t bits, octal allowlist)
  - Recursive flags still forbidden

TRADE-OFFS
  - Does NOT cover `chmod -R` (intentional — still defers)
  - Does NOT cover globs in path components (only basename glob)
  - One extra os.scandir per invocation when glob present

CONFIDENCE: 78 — predicate extension on an existing well-tested class;
mode/flag exclusions stay intact; only the path-expansion step changes.

Proceed?  (Yes / No / Modify)
```

**Step 6 — after build (sketch):**

```
$ python3 ${CLAUDE_PLUGIN_ROOT}/hooks/bash_gate.py --cmd "chmod +x ~/.local/tools/*.sh && ~/.local/tools/status.sh" --cwd ~ --explain
...
overall: ALLOW
```

Tests: 165/165 (4 new allow fixtures + 4 new defer fixtures + 2 unit cases for glob expansion).

---

## Example B — `cd && rm <relative> && npm run build | tail`

**Input** (pasted text):

```
cd ~/dev/work/myrepo && rm -f .tool-versions.tmp && npm run build | tail -50
```

cwd at prompt time: `~`.

**Step 2 — `--explain` output (the actual smoke test from above):**

```
outer segments (3):
  [1] cd ~/dev/work
       classification: CWD_MUTATION (effective_cwd -> ~/dev/work)
  [2] rm -f .tool-versions.tmp
       candidate allow classes for verb 'rm':
         rm-git-tracked-clean, rm-gitignored-build-artifact, rm-under-tmp
       ask-pattern match: Bash(rm:*)
       dispatch defer reason: not-a-regular-file(word=.tool-versions.tmp)
       => SEG_DEFER_DANGEROUS
  [3] npm run build | tail -50
       pipe sub-segments (2):
         [3a] npm run build   => SEG_INERT
         [3b] tail -50        => SEG_INERT
       => SEG_ALLOW (all pipe sub-segments INERT)
overall: DEFER (segment 2 is dangerous)
```

**Step 3 — gap category:** ambiguous between `predicate-too-tight` (the `not-a-regular-file` reason is wrong; the file DID exist) and `architectural-gap`. Investigation in main context: the precheck runs `os.path.isfile(abs_path)` where `abs_path` comes from `_resolve_path_against_cwd(".tool-versions.tmp", effective_cwd="~/dev/work")` — but `myrepo` lives at `~/dev/work/myrepo/`. Effective cwd is wrong: segment [1] sets it to `~/dev/work`, not `~/dev/work/myrepo`. The motivating command itself has a typo (missing `/myrepo`). Re-run with corrected command shows the file exists and the rm-gitignored-build-artifact class hits (since `.tool-versions.tmp` is in `.gitignore` of the scratch repo / equivalent in myrepo).

**Step 4 — recommendation:** the original prompt was a user-error typo, not a hook gap. STOP. Surface to the user: "the typo'd command would have correctly deferred; the corrected command already allows. No build needed."

This is the failure mode the skill is built to catch: not every prompt deserves a hook extension. The explain output told the truth.

---

## Example C — new safe redirect path under `~/Library/Logs/`

**Input** (pasted text):

```
git diff > ~/Library/Logs/claude-diff.log
```

**Step 2 — `--explain` output:**

```
outer segments (1):
  [1] git diff > ~/Library/Logs/claude-diff.log
       => SEG_DEFER (unsafe-redirect(> ~/Library/Logs/claude-diff.log))
overall: DEFER (segment 1: unsafe-redirect)
```

**Step 3 — gap category:** `safe-root-expansion` (or "redirect-not-safe-recognized" — both apply; the cleaner framing is the former since `~/Library/Logs/` is conceptually a safe write destination).

**Step 4 — recommendation:** add `~/Library/Logs/` to `SAFE_REDIRECT_PATH_PREFIXES`. **However** — this prefix is not a "dev root," it's a log destination. Confidence ~55: the right call may be a separate `safe_redirect_path_prefixes` config list in `~/.config/bash-gate/config.yaml`, not extending `dev_roots`. Surface to the user with confidence and the recommendation to externalize the prefix list to config so future additions don't require code edits.

In practice: this is where `bash-gate-add` does its highest-value work — turning "I want this specific redirect to work" into a *configurable* extension instead of a one-off code patch.
