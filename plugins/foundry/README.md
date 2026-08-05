# foundry

**Status: decommissioned for public use.** The autonomous-fix loop this plugin
originally shipped (V0: a deterministic bash engine that drove a Worker/Integrator
pair through isolated git worktrees) has been retired. Execution now routes
through **Sven's native Unit runtime** — a private, personal automation project
(`sven_unit_workflow`) that lives outside this repository and is not distributed
here. There is no build, install, or setup path in this repo that gets a
marketplace user a working `sven_unit_workflow` binary.

**If you installed this plugin expecting the V0 behavior described in earlier
releases: it no longer exists.** `foundry_tick.sh` is now a stub that prints a
decommission notice and exits non-zero; `repos.example.json`,
`unit-contract.md`, `integrator-prompt.md`, and `worker-prompt.md` are all
inert placeholders pointing at the private runtime. The `/foundry-run` skill
is kept only as a compatibility conductor for old invocations by its
maintainer — see
[`skills/foundry-run/SKILL.md`](skills/foundry-run/SKILL.md) for exactly what
it does now.

## What changed and why

The original design's core safety property was that the guardrails (never
push to a remote, worktree isolation, independent review gate) were
**structural** — enforced by a script shipped in this repo, auditable by
anyone who installed the plugin. That is no longer true. The replacement
engine is closed-source and not part of this marketplace, so the only
remaining guardrails are prompt-level instructions in `SKILL.md` ("never
push, open a PR, merge to a remote..."), which are advisory, not structural.
Do not rely on this plugin for the safety guarantees the earlier version
provided.

## Should you install this plugin?

No, unless you are the maintainer with a local checkout of the private Sven
project. For everyone else this plugin currently has no working
functionality — installing it will not run an autonomous-fix loop against
your repo.

## License

MIT
