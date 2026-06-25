---
name: permission-setup
description: Recommend safe, conservative agent permission settings for a less-technical user, then delegate the write — never mutate security config directly. Detects the provider (Claude Code / Codex / Cursor / others) and surface (CLI / Desktop-IDE / Cloud), explains permissions in plain language, recommends the "Cautious" least-privilege posture as behavior then concrete config, names that provider's bypass footgun by name, and shows the exact config + location for the user (or a platform config skill) to apply. Use when the user says "/permission-setup", "set up permissions", "set up my agent permissions", "is my agent safe", "make my agent safe", "what permissions should I use", "lock down my agent", "are my settings secure", "review my agent permissions", or finishes /ai-setup. Re-runnable any time; reads references/permission-profiles.md live.
---

# permission-setup

## Overview

A less-technical user has no way to judge whether their agent's permissions are
safe — the defaults vary by tool, the dangerous knobs are one flag away, and the
risk (a prompt injection in a file or web page running a destructive command) is
invisible until it fires. This skill gives them a **conservative starting point
they can understand**, in their tool's own vocabulary, without making them learn
permission internals.

It is a **recommend-and-delegate** flow. config-chunks **never writes security
config** — not `settings.json`, not `config.toml`, not `permissions.json`. This
skill detects the user's setup, explains the posture in plain language, shows the
*exact* config and where it lives, and hands the write to the user (or, where a
safe platform skill exists, drives that). The human stays in the loop and owns
the decision.

**When to run it:** the user wants their agent set up safely, is unsure if their
current settings are risky, or just finished `/ai-setup`. **When to skip it:** a
technical user who already manages their own permission rules and handed you a
specific config — don't second-guess a deliberate setup. Recommend the *gap*, not
a teardown of what they chose on purpose.

## The payload it reads

The verified, cited permission profiles live under the **engine home** at
`references/permission-profiles.md`. **Self-discover that path** — do not rely on
a bare `../../` path (it only resolves when the shell's working directory is this
skill directory; Cursor/Codex run from the project root). You know the absolute
path of this skill's own directory — substitute it for `<skill-dir>` and probe
for the first reference file that exists:

```bash
# Substitute <skill-dir> with the ABSOLUTE path of THIS skill directory.
SKILL_DIR="<skill-dir>"

PROFILES=""
for cand in \
  "${CONFIG_CHUNKS_HOME:+$CONFIG_CHUNKS_HOME/references/permission-profiles.md}" \
  "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/references/permission-profiles.md}" \
  "$SKILL_DIR/../.engines/config-chunks/references/permission-profiles.md" \
  "$SKILL_DIR/../../references/permission-profiles.md"; do
  [ -n "$cand" ] && [ -f "$cand" ] && { PROFILES="$cand"; break; }
done
[ -n "$PROFILES" ] && echo "profiles: $PROFILES" || echo "permission-profiles.md not found — re-export with --with-engine, or set CONFIG_CHUNKS_HOME" >&2
```

The candidate order mirrors the other config-chunks skills (`CONFIG_CHUNKS_HOME` →
`CLAUDE_PLUGIN_ROOT` → `--with-engine` exported sibling at
`<skill-dir>/../.engines/config-chunks/` → in-repo `<skill-dir>/../../`); the
exported-sibling probe is what lets this skill run on Cursor/Codex with zero env
vars. **Read `$PROFILES` at run time** and render the posture for the user's
detected (provider, surface) — do **not** hardcode provider config here. Provider permission models drift; the
reference carries the canonical 3-dial model, per-provider/per-surface "Cautious"
posture, the named footgun for each tool, and source URLs. If the file is missing,
say so and stop — do not invent permission config from memory.

The whole model reduces to **three dials + one never-touch**:

- **Capability** — what the agent can *do* (read freely; edits reviewed; no command exec until opted up).
- **Approval** — *when* it must stop and ask (auto-run only known-safe reads; ask before anything that changes/runs/sends).
- **Network** — outbound internet (off, or a tight registry allowlist).
- **⛔ Bypass** — the "do everything without asking" mode. The footgun is running it *naked*: outside a throwaway container, only ever run it behind a deterministic gate that still stops dangerous commands (see Step 4) — never bare.

The recommended **Cautious** posture is the same everywhere; only the spelling
differs per provider.

---

## Flow

### Step 1 — Detect provider + surface, then confirm

Auto-detect, then confirm in plain language — never assume silently. Detect via:

```bash
ls -d ~/.claude ~/.codex ~/.cursor 2>/dev/null
```

- `~/.claude` → **Claude Code**; `~/.codex` → **Codex**; `~/.cursor` → **Cursor**.
  Multiple present → ask which they want to set up (or do each in turn).
- None present, or another tool (Windsurf/Cline/Aider) → ask which tool they use.

Then pin the **surface**, because the posture genuinely differs:
- **CLI** (terminal) vs **Desktop / IDE extension** vs **Cloud / web** (hosted).

