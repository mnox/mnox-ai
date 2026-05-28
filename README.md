# mnox-ai

Matt Noxon's curated Claude Code skills, distributed as a single Claude Code plugin.

## What's inside

The `mnox-ai` plugin bundles three skills:

| Skill | Trigger | Category | Status | What it does |
|---|---|---|---|---|
| `aio` | `/mnox-ai:aio` | Agentic AI | Stable | Agentic Implementation Optimizer — audit existing agent implementations for reliability/cost/architecture issues, build new ones from scratch, or extend them with new capabilities. |
| `curriculum` | `/mnox-ai:curriculum` | Learning | Stable | Generate a structured, adaptive learning curriculum for any topic — modules with a 5-part spine plus an append-only assessment loop that adapts future modules to the learner's answers. |
| `strangler-fig` | `/mnox-ai:strangler-fig` | Refactoring | Stable | Clean-room legacy reimplementation — distill legacy code to functional requirements, rebuild greenfield behind a context firewall, verify behavioral parity, optionally cut over. |

All three skills are self-contained: no external MCP servers, API keys, or local-path assumptions required.

## Installation

In Claude Code, add the marketplace once:

```
/plugin marketplace add mnox/mnox-ai
```

Then install the plugin:

```
/plugin install mnox-ai@mnox-ai
```

All three skills install together.

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
    └── strangler-fig/
        ├── SKILL.md
        ├── references/
        └── scripts/
```

## License

MIT
