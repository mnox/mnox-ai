# mnox-ai

Matt Noxon's curated Agent Skills and local AI-agent utilities for building,
auditing, and refactoring software and AI systems. The portable core is standard
`SKILL.md` folders plus MCP utilities; Claude Code marketplace support is kept as
a provider adapter.

## What's inside

| Plugin | Category | What it does |
|---|---|---|
| `aio` | Agentic AI | Agentic Implementation Optimizer — audit existing agent implementations for reliability/cost/architecture issues, build new ones from scratch, or extend them with new capabilities. |
| `curriculum` | Learning | Generate a structured, adaptive learning curriculum for any topic — modules with a 5-part spine plus an append-only assessment loop that adapts future modules to the learner's answers. |
| `strangler-fig` | Refactoring | Clean-room legacy reimplementation — distill legacy code to functional requirements, rebuild greenfield behind a context firewall, verify behavioral parity, optionally cut over. |
| `schema-review` | Data | Review database schemas and in-code data structures (Ecto, Postgres DDL/migrations, dbt models, Elixir/TypeScript types) for correctness, integrity, performance, scalability, and design quality. |
| `compliance-review` | Compliance | Audit a repo, ADR/PRD, IaC posture, or live cloud state against SOC 2, HIPAA, or PCI-DSS — parallel control-domain agents produce findings with control IDs, severity, evidence, and remediation. |
| `util-review` | Tooling | Review Agent Skills, hooks, AGENTS.md/CLAUDE.md files, MCP configs, and workflow configs for design flaws, unclosed loops, stale references, side effects, and portability risks. |
| `debut` | Open Source | Audit a repo for public-readiness before open-sourcing — secrets/PII in history, licensing, community-health files, code quality, tests/CI, deps — scored SHIP IT / NEEDS POLISH / NOT READY with fix commands. |
| `diagnose-queries` | Data | Diagnose slow database queries across Postgres, the ORM layer (N+1), and Snowflake/dbt — five modes from known-query analysis to live-incident triage, ending in a root-caused, verified fix. |
| `config-chunks` | Tooling | Package manager for agent-instruction guidance — named, versioned "chunks" reconciled into your `CLAUDE.md` / `AGENTS.md` bundle, with guided onboarding (`/ai-setup`) and safe permission setup (`/permission-setup`). |
| `all-skills` | Bundle | Meta-plugin that installs every skill above at once. |
| `session-tracker` | Utility | **MCP server** (not a skill). Indexes and searches AI coding-agent sessions — list, search, label, inspect file-change history, view token usage. Lexical search by default; semantic search opt-in. Requires [Bun](https://bun.sh). |

## Installation

### Standard Agent Skills

Export the portable skills into the skills directory for your agent host:

```
python3 scripts/export_skills.py --output-dir ./.agents/skills
python3 scripts/export_skills.py --output-dir ./.cursor/skills
python3 scripts/export_skills.py --output-dir ~/.agents/skills --overwrite
```

You can export a subset with repeated `--skill` flags:

```
python3 scripts/export_skills.py --output-dir ./.agents/skills --skill schema-review --skill debut
```

See [`docs/provider-agnostic.md`](docs/provider-agnostic.md) for the portability
model, MCP setup notes, and provider-adapter guidance.

### Claude Code Marketplace

Claude Code users can add the marketplace once:

```
/plugin marketplace add mnox/mnox-ai
```

Then install à la carte — just the skill you want:

```
/plugin install schema-review@mnox-ai
```

…or grab the whole skill set in one shot:

```
/plugin install all-skills@mnox-ai
```

`all-skills` is a meta-plugin: installing it pulls in every skill as a
dependency, and `claude plugin uninstall all-skills --prune` removes them again.

### Utilities

Utilities ship a runtime rather than a skill. `session-tracker` is an MCP server.
Claude users can install it through the marketplace:

```
/plugin install session-tracker@mnox-ai
```

For other MCP-capable hosts, launch `plugins/session-tracker/bin/server.sh` as a
stdio MCP server. It requires [Bun](https://bun.sh) on your `PATH`
(`brew install oven-sh/bun/bun`). Dependencies install automatically on first
launch. See
[`plugins/session-tracker/README.md`](plugins/session-tracker/README.md) for
tools, configuration, and the opt-in semantic-search setup.

## Layout

```
mnox-ai/
├── AGENTS.md                     # provider-neutral repo instructions
├── docs/provider-agnostic.md     # portability and adapter guidance
├── scripts/export_skills.py      # copies/symlinks skills into host directories
├── .claude-plugin/
│   └── marketplace.json          # Claude Code adapter catalog
└── plugins/
    ├── aio/
    │   ├── .claude-plugin/plugin.json   # Claude adapter manifest
    │   └── skills/aio/SKILL.md
    ├── curriculum/                # skills/curriculum/{SKILL.md, scripts/, references/, assets/}
    ├── strangler-fig/             # skills/strangler-fig/{SKILL.md, scripts/, references/}
    ├── schema-review/             # skills/schema-review/{SKILL.md, references/, templates/}
    ├── compliance-review/         # skills/compliance-review/{SKILL.md, references/}
    ├── util-review/               # skills/util-review/{SKILL.md, references/}
    ├── debut/                     # skills/debut/{SKILL.md, scripts/, references/, templates/, agents/}
    ├── diagnose-queries/          # skills/diagnose-queries/{SKILL.md, references/}
    ├── all-skills/
    │   └── .claude-plugin/plugin.json   # dependencies: every skill above
    └── session-tracker/           # utility: MCP server (src/, bin/, hooks/) — not a skill
        ├── .claude-plugin/plugin.json
        └── src/server.ts
```

Each skill directory under `plugins/<name>/skills/<skill>/` is exportable as a
standard Agent Skill. Each plugin also keeps a `.claude-plugin/plugin.json`
manifest so Claude Code users can install exactly one, the whole set, or any
combination from the marketplace.

## License

MIT