Confirm in one plain sentence: *"Looks like you're on Claude Code in the
terminal — that right?"* Surface matters: Claude web ignores `~/.claude`
settings; Codex cloud's main dial is internet on/off; Cursor's Auto-review is not
a security boundary. Get this right before recommending anything.

### Step 2 — Explain permissions in two plain sentences

No jargon. Something like: *"Permissions decide what your AI assistant is allowed
to do on its own versus when it stops to ask you first. We'll start it cautious —
it can read and suggest freely, but it asks before doing anything that changes
files, runs commands, or goes online — and you can loosen that later."*

### Step 3 — Recommend "Cautious" — behavior first, then config

Lead with **what it means in practice**, in their terms:
- Reads your code and answers freely — no prompting for safe look-only actions.
- **Asks before** editing files, running commands, pushing, or going online.
- Internet access **off** (or a tight package-registry allowlist) until needed.
- You **level up one rung at a time** as you build trust — never start at the top.

*Then* show the concrete config for their (provider, surface), copied from the
reference file. Present it as a block they can apply, with a one-line note on what
each part does in plain language.

### Step 4 — Name the bypass footgun, by name

Every tool has one "do everything without asking" mode — name the user's
specific one (Claude `bypassPermissions` / `--dangerously-skip-permissions`;
Codex `--yolo` / `danger-full-access`; Cursor "Run Everything"; etc.) and the
concrete risk in one sentence: *"This turns off the asking entirely — so if a
file or web page it reads contains a hidden instruction to delete or leak
something, it just does it, with no chance for you to stop it."*

The footgun is **ungated** bypass — running it bare. Approval fatigue has *three*
honest responses, not two — and the cure for fatigue is path 3, not path 2:

1. **Stay cautious** (the default) — you keep approving things, but nothing
   dangerous runs unseen.
2. **Naked bypass** — no prompts, no net. **This is the footgun. Don't.**
3. **Bypass behind a deterministic gate** — run bypass, but keep a Bash gate in
   front that still stops dangerous commands while auto-approving the provably
   safe ones. You get the no-prompt flow *without* the naked risk.

If the user is drowning in approvals and eyeing bypass, point them at path 3, not
2: the **`bash-gate`** plugin (same marketplace, Claude Code only) is built
exactly for this — a PreToolUse gate that re-adds allow/deny/ask gating on Bash
*even under bypass*, so the safety net only ever catches genuine danger. Don't
sell a determined-bypass user a lock that forecloses it.

For Claude, the hard lock `disableBypassPermissionsMode: "disable"` is right
**only for a user who is certain they'll never need bypass** — it permanently
blocks path 3 too. Recommend it for the cautious never-bypass user; do **not**
apply it by default to someone with a legitimate gated-bypass workflow.

### Step 5 — Delegate the write (NEVER write it yourself)

config-chunks does not touch security config. Two paths:

- **Default — show-and-instruct.** Print the exact config block **and its file
  location** (`~/.claude/settings.json`, `~/.codex/config.toml`,
  `~/.cursor/permissions.json`, or the in-app setting + click-path for GUI
  tools). Tell the user precisely where to paste it. For GUI-driven tools
  (Cursor run mode, Windsurf Turbo), give the menu path, not just a file.
- **Platform skill — only where one safely exists.** On Claude Code, you may
  offer to drive the platform `update-config` skill to apply the
  `settings.json` change. Confirm explicitly before invoking it.

Frame the confirmation honestly: *"This is a recommended starting point to
review, not a guarantee — you control and are responsible for what you approve.
Want to apply it, or adjust first?"* Do not proceed without a clear yes, and if
you can't safely write it, leave the user with the exact block + location so they
can.

### Step 6 — Close: revisitable + level-up

Tell them it's not permanent: re-run `/permission-setup` any time, and **level up
one rung when ready** (e.g. Claude `default` → allow more Bash; Codex
`read-only` → `workspace-write` with network still off). One sentence, no
ceremony.

**Cutting approval fatigue (Claude Code).** If the routine "approve this safe
command again?" prompts are the pain, the answer is the **`bash-gate`** plugin
(see Step 4) — `claude plugin install bash-gate@mnox-ai`. It's a *separate*
plugin, not part of config-chunks (which still never touches security config);
mention it as a pointer, don't configure it from here.

## Guardrails

- **config-chunks NEVER writes security config.** No `settings.json`,
  `config.toml`, or `permissions.json` writes from this skill — recommend, show,
  delegate. This is the hard architectural rule.
- **Read the profile live.** Always pull provider config from the discovered
  `$PROFILES` (`references/permission-profiles.md` under the engine home) at run
  time; never assert permission facts from memory (they drift post-cutoff). File
  missing → say so and stop.
- **Least privilege, always.** Recommend the Cautious posture; never default a
  user up the ladder or near the bypass footgun.
- **Plain language.** Translate every dial into what it lets the agent do. If you
  must use a provider's term, define it in one clause.
- **Honest framing.** It's a starting point to review, not certified-secure; the
  user owns what they approve. Say that, in those words, before any write.
- **Detect, don't assume.** Confirm provider + surface before recommending — the
  posture differs by surface, and a wrong guess gives unsafe advice.
