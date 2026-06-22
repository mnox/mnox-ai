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

The verified, cited permission profiles live at
`../../references/permission-profiles.md` (plugin root). **Read that file at run
time** and render the posture for the user's detected (provider, surface) — do
**not** hardcode provider config here. Provider permission models drift; the
reference carries the canonical 3-dial model, per-provider/per-surface "Cautious"
posture, the named footgun for each tool, and source URLs. If the file is missing,
say so and stop — do not invent permission config from memory.

The whole model reduces to **three dials + one never-touch**:

- **Capability** — what the agent can *do* (read freely; edits reviewed; no command exec until opted up).
- **Approval** — *when* it must stop and ask (auto-run only known-safe reads; ask before anything that changes/runs/sends).
- **Network** — outbound internet (off, or a tight registry allowlist).
- **⛔ Bypass** — the "do everything without asking" mode. Never enable outside a throwaway container.

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
something, it just does it, with no chance for you to stop it. Leave this off
unless you're in a throwaway sandbox."* For Claude, recommend locking it with
`disableBypassPermissionsMode: "disable"`.

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

## Guardrails

- **config-chunks NEVER writes security config.** No `settings.json`,
  `config.toml`, or `permissions.json` writes from this skill — recommend, show,
  delegate. This is the hard architectural rule.
- **Read the profile live.** Always pull provider config from
  `../../references/permission-profiles.md` at run time; never assert permission
  facts from memory (they drift post-cutoff). File missing → say so and stop.
- **Least privilege, always.** Recommend the Cautious posture; never default a
  user up the ladder or near the bypass footgun.
- **Plain language.** Translate every dial into what it lets the agent do. If you
  must use a provider's term, define it in one clause.
- **Honest framing.** It's a starting point to review, not certified-secure; the
  user owns what they approve. Say that, in those words, before any write.
- **Detect, don't assume.** Confirm provider + surface before recommending — the
  posture differs by surface, and a wrong guess gives unsafe advice.
