# mnox-ai

Matt Noxon's curated Claude Code skills, distributed as a Claude Code plugin marketplace. Each skill is its own independently installable plugin.

## What's inside

| Plugin | Trigger | Description |
|---|---|---|
| `aio` | `/aio:aio` | Agentic Implementation Optimizer — audit, build, or extend agentic AI implementations. |
| `curriculum` | `/curriculum:curriculum` | Generate a structured, adaptive learning curriculum for any topic. |

## Installation

In Claude Code, add the marketplace once:

```
/plugin marketplace add mnoxon/mnox-ai
```

Then install whichever skills you want, à la carte:

```
/plugin install aio@mnox-ai
/plugin install curriculum@mnox-ai
```

## Layout

```
mnox-ai/
├── .claude-plugin/
│   └── marketplace.json      # catalog: lists all 3 plugins
├── aio/
│   ├── .claude-plugin/plugin.json
│   └── skills/aio/SKILL.md
├── curriculum/
│   ├── .claude-plugin/plugin.json
│   └── skills/curriculum/
│       ├── SKILL.md
│       ├── assets/
│       ├── references/
│       └── scripts/
└── README.md
```

## License

MIT
