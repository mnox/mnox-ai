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
python3 scripts/export_skills.py --output-dir ./.agents/skills
python3 scripts/export_skills.py --output-dir ./.cursor/skills
python3 scripts/export_skills.py --output-dir ~/.agents/skills --overwrite
```

The exporter writes a `skills-manifest.json` in the output directory so downstream
tools can see where each copied skill came from.

Use `--mode symlink` when the destination supports symlinks and you want live
edits in this repo to be visible to the host:

```bash
python3 scripts/export_skills.py --output-dir ./.agents/skills --mode symlink --overwrite
```

### Engine-backed skills

Most skills are pure `SKILL.md` instructions and export cleanly. A few are backed
by an on-disk **engine** (scripts + data the skill invokes) that lives at the
plugin root, *outside* the per-skill folders the exporter copies. On Claude Code
the engine is found via `CLAUDE_PLUGIN_ROOT`; off Claude there's no such variable,
so exporting the skill alone would orphan its engine.

A plugin opts into engine bundling by shipping an `engine.json` at its root:

```json
{ "home_env": "CONFIG_CHUNKS_HOME", "paths": ["scripts", "chunks", "groups", "references", "templates"] }
```

Pass `--with-engine` to co-locate those paths under `<output>/.engines/<plugin>/`
and print the `export <HOME_ENV>=…` line that points the skills at the bundled
engine:

```bash
python3 scripts/export_skills.py --output-dir ./.cursor/skills \
  --skill ai-setup --skill chunks --with-engine
# → export CONFIG_CHUNKS_HOME=<output>/.engines/config-chunks
```

The skill resolves its engine home with the precedence `<HOME_ENV>` →
`CLAUDE_PLUGIN_ROOT` → an absolute fallback, so the one exported tree works on
both Claude and non-Claude hosts. `config-chunks` is the first engine-backed
plugin; see its README for the one-line `install.sh` bootstrap that wires a host's
`AGENTS.md` end to end.

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
