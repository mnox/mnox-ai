# Contributing

Thanks for your interest in `mnox-ai`. This is a personal, curated set of Claude
Code skills, so the bar for additions is "useful to more than just me, and
self-contained." External contributions are welcome but may be declined if they
don't fit that bar.

## Repo shape

Each skill lives under `skills/<name>/` with a `SKILL.md` at its root. A skill
may also carry:

- `references/` — supporting docs the skill reads on demand
- `scripts/` — Python helpers (stdlib-only where possible)
- `assets/` — templates or seed content

The plugin is cataloged in `.claude-plugin/marketplace.json` and described by
`.claude-plugin/plugin.json`.

## Ground rules

- **Self-contained.** No required external MCP servers, API keys, or hardcoded
  local paths. A skill must work for anyone who installs the plugin.
- **Accurate frontmatter.** A `SKILL.md`'s `name` and `description` must match
  what the skill actually does — the `description` trigger phrases are how the
  agent decides to invoke it.
- **Stdlib-first Python.** Scripts target the system `python3` and avoid a
  `pip install` step wherever possible.
- **Docs over comments.** Skills are read by an agent — be explicit and
  unambiguous in the Markdown.

## Before you open a PR

1. Validate the plugin manifest:
   `claude plugin validate .`
2. Smoke-test any changed Python script:
   `python3 skills/<name>/scripts/<script>.py --help`
3. Bump `version` in **both** `.claude-plugin/plugin.json` and
   `.claude-plugin/marketplace.json` if you changed skill behavior.

Then open a PR with a short note on what the skill does and why it belongs here.
