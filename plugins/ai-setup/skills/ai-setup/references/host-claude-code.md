# Host Adapter — Claude Code

Where each layer lives on Claude Code and how to apply and verify it. Claude
Code is the reference host: every layer is available.

> **Verify before use.** This file was checked against Claude Code 2.1 and its
> documentation in late 2026. Mechanics drift. Before applying anything, run the
> relevant `--help` (commands below) and prefer what the installed CLI and the
> live docs at `code.claude.com/docs` say over this file. Record any difference
> in the plan.

**Contents**
- [Preflight](#preflight)
- [Layer map](#layer-map)
- [Instructions and rules](#instructions-and-rules)
- [Skills and subagents](#skills-and-subagents)
- [Plugins and marketplaces](#plugins-and-marketplaces)
- [MCP servers](#mcp-servers)
- [Settings: permissions and hooks](#settings-permissions-and-hooks)
- [Code intelligence](#code-intelligence)
- [Verification commands](#verification-commands)
- [Surfaces](#surfaces)

## Preflight

```bash
claude --version
claude plugin --help
claude mcp --help
```

If the `claude` CLI is not on the path (desktop or IDE-only installs), every CLI
step below becomes a human step using the in-session equivalents (`/plugin`,
`/mcp`). Say so in the plan.

## Layer map

| Layer | User scope | Repo scope (committed) | Repo local (git-ignored) |
|---|---|---|---|
| Instructions | `~/.claude/CLAUDE.md` | `CLAUDE.md` or `.claude/CLAUDE.md` | `CLAUDE.local.md` |
| Path-scoped rules | `~/.claude/rules/*.md` | `.claude/rules/**/*.md` | — |
| Skills | `~/.claude/skills/<name>/SKILL.md` | `.claude/skills/<name>/SKILL.md` | — |
| Subagents | `~/.claude/agents/<name>.md` | `.claude/agents/<name>.md` | — |
| Settings | `~/.claude/settings.json` | `.claude/settings.json` | `.claude/settings.local.json` |
| MCP servers | user scope via `claude mcp add -s user` | `.mcp.json` | local scope (default) |
| Plugins | `-s user` | `-s project` | `-s local` |

## Instructions and rules

- `CLAUDE.md` files load at session start. A file can import another with
  `@path`; relative paths resolve from the importing file, and import nesting is
  depth-limited. Imports pointing outside the project prompt for approval once.
- `AGENTS.md` can be loaded in place of `CLAUDE.md`; check the memory
  documentation for the current precedence. Where both must exist, keep the
  content in `AGENTS.md` and make `CLAUDE.md` a thin file: an `@AGENTS.md`
  import plus Claude-only extras.
- Rules are markdown files under `.claude/rules/`, discovered recursively. A
  rule with no frontmatter loads at launch like `CLAUDE.md`. A rule whose
  frontmatter has `paths` (glob patterns) loads only when a matching file is
  read or edited:

  ```markdown
  ---
  paths:
    - "src/components/**/*.tsx"
  ---

  Components here are client components; data loading belongs in the route.
  ```

  `paths` is the only frontmatter field a rule uses. Path-scoped rules are
  reloaded on demand after context compaction, and cloud sessions load only
  rules without `paths` — so a rule that must always hold has no `paths` or
  lives in `CLAUDE.md`.

## Skills and subagents

- A skill is a directory containing `SKILL.md` with `name` and `description`
  frontmatter; `name` equals the directory name. Authored practice skills go in
  `.claude/skills/` (team) or `~/.claude/skills/` (personal).
- A subagent is a markdown file whose frontmatter gives `name`, `description`
  (when to delegate to it), and optionally the tools and model it may use; the
  body is its system prompt.
- Both are plain files: write them, then validate
  ([Verification commands](#verification-commands)).

## Plugins and marketplaces

A plugin bundles skills, subagents, commands, hooks, MCP servers, or language
servers. Plugins come from marketplaces.

```bash
claude plugin marketplace list --json
claude plugin marketplace add <github-owner/repo | url | path> --scope <user|project|local>

claude plugin list --json --available
claude plugin details <plugin>
claude plugin install <plugin>@<marketplace> --scope <user|project|local>
```

- `plugin list --json --available` shows installed plugins and what the
  configured marketplaces offer — the host-catalog scout's primary source.
- `plugin details` reports a plugin's component inventory and **projected token
  cost**. Read it before recommending a plugin; it is the standing-cost figure
  for the vetting rubric.
- The official Anthropic marketplace is named `claude-plugins-official`.
  Confirm it is configured with `marketplace list` before relying on it.
- Scope decides who gets it: `user` for the engineer everywhere, `project`
  records it in the repo's committed settings so teammates are offered it,
  `local` keeps it personal to this repo.
- Installs take effect in a new session. Report them as needing a restart, not
  as verified.
- A marketplace-declared install command needs explicit acceptance when there
  is no terminal (`--yes`). Do not pass it for a T2 plugin without the engineer
  having approved that plugin by name.

## MCP servers

```bash
claude mcp list
claude mcp add --scope <local|user|project> --transport http <name> <url>
claude mcp add --scope <local|user|project> <name> -- <command> [args...]
claude mcp get <name>
claude mcp login <name>
```

- Scopes: `local` (default; this repo, this user), `project` (written to
  `.mcp.json`, committed, teammates approve it on first use), `user` (every
  repo).
- Prefer a vendor's remote HTTP endpoint with browser sign-in. Authentication
  (`claude mcp login`, or `/mcp` in a session) is always a human step.
- A server that needs a secret gets it from an environment variable the
  engineer sets. Never pass a secret on the command line you construct, and
  never write one into `.mcp.json`.
- Project-scoped servers show as pending until the engineer approves them.

## Settings: permissions and hooks

Settings merge across user, project, and local files; a deny rule wins at every
level and rules evaluate deny, then ask, then allow.

Permissions:

```json
{
  "permissions": {
    "allow": ["Bash(pnpm run test:*)", "Bash(pnpm run lint)", "Bash(pnpm run typecheck)"],
    "ask": ["Bash(git push:*)"],
    "deny": ["Read(./.env)", "Read(./.env.*)"]
  }
}
```

Build allow rules only from commands verified during this setup, as narrowly as
the syntax allows. Read-only operations already run without a rule. Writing
this block is a separately confirmed step (`layer-rules.md`); where a
config-editing skill exists on the host, prefer driving that over editing the
file directly.

Hooks:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{ "type": "command", "command": "<format the edited file>" }]
      }
    ],
    "Stop": [
      { "hooks": [{ "type": "command", "command": "<typecheck>" }] }
    ]
  }
}
```

- The hook receives the event as JSON on standard input, including the edited
  file's path for edit events. Matchers compare against tool names and are
  case-sensitive.
- `Stop` takes no matcher and fires whenever the agent finishes responding. A
  `Stop` hook that exits with code 2 sends its output back and keeps the agent
  working — use it only for checks that fail for reasons the agent can fix.
- Team guards go in the committed `.claude/settings.json`; personal ones in the
  user file.
- When merging into an existing settings file: parse it, add only new entries,
  preserve every existing key and its order, and re-parse the result before
  writing. A malformed settings file disables the whole file.

## Code intelligence

Language-server plugins give the agent definitions, references, and
diagnostics. The official marketplace publishes them per language
(`<language>-lsp@claude-plugins-official`). Two things to tell the engineer:

- The plugin configures the connection; the language-server binary is installed
  separately with the language's own package manager. That install is a human
  step.
- Language servers started by plugins do not run in cloud sessions.

## Verification commands

| Check | Command |
|---|---|
| Authored skills, subagents, and commands are well-formed | `claude plugin validate <directory>` (add `--strict` to fail on warnings) |
| Plugins registered | `claude plugin list --json` |
| Servers configured and reachable | `claude mcp list` |
| Settings files parse | covered by `verify_setup.py` (`json` check) |
| Instruction files loaded | In a new session, `/memory` lists what was loaded — a playbook smoke step |

## Surfaces

- **Terminal, IDE extension, desktop app:** the same files and settings apply.
- **Cloud sessions:** user-level configuration under `~/.claude` does not
  apply. Only what is committed to the repo does — so anything the team needs in
  cloud sessions must be repo-scoped, and path-scoped rules and plugin language
  servers are unavailable there.
