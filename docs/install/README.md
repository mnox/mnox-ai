# Installing mnox-ai — per-provider guides

mnox-ai is a **distribution repo**: its skills, the `session-tracker` MCP utility,
and the `bash-gate` hook are meant to be installed *into your host*, not run from
this checkout. How you install depends on the host — pick your guide:

- **[Claude Code](./claude.md)** — native host; plugin marketplace with true
  à la carte + bundle installs. Everything ports here.
- **[OpenAI Codex CLI](./codex.md)** — native `SKILL.md` support via the exporter;
  MCP wired in `~/.codex/config.toml` (tools-only).
- **[Cursor](./cursor.md)** — reads `~/.claude/skills/` directly (often zero-copy);
  MCP wired in `.cursor/mcp.json` (full surface).

For the *why* behind this layout — the portable core vs. Claude adapters — see
[`docs/provider-agnostic.md`](../provider-agnostic.md).

## The core distinction: à la carte vs. all-skills

| | À la carte (one skill) | All-skills (the bundle) |
|---|---|---|
| **Claude Code** | `/plugin install <name>@mnox-ai` | `/plugin install all-skills@mnox-ai` |
| **Codex / Cursor / others** | `export_skills.py --skill <name>` | `export_skills.py` (no `--skill` = all) |

Only Claude Code has a marketplace, so only Claude gets a true *install primitive*
for the choice. On every other host the "bundle vs. one" decision is just **which
folders the exporter drops into the host's skills directory** — same mechanism,
scoped by `--skill` flags.

## Capability matrix

| Host | Skills (`SKILL.md`) | MCP (`session-tracker`) | `bash-gate` hook | Auto session-indexing |
|---|---|---|---|---|
| **Claude Code** | ✅ marketplace + skills dir | ✅ auto-wired via plugin | ✅ native | ✅ (lifecycle hooks) |
| **Codex** | ✅ `.agents/skills/` · `~/.codex/skills/` | ⚠️ manual `config.toml`, **tools-only** | ❌ not available | ❌ backfill only |
| **Cursor** | ✅ reads `.claude/skills/` too | ⚠️ manual `.cursor/mcp.json`, full surface | ❌ not available | ❌ backfill only |

✅ ports clean · ⚠️ works with manual setup / caveats · ❌ host-specific, doesn't port

## Verify an install

`scripts/smoke_host_load.py` proves the skills land where each host discovers them
(placement + frontmatter + engine bundling + a resolved-absolute MCP snippet):

```bash
python3 scripts/smoke_host_load.py                 # automated checks, all hosts
python3 scripts/smoke_host_load.py --host codex --live   # real host-load probe (model call)
```

## Other AGENTS.md / MCP-capable hosts

The big three above have dedicated guides. Every other skills- or MCP-aware host
follows the same two mechanisms:

- **Skills** — export the portable folders into the host's skill directory:
  `python3 scripts/export_skills.py --output-dir <host-skills-dir>` (add
  `--skill X` for à la carte, `--with-engine` for `config-chunks`).
- **MCP** — register `session-tracker` in that host's MCP config with a **real
  absolute path** to `plugins/session-tracker/bin/server.sh` and `command: bash`.

Host-specific discovery paths and quirks (verify against each vendor's current
docs before relying on them):

| Host | Skills dir | MCP config | Notes |
|---|---|---|---|
| **Gemini CLI** | per Gemini extension docs | `.gemini/settings.json` | `GEMINI.md` is default context; add a `context` block to prefer `AGENTS.md`. |
| **GitHub Copilot** | CLI skills support | ships GitHub MCP | Merges root `AGENTS.md` + `copilot-instructions.md`; path-scoped `*.instructions.md`. |
| **Zed** | native Skills (replaced Rules) | ✅ | Reads `AGENTS.md`/`CLAUDE.md`; also an ACP host that can run other agents as sub-agents. |
| **Windsurf** | emerging | ✅ | Auto-discovers `AGENTS.md`/`CLAUDE.md`; `.windsurf/rules/`. |
| **Aider** | ❌ no skills | server-only, not a client | Point `--read` at `AGENTS.md`. |
| **Continue.dev** | ❌ (rules are the primitive) | ✅ any MCP server | `.continue/rules/`. |

Universal caveats on any non-Claude host: `bash-gate` doesn't port; `session-tracker`
gets no auto-indexing (MCP tools work over backfilled data); MCP **prompts/resources**
are patchily implemented (tools are safe); skill auto-invocation is model-dependent;
bundled `scripts/` execute only if the host's sandbox allows.
