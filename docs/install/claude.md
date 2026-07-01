# Installing mnox-ai on Claude Code

Claude Code is the **native host** for this repo. It's the only host with a
first-class *à la carte vs. bundle* install primitive: the plugin marketplace.
Everything here — skills, the MCP utility, and the Bash hook — installs through it.

## 1. Add the marketplace (once)

```
/plugin marketplace add mnox/mnox-ai
```

## 2. Install skills

### À la carte — just the one you want

```
/plugin install schema-review@mnox-ai
```

Swap `schema-review` for any plugin: `aio`, `curriculum`, `strangler-fig`,
`compliance-review`, `util-review`, `debut`, `diagnose-queries`,
`ontology-review`, `retrieval-review`, `foundry`, `create-skill`, `config-chunks`.

### The whole set — one shot

```
/plugin install all-skills@mnox-ai
```

`all-skills` is a meta-plugin: it pulls in every reviewing/building skill as a
dependency. Remove them all again with:

```
claude plugin uninstall all-skills --prune
```

> **Scope note.** `all-skills` bundles the 11 core agentic skills (`aio`,
> `compliance-review`, `curriculum`, `debut`, `diagnose-queries`, `foundry`,
> `ontology-review`, `retrieval-review`, `schema-review`, `strangler-fig`,
> `util-review`). The tooling plugins — `config-chunks`, `create-skill`,
> `session-tracker`, `bash-gate` — install individually.

## 3. Wire the MCP utility (`session-tracker`)

```
/plugin install session-tracker@mnox-ai
```

On Claude Code this is the **easy path**: the plugin registers the MCP server
*and* wires the session lifecycle hooks automatically, so sessions index as you
work. Requires [Bun](https://bun.sh) on your `PATH`
(`brew install oven-sh/bun/bun`); dependencies install on first launch.

## 4. Install the Bash hook (`bash-gate`)

```
/plugin install bash-gate@mnox-ai
```

`bash-gate` is a **PreToolUse hook**, not a skill — it's Claude-Code-specific and
has no equivalent on other hosts. Ships safe-by-default (auto-allows nothing until
you opt in). See [`plugins/bash-gate/README.md`](../../plugins/bash-gate/README.md).

## Alternative: manual skills directory (no marketplace)

If you'd rather not use the marketplace, export the portable `SKILL.md` folders
straight into a Claude skills directory:

```bash
# everything, user-global
python3 scripts/export_skills.py --output-dir ~/.claude/skills --overwrite

# à la carte, project-local
python3 scripts/export_skills.py --output-dir .claude/skills \
  --skill schema-review --skill debut
```

Claude auto-loads each skill's name + description at startup; invoke manually with
`/schema-review`.

## What to know

- **Everything ports here** — this is the reference host.
- The `.claude-plugin/` marketplace files and `${CLAUDE_PLUGIN_ROOT}` engine
  resolution are **Claude-only adapters**. On other hosts you use the exporter
  (`--with-engine` for engine-backed skills like `config-chunks`). See the
  per-host guides in [`docs/install/`](./README.md).
