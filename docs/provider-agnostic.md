# Provider-Agnostic Architecture

`mnox-ai` now treats provider support as an adapter layer. The portable core is:

1. **Agent Skills**: each skill is a folder with `SKILL.md` plus optional
   `scripts/`, `references/`, `templates/`, `assets/`, or `agents/`.
2. **MCP utilities**: runtime tools, such as `session-tracker`, expose an MCP
   server entrypoint that any MCP-capable host can launch.
3. **Repo guidance**: `AGENTS.md` carries provider-neutral instructions for
   coding agents working in this repository.

The existing `.claude-plugin/` files remain the Claude Code marketplace adapter.
They should mirror the portable core, not define it.

## Export Skills

Use the exporter to copy the canonical skills into any host's skills directory:

```bash
python3 scripts/export_skills.py --output-dir ./.codex/skills
python3 scripts/export_skills.py --output-dir ./.cursor/skills
python3 scripts/export_skills.py --output-dir ~/.codex/skills --overwrite
```

The exporter writes a `skills-manifest.json` in the output directory so downstream
tools can see where each copied skill came from.

Use `--mode symlink` when the destination supports symlinks and you want live
edits in this repo to be visible to the host:

```bash
python3 scripts/export_skills.py --output-dir ./.codex/skills --mode symlink --overwrite
```

## Provider Adapters

Claude Code can still install from the marketplace:

```bash
/plugin marketplace add mnox/mnox-ai
/plugin install schema-review@mnox-ai
```

Other skills-compatible clients should point at the exported skill directory or
copy individual `plugins/<name>/skills/<skill>` folders into their own skills
location.

## Utilities And MCP

`session-tracker` is a local MCP server. Claude users get automatic hook wiring
from the Claude plugin adapter. Other MCP clients can launch it directly:

```json
{
  "mcpServers": {
    "session-tracker": {
      "command": "bash",
      "args": ["plugins/session-tracker/bin/server.sh"]
    }
  }
}
```

Lifecycle hooks are host-specific. Without hooks, the MCP tools still work for
already-indexed data and manual backfills; hosts that expose session lifecycle
events can wire those events to the scripts in `plugins/session-tracker/bin/`.

## Compatibility Checklist

- `SKILL.md` frontmatter has `name` and `description`.
- Bundled helper scripts resolve relative to the skill folder.
- Skill prose does not require Claude-only commands, variables, or model names.
- Provider-specific hooks and manifests live in adapter directories.
- Utilities document MCP launch commands and environment variables.
