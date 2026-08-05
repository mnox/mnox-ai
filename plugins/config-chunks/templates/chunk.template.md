---
name: my-chunk-name
version: 1.0.0
owner: config-chunks
order: 50
summary: One-line description of what this guidance does and why it belongs in every agent-instruction file.
---

## My Section Heading

The actual agent-instruction content goes here. Everything below the closing
`---` is what gets injected, verbatim, into every subscriber's host
instruction file (CLAUDE.md via @import, AGENTS.md inlined).

Keep it tight — imported content costs context tokens exactly like inline
content. Run the `chunk-review` skill before opening a chunk PR.

<!--
Frontmatter contract:
  name     — unique kebab-case slug. The bundle dedup key: two plugins
             shipping the same `name` collapse to one (highest version wins).
  version  — semver. Bumps trigger a reconcile even before the sync TTL.
  owner    — the plugin that owns this chunk (kebab-case slug).
             Used to name the published file: registered/<owner>.<name>.md
  order    — integer sort key within the bundle. The instruction file is a
             sequence: later instructions can override earlier ones, so order
             matters. Convention: 0-20 foundational, 40-60 normal, 80-100 last.
  summary  — one-line human description for review + catalog purposes.

Optional progressive-disclosure keys (see templates/pointer-chunk.template.md):
  disclosure — `inline` (default) or `pointer`. Pointer chunks render as a
               compact stub (rule + → load <skill>) and use a tighter 400-char
               body cap. Inline chunks render in full and use a 2000-char cap.
  skill      — required iff disclosure: pointer. Slug of the skill that holds
               the full procedure / examples.

Optional replacement key:
  supersedes — comma-separated `name`s this chunk REPLACES. Each named chunk is
               dropped from the bundle entirely. Use it when your chunk restates
               another's substance (e.g. a local chunk binding a universal
               chunk's generic steps to concrete tools) — shipping both is
               duplicated always-on context tax, and version-dedup cannot
               collapse them because the `name`s differ.

               Owner-blind: a local chunk may supersede a first-party one and
               vice versa. Naming an absent chunk is a silent no-op. Applied
               drops are announced on every reconcile.

               RIDER vs REPLACEMENT: only supersede when your chunk carries the
               other's substance. If it merely ADDS local specifics on top, it
               is a rider — ship both and say "Rides on **<name>**" in the body.
               Before superseding, move any prose the target holds and yours
               lacks INTO yours; the supersede silently deletes the rest.

               Chains are rejected fail-closed: if a chunk both declares
               `supersedes` and is itself superseded, the reconcile aborts and
               the previous bundle survives. Flatten instead — have the one
               surviving chunk name every target directly.

To ship this chunk from your plugin:
  1. Put this file in your plugin's `chunks/` dir.
  2. Copy config-chunks/scripts/publish-chunks.sh into your plugin's
     `scripts/` dir.
  3. Add a SessionStart hook running it (see publish-chunks.sh header).
-->
