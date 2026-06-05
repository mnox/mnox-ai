# foundry

An **autonomous-fix loop driver** for Claude Code. Foundry drains a *bucket* of
work-unit files one at a time: for each unit it spawns an Opus **Worker** that
implements the fix in an isolated git worktree and drives the repo's verifier to
green, then an independent Opus **Integrator** that reviews the diff and votes
PASS/FAIL. Passing units are merged into a local bucket branch; everything else is
surfaced for you. You review the bucket branch and push by hand.

It is repo-agnostic (driven by a `repos.json` profile per target repo) and ships as
a single `/foundry-run` skill plus a deterministic bash engine.

## ⚠️ Safety model — read this first

Foundry runs autonomous agents that **write code and commit it in a loop**. The
guardrails that make that acceptable are structural, not advisory:

- **Never touches a remote.** The driver and both sub-agents are forbidden from
  `git push`, opening PRs, or merging to a remote. The only network op in the whole
  system is a `git fetch <base>` inside `init`. **You** push the finished bucket
  branch by hand, after reviewing it.
- **Worktree isolation.** Each unit is implemented in its own `git worktree` on its
  own branch — never in your main clone. The Worker may only write inside that
  worktree.
- **Strictly serial, cap = 1.** Exactly one unit advances per loop tick. No fleet,
  no parallel writers.
- **Independent review gate.** The Integrator is a *distinct* agent instance from
  the Worker and is read-only — it judges, it never repairs.
- **No auto-retry (V0).** Rejected / blocked / failed / merge-conflict units are
  recorded and surfaced, never silently re-attempted.
- **`setup_cmd` / `verifier_cmd` run on your machine** via the shell. Only add
  repo profiles you trust, and review those commands before running.

Run it against a repo you can afford to throw the bucket branch away on until you
trust it.

## Install

Add the marketplace and install the `foundry` plugin:

```
/plugin marketplace add mnox/mnox-ai
/plugin install foundry@mnox-ai
```

## Setup

1. **Create a repo profile.** Copy the template and edit it:

   ```bash
   cd <plugin>/skills/foundry-run/scripts
   cp repos.example.json repos.json   # then edit repos.json
   ```

   Or keep your registry anywhere and point `FOUNDRY_REPOS` at it. Each profile
   supplies `repo_dir`, `findings_dir` (where the work-unit files live),
   `worktrees_base`, `branch_prefix`, `base` (a `remote/branch` ref the bucket is
   cut from), `setup_cmd`, `verifier_cmd`, and optional `unit_glob` / `risk_tier`.
   See the comments in `repos.example.json`.

2. **Write some work units.** A bucket is a directory of `<id>.md` files (matched by
   the profile's `unit_glob`, default `UNIT-*.md`). Each unit needs `id` / `title` /
   `status: open` frontmatter and a non-empty `## Acceptance Criteria` section —
   that section is both the Worker's target and the Integrator's rubric. See
   [`unit-contract.md`](skills/foundry-run/unit-contract.md) for the full contract.

3. **Run the loop:**

   ```
   /foundry-run                       # defaults to the `example` profile
   /foundry-run run foundry on <key>  # selects a named profile
   ```

   Foundry self-paces under [`/loop`](https://docs.claude.com/en/docs/claude-code)
   (a built-in Claude Code command that re-runs a prompt on a cadence), advancing
   one unit per tick until the bucket is drained, then prints a run summary.

## How it works

```
/loop tick ─▶ foundry_tick.sh next ─▶ ACTION=?
                                       ├─ implement ─▶ claim ─▶ Worker (Opus, worktree) ─▶ agent-code-complete
                                       ├─ integrate ─▶ Integrator (Opus, read-only) ─▶ PASS→merge / FAIL→reject
                                       └─ drained   ─▶ print summary, STOP
```

- **`foundry_tick.sh`** is the only component that does git surgery (branch, worktree,
  `merge --no-ff`, frontmatter writes). Pure `bash` + `python3` (stdlib) + `git` — no
  other dependencies.
- **The skill (`SKILL.md`)** is the conductor prompt: it asks the engine what to do,
  spawns the right sub-agent, parses its output, and routes. It writes scratch
  run-state to `${FOUNDRY_STATE_DIR:-~/.foundry}/run-<repo>.json`.
- **Worker / Integrator prompts** are the two Opus sub-agent roles.

## V0 scope

V0 is deliberately thin. There is **no** fleet, leases, heartbeats, concurrency
planner, escalation cascade, or remote push. It does one repo at a time, one unit at
a time, and hands the bucket branch to you. That is the point.

## License

MIT
