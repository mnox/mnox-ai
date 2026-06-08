# AGENTS.md

## Provider-Agnostic Project

`mnox-ai` is a provider-agnostic collection of Agent Skills and local utilities.
The canonical skill content lives in `plugins/<name>/skills/<skill>/SKILL.md`
with optional `references/`, `scripts/`, `templates/`, `assets/`, and `agents/`
directories beside it.

Claude Code marketplace files under `.claude-plugin/` are provider adapters, not
the source of truth. Keep them working, but do not make new skills depend on
Claude-only commands, environment variables, hooks, or model names unless the
skill is explicitly about Claude-specific tooling.

## Setup Commands

- Run unit tests: `python3 -m unittest discover -s tests -t .`
- Run lint: `ruff check .`
- Validate portable skill export: `python3 scripts/export_skills.py --list`
- Typecheck `session-tracker`: from `plugins/session-tracker`, run `bun install`
  if needed, then `bun run typecheck`

## Portability Rules

- Prefer `python3` and standard-library helper scripts for skill workflows.
- Resolve bundled files relative to the active `SKILL.md` directory. Avoid
  host-specific variables such as `${CLAUDE_PLUGIN_ROOT}` in portable skill
  instructions.
- Describe user clarification, delegated agents, and lifecycle hooks in
  host-neutral terms. If a provider-specific mechanism is helpful, put it in a
  provider adapter or clearly label it as an example.
- MCP utilities should expose stdio or HTTP entrypoints that any MCP-capable
  client can configure.

## Testing Instructions

- Add or update tests for helper scripts and portability invariants when changing
  repo layout, manifests, or install docs.
- The Claude marketplace JSON check is intentionally lightweight in CI; run the
  full Claude validator locally only when touching Claude adapter manifests.
