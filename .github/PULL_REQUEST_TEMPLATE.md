## What & why

<!-- What does this change, and why does it belong in mnox-ai? -->

## Plugin(s) touched

<!-- e.g. aio, debut, session-tracker — or "none / tooling" -->

## Checklist

- [ ] `claude plugin validate .` passes
- [ ] `ruff check .` is clean
- [ ] `python -m unittest discover -s tests -t .` passes
- [ ] Bumped `version` in **both** the plugin's `plugins/<name>/.claude-plugin/plugin.json` and its matching entry in `.claude-plugin/marketplace.json` (if behavior changed)
- [ ] Updated `CHANGELOG.md`
