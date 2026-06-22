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

To ship this chunk from your plugin:
  1. Put this file in your plugin's `chunks/` dir.
  2. Copy config-chunks/scripts/publish-chunks.sh into your plugin's
     `scripts/` dir.
  3. Add a SessionStart hook running it (see publish-chunks.sh header).
-->
