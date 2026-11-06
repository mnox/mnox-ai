# Host Matrix — layers on hosts other than Claude Code

The profile, slot table, vetting, practice skills, and instruction content are
host-neutral. What differs per host is where each layer lives and which layers
exist at all. Claude Code has its own adapter (`host-claude-code.md`); this file
covers the rest.

> **Verify before use.** Paths and capabilities here reflect each host's
> documentation as of mid-to-late 2026 and move quickly. Confirm against the
> host's own docs before applying, and record differences in the plan.

**Contents**
- [Layer availability](#layer-availability)
- [Fallbacks for missing layers](#fallbacks-for-missing-layers)
- [Per-host notes](#per-host-notes)
- [Engineers on more than one host](#engineers-on-more-than-one-host)

## Layer availability

| Layer | Codex | Cursor | Any host that reads `AGENTS.md` |
|---|---|---|---|
| Global instructions | `~/.codex/AGENTS.md` | User rules in the app's settings (a human step) | Host-specific; often none |
| Repo instructions | `AGENTS.md`, concatenated from the repo root down to the working directory | `AGENTS.md`, plus `.cursor/rules/*.mdc` | `AGENTS.md` |
| Path-scoped rules | A nested `AGENTS.md` in the subdirectory | `.cursor/rules/*.mdc` with glob frontmatter | A nested `AGENTS.md` |
| Skills | `.agents/skills/` (repo), `~/.codex/skills/` (user) | `.cursor/skills/`, `~/.cursor/skills/`; also reads `.claude/skills/` and `~/.claude/skills/` | `.agents/skills/` where supported |
| Plugins / marketplace | None | None | None |
| MCP servers | `[mcp_servers.<name>]` in `~/.codex/config.toml`; tools only | `.cursor/mcp.json` (repo), `~/.cursor/mcp.json` (user) | Host-specific |
| Lifecycle hooks | None | Check the host's docs | Usually none |
| Subagent definitions | None | Check the host's docs | Usually none |
| Permissions | Sandbox mode and approval policy in `~/.codex/config.toml` | Run mode in the app, plus `permissions.json` | Host-specific |
| Parallel delegation for this skill's fan-out | Degrades to one context | Varies | Assume sequential |

## Fallbacks for missing layers

When the host lacks a layer, drop to the next most deterministic portable
mechanism. Never substitute prose for a guard and call the slot filled.

| Missing layer | Fallback | Slot status |
|---|---|---|
| Plugin marketplace | Install the plugin's skills as plain skill folders in the host's skills directory. Its hooks and bundled servers do not come along — plan those separately | Filled if the skill was the point |
| Lifecycle hooks | A pre-commit hook and a CI job running the same repo scripts, plus one instruction line naming the command to run before finishing | Filled, weaker: the check runs at commit, not at edit |
| Path-scoped rules | A nested `AGENTS.md` in the directory | Filled |
| Subagent definitions | Fold the specialist's instructions into a skill | Filled without isolation — say so |
| Language-server integration | The type checker and linter as commands in the verification loop | Filled, slower |
| Global instruction file | Put person-scoped lines in the host's user-rules setting as a human step | `needs-human` |
| Delegation | Run the scout and author lanes sequentially (SKILL.md, Degraded Modes) | — |

## Per-host notes

### Codex

- Skills are discovered in `.agents/skills/` (repo) and `~/.codex/skills/`
  (user). A `.codex/skills/` directory inside a repo is **not** a discovery
  path; writing there is a silent no-op.
- `AGENTS.md` files are concatenated from root to working directory, with later
  files overriding, under a total size cap. Keep the root file within the
  instruction budget and put package specifics in nested files.
- MCP configuration needs absolute paths for local servers. Codex exposes MCP
  tools only; prompts and resources a server offers are ignored.
- There is no hook surface: the `guards` slot is filled by pre-commit and CI.
- Bundled scripts run only as far as the sandbox permits; when blocked, use the
  manual path in SKILL.md's Degraded Modes.

### Cursor

- Cursor reads Claude Code's skill directories directly. If the engineer also
  uses Claude Code, install skills once in `.claude/skills/` and do not copy
  them.
- `.cursor/rules/*.mdc` is the native rule format and supports glob scoping; it
  is the right home for path-scoped conventions. The legacy single-file rules
  format is ignored in agent mode.
- Skills and rules apply in agent and chat modes, not in inline edit.
- Permission posture is partly a setting in the app. Treat it as a human step
  with the exact menu path.

### Other hosts

Assume the portable minimum: a repo `AGENTS.md`, skills in `.agents/skills/` if
the host supports the Agent Skills format, and MCP if the host supports it.
Everything else uses the fallbacks above. Hosts with no skill support get the
practice skills' Quick Reference tables condensed into a nested `AGENTS.md` near
the code they govern — a lossy port; say so.

### Permissions on any host

Permission configuration is host-specific security configuration. Where a
dedicated permission skill is installed (such as `/permission-setup`), hand the
posture to it and contribute only the stack-specific command list. Otherwise
present the host's documented conservative settings with their file location or
menu path as a human step. Do not write another host's security configuration
from memory.

## Engineers on more than one host

Keep one copy of everything that can be shared:

| Layer | Single source | How the other hosts see it |
|---|---|---|
| Repo instructions | `AGENTS.md` | A thin host-specific file that imports or points to it, only for hosts that need one |
| Skills | One directory | Hosts that read it directly need nothing; for the rest, a symlink from their skills directory where the host follows symlinks, otherwise a copy recorded in the manifest so re-runs refresh it |
| Practice skills | Authored once, in portable form (`name` and `description` frontmatter only, no host-specific features) | As skills above |
| MCP servers | None — each host has its own configuration file | Configure per host; record each as its own manifest item |
| Guards | The repo's own scripts | Each host's hook surface, or pre-commit and CI, calls the same scripts |

Record the primary host first in `profile.hosts`. Verification in Phase 6 runs
against the primary host; secondary hosts are checked statically and listed in
the playbook with their own smoke prompts.
