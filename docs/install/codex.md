# Installing mnox-ai on OpenAI Codex CLI

Codex reads the open **Agent Skills** (`SKILL.md`) standard natively, so the
skills in this repo run unmodified — but Codex has **no plugin marketplace**. The
"à la carte vs. all-skills" choice becomes *which folders you export*: the
exporter's `--skill` flag is à la carte; its default (no flag) is the full bundle.

## Prerequisites

- Codex CLI installed and configured.
- This repo cloned locally. Note its absolute path — you'll need it for MCP wiring.
  Below, `MNOX_AI` stands for that path (e.g. `/Users/you/dev/mnox-ai`).

## 1. Install skills

Codex discovers skills in **`.agents/skills/`** (project) or **`~/.codex/skills/`**
(user-global). Export the portable folders there:

### The whole set — one shot

```bash
# user-global (available in every Codex session)
python3 scripts/export_skills.py --output-dir ~/.codex/skills --overwrite

# or project-local
python3 scripts/export_skills.py --output-dir ./.agents/skills --overwrite
```

### À la carte — just the ones you want

```bash
python3 scripts/export_skills.py --output-dir ~/.codex/skills \
  --skill schema-review --skill debut --overwrite
```

Valid `--skill` names: `aio`, `compliance-review`, `curriculum`, `debut`,
`diagnose-queries`, `foundry-run`, `ontology-review`, `retrieval-review`,
`schema-review`, `strangler-fig`, `util-review`, `create-skill`, plus the
`config-chunks` skills (`ai-setup`, `chunks`, `chunk-review`, `ideation`,
`permission-setup`) and `bash-gate-add`.

> **Path trap.** `.codex/skills/` is **not** a discovery path — it's
> `.agents/skills/` (project) or `~/.codex/skills/` (user). Exporting to the wrong
> place is a silent no-op: Codex finds nothing and never tells you.

### Share one copy with Claude Code (symlink)

If you already use Claude Code, Codex follows symlinks — point its skills dir at
your existing Claude skills instead of a second copy:

```bash
ln -s ~/.claude/skills ~/.codex/skills
```

### Engine-backed skills (`config-chunks`)

`config-chunks` skills call an on-disk engine that lives outside the skill folder.
Off Claude there's no `${CLAUDE_PLUGIN_ROOT}`, so bundle the engine and export the
env var it prints:

```bash
python3 scripts/export_skills.py --output-dir ~/.codex/skills \
  --skill ai-setup --skill chunks --with-engine
# → export CONFIG_CHUNKS_HOME=~/.codex/skills/.engines/config-chunks
```

The fastest path for `config-chunks` specifically is its own bootstrap, which
wires a host's `AGENTS.md` directly — see
[`plugins/config-chunks/README.md`](../../plugins/config-chunks/README.md).

## 2. Wire the MCP utility (`session-tracker`)

Add it to `~/.codex/config.toml`. Codex needs a **real absolute path** — never a
repo-relative path or `${CLAUDE_PLUGIN_ROOT}` (Claude-only):

```toml
[mcp_servers.session-tracker]
command = "bash"
args = ["MNOX_AI/plugins/session-tracker/bin/server.sh"]   # ← substitute the real absolute path
```

Or with the CLI: `codex mcp add`. Requires [Bun](https://bun.sh) on your `PATH`.

## What does NOT port to Codex

- **`bash-gate`** — a Claude Code PreToolUse hook. Codex has no equivalent hook
  surface; not available.
- **`session-tracker` auto-indexing** — the lifecycle hooks that auto-capture
  sessions are Claude-only. On Codex the MCP **tools still work**, but only over
  data you've already indexed or backfilled (`plugins/session-tracker/bin/backfill.sh`).
  No automatic session capture.
- **MCP prompts / resources** — Codex is **tools-only**. Any MCP prompt or
  resource a server exposes is silently ignored (session-tracker's tools are
  unaffected).
- **Parallel sub-agent fan-out** — skills that fan work across sub-agents degrade
  to single-context on Codex.
- **Script execution** — a skill's bundled `scripts/` run only if Codex's sandbox
  permits; some skills degrade to read-only instructions.

## Notes

- Codex concatenates `AGENTS.md` **root → cwd** (later overrides), with a global
  at `~/.codex/AGENTS.md` and a 32 KiB cap.
- Skill auto-invocation is model-dependent — *which* skill fires for a borderline
  description varies. Invoke explicitly when it must run.

Docs: <https://developers.openai.com/codex/skills> ·
<https://developers.openai.com/codex/mcp>
