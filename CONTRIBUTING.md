# Contributing

Thanks for your interest in `mnox-ai`. This is a personal, curated set of
provider-agnostic Agent Skills and local AI-agent utilities, so the bar for
additions is "useful to more than just me, portable across hosts where practical,
and self-contained." External contributions are welcome but may be declined if
they don't fit that bar.

## Repo shape

This repo's portable core is a collection of standard Agent Skills plus utility
MCP servers. Claude Code marketplace files are maintained as a provider adapter.
Every package lives under `plugins/<name>/`; portable skill content lives at
`plugins/<name>/skills/<skill>/SKILL.md`, and the Claude adapter manifest lives
at `plugins/<name>/.claude-plugin/plugin.json`.

There are three kinds of entry:

- **Skills** — `plugins/<name>/` containing `skills/<skill>/SKILL.md`. A skill may
  also carry `references/` (docs read on demand), `scripts/` (Python helpers,
  stdlib-first), `templates/`, `assets/`, or `agents/`.
- **Provider adapters** — `.claude-plugin/` files keep Claude marketplace install
  support. When you add a new skill, update the Claude catalog and `all-skills`
  dependency list if it should be installable there.
- **Utils** — heavier components (e.g. an MCP server) that ship their own runtime
  and dependencies. Utils are a deliberately separate class from skills: they are
  exempt from the stdlib-only / no-MCP rules below, but must document their runtime
  requirements and degrade gracefully when optional ones (API keys, embedding
  services) are absent.

## Ground rules

- **Self-contained (skills).** A skill requires no external MCP servers, API
  keys, or hardcoded local paths — it must work for anyone who installs it.
  (Utils may carry runtime dependencies; see *Repo shape*. Neither class may
  hardcode local paths or commit secrets.)
- **Provider-neutral first.** Portable skill prose should avoid provider-only
  commands, environment variables, model names, and lifecycle hooks. Put
  provider-specific wiring in an adapter or mark it clearly as an example.
- **Accurate frontmatter.** A `SKILL.md`'s `name` and `description` must match
  what the skill actually does — the `description` trigger phrases are how the
  agent decides to invoke it.
- **Stdlib-first Python.** Scripts target the system `python3` and avoid a
  `pip install` step wherever possible.
- **Docs over comments.** Skills are read by an agent — be explicit and
  unambiguous in the Markdown.

## Before you open a PR

1. Validate portable skill export:
   `python3 scripts/export_skills.py --list`
2. Validate the Claude marketplace + all plugin manifests when the adapter changed:
   `claude plugin validate .`
3. Smoke-test any changed Python script:
   `python3 plugins/<name>/skills/<name>/scripts/<script>.py --help`
4. Run the suite and linter:
   `python3 -m unittest discover -s tests -t .` and `ruff check .`
5. Bump `version` in **both** the plugin's
   `plugins/<name>/.claude-plugin/plugin.json` and its matching entry in
   `.claude-plugin/marketplace.json` — the two must agree (`claude plugin tag`
   enforces it).

Then open a PR with a short note on what the skill does and why it belongs here.
