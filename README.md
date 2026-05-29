# mnox-ai

Matt Noxon's curated Claude Code skills, distributed as a single Claude Code plugin.

## What's inside

The `mnox-ai` plugin bundles seven skills:

| Skill | Trigger | Category | What it does |
|---|---|---|---|
| `aio` | `/mnox-ai:aio` | Agentic AI | Agentic Implementation Optimizer — audit existing agent implementations for reliability/cost/architecture issues, build new ones from scratch, or extend them with new capabilities. |
| `curriculum` | `/mnox-ai:curriculum` | Learning | Generate a structured, adaptive learning curriculum for any topic — modules with a 5-part spine plus an append-only assessment loop that adapts future modules to the learner's answers. |
| `strangler-fig` | `/mnox-ai:strangler-fig` | Refactoring | Clean-room legacy reimplementation — distill legacy code to functional requirements, rebuild greenfield behind a context firewall, verify behavioral parity, optionally cut over. |
| `schema-review` | `/mnox-ai:schema-review` | Data | Review database schemas and in-code data structures (Ecto, Postgres DDL/migrations, dbt models, Elixir/TypeScript types) for correctness, integrity, performance, scalability, and design quality. |
| `compliance-review` | `/mnox-ai:compliance-review` | Compliance | Audit a repo, ADR/PRD, IaC posture, or live cloud state against SOC 2, HIPAA, or PCI-DSS — parallel control-domain agents produce findings with control IDs, severity, evidence, and remediation. |
| `util-review` | `/mnox-ai:util-review` | Tooling | Review Claude Code skills, hooks, CLAUDE.md files, and other workflow configs for design flaws, unclosed loops, stale references, side effects, and security/portability risks. |
| `debut` | `/mnox-ai:debut` | Open Source | Audit a repo for public-readiness before open-sourcing — secrets/PII in history, licensing, community-health files, code quality, tests/CI, and deps — scored SHIP IT / NEEDS POLISH / NOT READY with fix commands. |

## Installation

In Claude Code, add the marketplace once:

```
/plugin marketplace add mnox/mnox-ai
```

Then install the plugin:

```
/plugin install mnox-ai@mnox-ai
```

## Layout

```
mnox-ai/
├── .claude-plugin/
│   ├── marketplace.json      # catalog: one plugin, "mnox-ai"
│   └── plugin.json           # the plugin manifest
└── skills/
    ├── aio/
    │   └── SKILL.md
    ├── curriculum/
    │   ├── SKILL.md
    │   ├── assets/
    │   ├── references/
    │   └── scripts/
    ├── strangler-fig/
    │   ├── SKILL.md
    │   ├── references/
    │   └── scripts/
    ├── schema-review/
    │   ├── SKILL.md
    │   ├── references/
    │   └── templates/
    ├── compliance-review/
    │   ├── SKILL.md
    │   └── references/
    ├── util-review/
    │   ├── SKILL.md
    │   └── references/
    └── debut/
        ├── SKILL.md
        ├── agents/
        ├── references/
        ├── scripts/
        └── templates/
```

## License

MIT
