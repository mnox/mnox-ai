# Installing mnox-ai on Cursor

**Headline: if you already use Claude Code, you may not have to install anything.**
Cursor 2.4+ reads Agent Skills from `~/.claude/skills/` and `.claude/skills/`
**directly** — the biggest cross-host compatibility win in the ecosystem. Any
mnox-ai skill you've installed for Claude Code is already visible to Cursor.

Like Codex, Cursor has **no plugin marketplace**, so "à la carte vs. all-skills"
is *which folders land in a skills directory* — the exporter's `--skill` flag is
à la carte; its default is the full bundle.

## Prerequisites

- Cursor 2.4 or later (native Skills support).
- This repo cloned locally. `MNOX_AI` below = its absolute path.

## 1. Install skills

### Already a Claude Code user? Do nothing.

Cursor scans `~/.claude/skills/` and `<project>/.claude/skills/` automatically. If
your skills are there (via the Claude marketplace or the exporter), Cursor picks
them up as-is. Confirm in the Cursor Skills UI.

### Otherwise — export into a Cursor skills directory

Cursor also discovers **`.cursor/skills/`** (project) and **`~/.cursor/skills/`**
(user-global):

```bash
# the whole set, user-global
python3 scripts/export_skills.py --output-dir ~/.cursor/skills --overwrite

# à la carte
python3 scripts/export_skills.py --output-dir ~/.cursor/skills \
  --skill schema-review --skill debut --overwrite
```

Valid `--skill` names: `aio`, `compliance-review`, `curriculum`, `debut`,
`diagnose-queries`, `foundry-run`, `ontology-review`, `retrieval-review`,
`schema-review`, `strangler-fig`, `util-review`, `create-skill`, plus the
`config-chunks` skills (`ai-setup`, `chunks`, `chunk-review`, `ideation`,
`permission-setup`) and `bash-gate-add`.

> `foundry-run` exports but is **decommissioned for public use** — it now
> routes into the maintainer's private Sven Unit runtime, not distributed
> here. See [`plugins/foundry/README.md`](../../plugins/foundry/README.md).

### Engine-backed skills (`config-chunks`)

`config-chunks` skills need their engine co-located off Claude:

```bash
python3 scripts/export_skills.py --output-dir ~/.cursor/skills \
  --skill ai-setup --skill chunks --with-engine
# → export CONFIG_CHUNKS_HOME=~/.cursor/skills/.engines/config-chunks
```

See [`plugins/config-chunks/README.md`](../../plugins/config-chunks/README.md) for
the one-line `AGENTS.md` bootstrap.

## 2. Wire the MCP utility (`session-tracker`)

Add it to `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global). Use a real
absolute path — never `${CLAUDE_PLUGIN_ROOT}`:

```json
{
  "mcpServers": {
    "session-tracker": {
      "command": "bash",
      "args": ["MNOX_AI/plugins/session-tracker/bin/server.sh"]
    }
  }
}
```

Cursor supports the full MCP surface (tools + prompts + resources, plus
Roots/Elicitation). `${workspaceFolder}` and `${env:NAME}` interpolation are
available if you prefer them to a hardcoded path. Requires [Bun](https://bun.sh)
on your `PATH`.

## What does NOT port to Cursor

- **`bash-gate`** — a Claude Code PreToolUse hook; no Cursor equivalent. Not
  available.
- **`session-tracker` auto-indexing** — Claude-only lifecycle hooks. MCP tools
  work over already-indexed / backfilled data
  (`plugins/session-tracker/bin/backfill.sh`); no automatic session capture.
- **Inline Edit** ignores skills and user rules entirely — skills fire only in
  **Agent / Chat** mode.
- **Script execution** — bundled `scripts/` run subject to Cursor's sandbox.
- **Auto-invocation** is model-dependent — invoke explicitly when a skill must run.

## Notes

- Cursor's own instruction primitive is `.cursor/rules/*.mdc` (the legacy
  `.cursorrules` is deprecated and ignored in Agent mode). Cursor also reads
  `AGENTS.md`. Skills and rules coexist.

Docs: <https://cursor.com/docs/skills> · <https://cursor.com/docs/context/rules>
