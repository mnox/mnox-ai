# mnox-ai

Matt Noxon's curated Claude Code skills and utilities for building, auditing, and
refactoring software and AI systems — distributed as a **marketplace of
independently-installable plugins**. Grab one skill, grab them all, or pull a
standalone utility.

## What's inside

| Plugin | Category | What it does |
|---|---|---|
| `aio` | Agentic AI | Agentic Implementation Optimizer — audit existing agent implementations for reliability/cost/architecture issues, build new ones from scratch, or extend them with new capabilities. |
| `curriculum` | Learning | Generate a structured, adaptive learning curriculum for any topic — modules with a 5-part spine plus an append-only assessment loop that adapts future modules to the learner's answers. |
| `strangler-fig` | Refactoring | Clean-room legacy reimplementation — distill legacy code to functional requirements, rebuild greenfield behind a context firewall, verify behavioral parity, optionally cut over. |
| `schema-review` | Data | Review database schemas and in-code data structures (Ecto, Postgres DDL/migrations, dbt models, Elixir/TypeScript types) for correctness, integrity, performance, scalability, and design quality. |
| `compliance-review` | Compliance | Audit a repo, ADR/PRD, IaC posture, or live cloud state against SOC 2, HIPAA, or PCI-DSS — parallel control-domain agents produce findings with control IDs, severity, evidence, and remediation. |
| `util-review` | Tooling | Review Claude Code skills, hooks, CLAUDE.md files, and other workflow configs for design flaws, unclosed loops, stale references, side effects, and security/portability risks. |
| `debut` | Open Source | Audit a repo for public-readiness before open-sourcing — secrets/PII in history, licensing, community-health files, code quality, tests/CI, deps — scored SHIP IT / NEEDS POLISH / NOT READY with fix commands. |
| `all-skills` | Bundle | Meta-plugin that installs every skill above at once. |

## Installation

In Claude Code, add the marketplace once:

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

## Layout

```
mnox-ai/
├── .claude-plugin/
│   └── marketplace.json          # catalog: one entry per plugin below
└── plugins/
    ├── aio/
    │   ├── .claude-plugin/plugin.json
    │   └── skills/aio/SKILL.md
    ├── curriculum/                # skills/curriculum/{SKILL.md, scripts/, references/, assets/}
    ├── strangler-fig/             # skills/strangler-fig/{SKILL.md, scripts/, references/}
    ├── schema-review/             # skills/schema-review/{SKILL.md, references/, templates/}
    ├── compliance-review/         # skills/compliance-review/{SKILL.md, references/}
    ├── util-review/               # skills/util-review/{SKILL.md, references/}
    ├── debut/                     # skills/debut/{SKILL.md, scripts/, references/, templates/, agents/}
    └── all-skills/
        └── .claude-plugin/plugin.json   # dependencies: every skill above
```

Each plugin under `plugins/<name>/` is self-describing via its own
`.claude-plugin/plugin.json`, so a user can install exactly one, the whole set,
or any combination.

## License

MIT
