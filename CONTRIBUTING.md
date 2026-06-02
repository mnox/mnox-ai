# Contributing

Thanks for your interest in `mnox-ai`. This is a personal, curated set of Claude
Code skills, so the bar for additions is "useful to more than just me, and
self-contained." External contributions are welcome but may be declined if they
don't fit that bar.

## Repo shape

This repo is a Claude Code **marketplace** of independently-installable plugins.
Every plugin lives in its own directory under `plugins/<name>/` with a manifest
at `plugins/<name>/.claude-plugin/plugin.json`, and the whole catalog is listed
in `.claude-plugin/marketplace.json` at the repo root.

There are three kinds of entry:

- **Skills** — `plugins/<name>/` containing `skills/<name>/SKILL.md`. A skill may
  also carry `references/` (docs read on demand), `scripts/` (Python helpers,
  stdlib-first), `templates/`, `assets/`, or `agents/`.
- **`all-skills`** — a meta-plugin that installs every skill at once via its
  `dependencies` array. When you add a new skill, add its name here too.
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
- **Accurate frontmatter.** A `SKILL.md`'s `name` and `description` must match
  what the skill actually does — the `description` trigger phrases are how the
  agent decides to invoke it.
- **Stdlib-first Python.** Scripts target the system `python3` and avoid a
  `pip install` step wherever possible.
- **Docs over comments.** Skills are read by an agent — be explicit and
  unambiguous in the Markdown.

## Before you open a PR

1. Validate the marketplace + all plugin manifests:
   `claude plugin validate .`
2. Smoke-test any changed Python script:
   `python3 plugins/<name>/skills/<name>/scripts/<script>.py --help`
3. Run the suite and linter:
   `python3 -m unittest discover -s tests -t .` and `ruff check .`
4. Bump `version` in **both** the plugin's
   `plugins/<name>/.claude-plugin/plugin.json` and its matching entry in
   `.claude-plugin/marketplace.json` — the two must agree (`claude plugin tag`
   enforces it).

Then open a PR with a short note on what the skill does and why it belongs here.
