## What & why

<!-- What does this change, and why does it belong in mnox-ai? -->

## Plugin(s) touched

<!-- e.g. aio, debut, session-tracker — or "none / tooling" -->

## Checklist

- [ ] `python3 scripts/export_skills.py --list` passes
- [ ] `claude plugin validate .` passes, if Claude adapter manifests changed
- [ ] `ruff check .` is clean
- [ ] `python -m unittest discover -s tests -t .` passes
- [ ] Bumped `version` in **both** the plugin's `plugins/<name>/.claude-plugin/plugin.json` and its matching entry in `.claude-plugin/marketplace.json` if Claude-distributed behavior changed
- [ ] Updated `CHANGELOG.md`
