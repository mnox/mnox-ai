---
name: chunks
description: Manage guidance chunks — toggle subscription to chunk groups and standalone chunks in `~/.claude/config/chunks.yaml`, set which host files receive the bundle, or run a doctor check on the config. Use when the user says "/chunks", "list my chunks", "what chunks am I on", "add a chunk group", "opt into a chunk", "subscribe me to <group/chunk>", "unsubscribe from <group/chunk>", "set chunk targets", "diagnose my chunks config", "fix my chunks.yaml", or otherwise wants to change which guidance chunks land in their CLAUDE.md / AGENTS.md bundle. The skill drives the engine script — it never hand-edits YAML.
---

# chunks

## Overview

`~/.claude/config/chunks.yaml` is the user's opt-in switchboard for the
guidance-chunk library shipped by `config-chunks`. Chunks are versioned guidance
files; you opt in either by **group** (a named bundle of chunk slugs) or by an
individual **chunk slug**. This skill toggles entries on that switchboard via the
engine script — which is BSD-awk-safe, idempotent, and re-publishes + reconciles
after every mutation so the change lands in `~/.claude/chunks/bundle.md`
immediately — no session restart needed.

`targets:` selects which host instruction files receive the assembled bundle:

- `claude` → a marker-wrapped `@import` line in `~/.claude/CLAUDE.md`
- `agents` → the bundle body inlined into the AGENTS.md target

Omitting `targets:` auto-detects (CLAUDE.md / AGENTS.md if present).

**Never hand-edit `chunks.yaml` from this skill.** The reconciler's parser only
accepts block-form YAML; inline form (`groups: [recommended]`) silently parses
to empty and the user's bundle goes wrong without an error.

## When to use

- *"subscribe me to the recommended chunk group"* → `add-group recommended`
- *"unsubscribe from recommended"* → `remove-group recommended`
- *"toggle recommended"* → `toggle-group recommended`
- *"add the <slug> chunk directly"* → `add-chunk <slug>`
- *"remove the <slug> chunk"* → `remove-chunk <slug>`
- *"what chunks am I on"* / *"list my chunks"* → `list`
- *"write the bundle into AGENTS.md too"* → `add-target agents`
- *"only maintain CLAUDE.md"* → `set-targets claude`
- *"my chunks config feels off"* / *"diagnose"* / *"fix my chunks.yaml"* → `doctor`

## How to invoke

The engine is `scripts/chunks-config.sh` at the **plugin root** — this skill
lives at `<plugin-root>/skills/chunks/SKILL.md`, so the engine is two directories
up. Build an **absolute** path to it first; do not rely on a bare `../../` path,
which only resolves when the shell's working directory happens to be this skill
directory (Claude Code sets that, but other hosts may run from elsewhere):

```bash
# Home resolution, highest precedence first — matches the engine itself:
#   CONFIG_CHUNKS_HOME  set by install.sh / `export_skills.py --with-engine` on
#                       non-Claude hosts (Cursor, Codex, …).
#   CLAUDE_PLUGIN_ROOT  exported by Claude Code.
#   <plugin-root>       the absolute path you read this skill from, if neither
#                       env var is set (two levels above this file).
ENGINE="${CONFIG_CHUNKS_HOME:-${CLAUDE_PLUGIN_ROOT:-<plugin-root>}}/scripts/chunks-config.sh"
bash "$ENGINE" <command> [args]
```

You already know `<plugin-root>`'s absolute path — it's the directory two levels
above this skill file. Reuse `$ENGINE` for every command below.

### Commands

| Command | Effect |
|---|---|
| `list` | Show current group/chunk subscriptions, active targets, resolved slug set, and what's available. |
| `doctor` | Ensure the config exists, validate block-form, flag the inline-form footgun, validate targets, list unknown subscriptions, and flag unpublished slugs. |
| `add-group <name>` | Subscribe to a group. Idempotent. |
| `remove-group <name>` | Unsubscribe from a group. Idempotent. |
| `toggle-group <name>` | Flip subscription state for a group. |
| `add-chunk <slug>` | Opt into a standalone chunk (bypasses group membership). |
| `remove-chunk <slug>` | Drop a standalone chunk. |
| `toggle-chunk <slug>` | Flip subscription state for a standalone chunk. |
| `add-target <claude\|agents>` | Add a host target. Idempotent. Only `claude` or `agents` are valid. |
| `set-targets <claude\|agents>...` | Replace the entire target set with the listed values (dedup, order preserved). |

All mutations automatically re-publish first-party chunks and run the reconciler
so `bundle.md` and the host files stay up to date.

## Step 1 — Resolve the user's intent

Pick the smallest matching command. If the user names something ambiguous
("subscribe me to recommended"), prefer `add-group` over `add-chunk` — groups
are the canonical opt-in vehicle. Fall back to `add-chunk` only when the user
explicitly references a slug.

For target changes: use `add-target` when the user wants to *add* a host file
without disturbing the others; use `set-targets` when they want the target set
to be *exactly* what they named ("only CLAUDE.md").

If the user asks for a status check ("what am I subscribed to", "is chunk X on
for me"), use `list`. If they describe a problem ("my bundle didn't update",
"the chunk isn't showing up"), run `doctor` first.

## Step 2 — Run the command

Run the engine via Bash. Capture stdout and stderr.

## Step 3 — Report back

Reflect the engine's result in one or two sentences. Quote the relevant line of
output (e.g., `added: groups += recommended` or `set-targets: targets = claude
agents`). If the engine reported `already subscribed` / `not subscribed` /
`already a target`, say so plainly — don't pretend a mutation happened.

For `doctor`, surface every `✗` line verbatim with the recommended fix. For
`list`, summarize: groups subscribed, standalone chunks, active targets,
resolved slug count, and any foreign-plugin chunks visible (those are not
togglable here).

If `doctor` reports an inline-form list, do not auto-rewrite the file — tell the
user exactly what to change and where. The engine is conservative by design and
refuses to mutate a key that is in non-empty inline form.

## What this skill does not do

- It does not install or uninstall the plugin itself — that is a marketplace
  operation.
- It does not toggle foreign-plugin chunks. Those are gated by whether the
  contributing plugin is installed and publishing; toggling lives at the plugin
  layer, not here.
- It does not edit `~/.claude/CLAUDE.md` or the AGENTS.md target directly — only
  the reconciler manages the marker-wrapped block / inlined body.
