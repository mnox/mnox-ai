# Template — global instructions (the ai-setup managed block)

Fill-in notes — do not copy this section into the output:

- Emit only the block between the markers below, markers included, appended to
  the end of the engineer's existing global instruction file (or as the whole
  file if none exists).
- Keep it within about 60 lines. Every line must pass the inclusion test in
  `references/instruction-files.md`.
- **Never invent preferences.** The "Preferences" list holds only what the
  engineer stated during intake or what their existing file already says in
  other words (in which case, leave it out — it is already there).
- If another tool's managed block is present in the file, do not restate what
  it covers; drop the matching lines here.
- Delete any heading whose list ends up empty.

```markdown
<!-- ai-setup:start -->
## Role

- I work primarily as a <role>.
- Default stack for new work: <facet> <major>, <facet> <major>, <facet> <major>.

## Working agreements

- <When to proceed versus ask, phrased from the chosen autonomy posture.>
- <Commit and push etiquette, e.g. commit only when asked; never push without asking.>
- When reporting finished work, lead with the result and say plainly what was not verified.

## Preferences

- <A preference no tool enforces, as the engineer stated it.>

## This setup

- Practice skills for my stack are installed: <skill names>. For <stack> work,
  prefer them over general knowledge — they are pinned to the versions I use.
- Prove changes with the repo's verification loop before calling them done.
- Setup ledger and playbook: `~/.ai-setup/<profile-slug>/`.
<!-- ai-setup:end -->
```
