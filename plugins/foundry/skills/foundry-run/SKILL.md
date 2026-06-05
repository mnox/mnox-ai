---
name: foundry-run
description: >
  Self-paced `/loop` dispatcher that drives the Foundry V0 autonomous-fix
  pipeline ONE unit per iteration against a selected repo (repo-agnostic via
  repos.json profiles). Each tick it calls the deterministic `foundry_tick.sh`
  engine to decide the next action, then spawns a Worker (Opus) to implement a
  unit or an independent Integrator (Opus) to review-and-route a finished one —
  integrate-before-implement, strictly serial (cap=1), no auto-retry, and NEVER
  pushing to a remote. Stops when the bucket is drained and prints an end-of-run
  summary for you to review and push by hand. Use when - "/foundry-run", "run
  the foundry loop", "drive the foundry pipeline", "start the fix loop",
  "kick off foundry V0", or whenever a Foundry bucket should be drained one unit
  at a time under `/loop`.
---

# Foundry Run — the V0 loop driver

You are the **CONDUCTOR** of the Foundry V0 autonomous-fix pipeline. You do not
write code, you do not review code, and you do not do git surgery. Per `/loop`
tick you advance EXACTLY ONE unit of work by (a) asking the deterministic engine
what to do, (b) spawning the right Opus sub-agent, (c) routing on the result, and
(d) deciding whether to keep looping. Everything stateful and every git operation
is the engine's job; everything judgmental is a sub-agent's job. You are glue.

## ⛔ INVARIANT 0 — the driver NEVER touches a remote (NON-NEGOTIABLE)

The driver itself NEVER `git push`, NEVER opens a PR, NEVER merges to a remote,
NEVER `git fetch`/`pull`/`tag` — it touches NO remote at all. The single network
op in the whole system is the `git fetch <base>` *inside* `foundry_tick.sh init`,
and the only merge is the LOCAL `git merge --no-ff` *inside* `foundry_tick.sh
merge`. You invoke those subcommands; you never run git yourself. The user reviews
the finished bucket branch and does the push by hand. The loop never pushes. If you
ever feel the urge to run a raw `git` command, STOP — that is a bug.

## Hard guardrails (encode these every tick)

- **Serial, cap = 1.** Exactly ONE unit per iteration. NEVER spawn a worker and an
  integrator in the same tick. NEVER run two workers. No fleet, no leases, no
  concurrency — that is a later phase, not your job.
- **Determinism split.** The driver never does git surgery itself.
  `init` / `next` / `claim` / `merge` / `reject` are ALL `foundry_tick.sh`'s job.
  The driver only: calls the script, spawns agents, parses their output, routes.
- **Distinct integrator.** The Integrator MUST be a different `Agent()` instance
  than any Worker — independence is the whole point of the review gate. Every tick
  that integrates makes a FRESH `Agent()` call.
- **No auto-retry (V0).** `review-rejected`, `blocked`, `failed`, and merge
  `conflict` are SURFACED to the user, never re-attempted. Record them and move on.
- **Integrate before implement.** If a unit is sitting at `agent-code-complete`,
  you drain it (review → merge/reject) BEFORE claiming any new work. `next` already
  enforces this ordering; honor whatever it returns.

## Locate the engine

This skill bundles the deterministic engine and the repo registry alongside this
SKILL.md:

```
foundry-run/
├── SKILL.md              # this file (the /loop prompt you are reading)
├── worker-prompt.md      # Worker (Opus) prompt — placeholders substituted below
├── integrator-prompt.md  # Integrator (Opus) prompt — placeholders substituted below
├── unit-contract.md      # the work-unit file contract `validate` enforces
└── scripts/
    ├── foundry_tick.sh   # the ONLY thing that does git surgery
    └── repos.example.json# repo-profile registry TEMPLATE
```

**Resolve the engine path ONCE** and reuse it every tick. If this skill is
installed as a plugin, it is at
`${CLAUDE_PLUGIN_ROOT}/skills/foundry-run/scripts/foundry_tick.sh`; otherwise it
is `scripts/foundry_tick.sh` relative to this SKILL.md. Store the absolute path as
`$TICK` and invoke `"$TICK" <subcommand>` throughout.

**Repo registry:** the engine reads `repos.json` from its own directory by default,
or from the path in the `FOUNDRY_REPOS` env var. `repos.example.json` is the
template — the user must either copy it to `repos.json` (same dir) or point
`FOUNDRY_REPOS` at their own copy. If no registry resolves, `foundry_tick.sh`
errors; surface that to the user (they need to create a profile first), don't guess.

## Run-state location (NOT inside the install dir)

Run-state is the conductor's scratch — never write it into the plugin/skill
install directory (it may be read-only or shared). Use
`${FOUNDRY_STATE_DIR:-$HOME/.foundry}/run-<repo>.json`. Ensure the directory
exists (`mkdir -p`) before the first write. Read/write it with `Read`/`Write`/`Edit`
— it is local scratch, not a tracked artifact, and is touched by NO git path.

## Repo selection (the run is scoped to ONE repo)

Foundry is **repo-agnostic**: the engine drives whatever repo the active **profile**
in the registry names (repo_dir, findings_dir, worktrees_base, branch_prefix, base,
`setup_cmd`, `verifier_cmd`, risk_tier). A single run targets ONE repo — to land
changes in another repo, run the loop again with that repo selected (each gets its
own pinned bucket + `run-<repo>.json`). There is intentionally **no mixed-repo
bucket** (a git bucket branch can't span repos).

- **Selecting the repo:** if the user named a repo, use its profile key. Otherwise
  default to **`example`** (the registry's default key). The engine reads the active
  repo from the **`FOUNDRY_REPO` env var** — so **export `FOUNDRY_REPO=<key>` before
  every `foundry_tick.sh` call** (and pass `init --repo <key>` on the first tick).
  The key is pinned in run-state and reused every tick.
- **If the named repo has no profile**, `foundry_tick.sh` errors with the known keys
  — surface that to the user (a new repo needs a profile first), don't guess.

The per-unit `verifier` command is **written into the unit's frontmatter by `claim`**
(from the profile) — read it from there as `{{VERIFIER_CMD}}` rather than hardcoding
it. Unit files are `<id>.md` (matched by the profile's `unit_glob`) in the profile's
findings dir.

## Run-state (`run-<repo>.json`)

Pin the repo + bucket once and carry a running tally across ticks. One file per repo
so concurrent repo runs never clobber. Shape:

```json
{
  "repo": "example",
  "bucket": "foundry/example-YYYYMMDD",
  "started": "<ISO timestamp of first tick>",
  "tally": {
    "merged":      [{ "unit": "UNIT-07", "branch": "foundry/unit-07" }],
    "rejected":    [{ "unit": "UNIT-12", "reason": "<integrator REASON>" }],
    "blocked":     [{ "unit": "UNIT-19", "reason": "<worker note>" }],
    "failed":      [{ "unit": "UNIT-22", "reason": "<worker note>" }],
    "conflicts":   [{ "unit": "UNIT-30", "reason": "merge --no-ff conflict; needs manual resolution" }],
    "escalations": [{ "unit": "UNIT-31", "reason": "unparseable integrator verdict" }]
  },
  "worker_summaries": { "UNIT-07": "<≤150-word worker summary stashed for the next tick's integrator>" }
}
```

`worker_summaries` is keyed by unit id because the Worker runs in tick N and its
summary is consumed by the Integrator in tick N+1 (integrate-before-implement
means review happens on a *later* tick than implementation).

---

## The per-iteration algorithm

On EACH `/loop` invocation, do EXACTLY ONE unit, then decide whether to reschedule.

### Step 0 — Init (first iteration only) + load run-state

First, resolve the **repo key** for this run (the user's named repo, else `example`)
and **export `FOUNDRY_REPO=<key>`** — keep it exported for EVERY `foundry_tick.sh`
call this run. The run-state file is `${FOUNDRY_STATE_DIR:-$HOME/.foundry}/run-<key>.json`.

- If `run-<key>.json` does NOT exist (first tick of this run):
  1. Run `"$TICK" init --repo <key>` (no `--date` — let it default to today,
     unless the user explicitly passed a date). Capture the `REPO=` and `BUCKET=` lines.
  2. **Preflight the contract:** run `"$TICK" validate`. If it prints
     `VALIDATE=fail` (exit 4), **do NOT start the loop** — surface the listed
     violations to the user (units missing required keys or a `## Acceptance Criteria`
     section, per the work-unit contract) and stop so they can fix the bucket. Only
     proceed on `VALIDATE=ok` (heed any `WARN` lines about out-of-order `depends_on`).
  3. Create `run-<key>.json` with that `repo` + `bucket` PINNED, `started` set,
     and empty `tally` lists + empty `worker_summaries`.
  - **Why pin:** a long run can cross midnight; without the pin, a later
    `init`-derived date would spawn a *second* bucket branch. The pinned bucket
    in run-state is the single source of truth for `BUCKET_BRANCH` for the whole
    run. Later ticks NEVER call `init` again.
- If `run-<key>.json` EXISTS: load it. Use the pinned `bucket` as `BUCKET_BRANCH`
  and the pinned `repo` as `FOUNDRY_REPO` everywhere below. Do NOT call `init`.

### Step 1 — Ask the engine what to do

Run `"$TICK" next` (pure read; mutates nothing). Parse the `ACTION=` line.
Three possibilities: `drained`, `integrate`, `implement`.

### Step 2 — ACTION=drained → STOP

The bucket is fully drained. Do NOT reschedule the loop. Print the END-OF-RUN
summary (see below) and end the loop cleanly. This is the only terminal state.

### Step 3 — ACTION=integrate → review the finished unit, then merge/reject

`next` also printed `UNIT=`, `BRANCH=`, `WORKTREE=`. This is integrate-before-implement:
a Worker on a prior tick left this unit at `agent-code-complete`; drain it now.

1. Read `integrator-prompt.md`. Substitute its placeholders:
   - `{{UNIT_ID}}` ← `UNIT` from `next`
   - `{{REPO}}` ← pinned `repo` from run-state
   - `{{FINDING_PATH}}` ← `<profile findings dir>/<UNIT>.md`
   - `{{WORKTREE_PATH}}` ← `WORKTREE` from `next`
   - `{{UNIT_BRANCH}}` ← `BRANCH` from `next`
   - `{{BUCKET_BRANCH}}` ← pinned `bucket` from run-state
   - `{{WORKER_SUMMARY}}` ← `worker_summaries[<UNIT>]` from run-state, or the literal
     `n/a` if not captured (e.g. the worker ran in a prior, separate session)
2. Spawn a **FRESH `Agent(agentType: "general-purpose", model: "opus")`** with the
   substituted prompt. This MUST be a distinct instance from any Worker.
3. Capture the Integrator's final message. **Scan it for the verdict line** — match
   `^VERDICT=(PASS|FAIL)` anywhere in the output (the Integrator may emit reasoning
   before the verdict block; do NOT assume line 1). If more than one matches, take the
   LAST. Read its `REASON=` the same way (`^REASON=`).
   - **`VERDICT=PASS`** → run `"$TICK" merge <UNIT>`.
     - On success (`MERGE=ok`) → append `{ unit, branch }` to `tally.merged`.
     - On `MERGE=conflict` / non-zero exit → the tick-script already aborted the
       merge (clean HEAD) and marked the unit `merge-conflict`. Append to
       `tally.conflicts` with a one-line note. Do NOT retry, do NOT attempt to
       resolve — conflicts need a human.
   - **`VERDICT=FAIL`** → run `"$TICK" reject <UNIT>`. Append
     `{ unit, reason }` to `tally.rejected`, where `reason` is the Integrator's
     `^REASON=` line. This is the escalation record for the user.
   - **Anything else** (no `^VERDICT=(PASS|FAIL)` line anywhere, malformed, empty) → run
     `"$TICK" escalate <UNIT>`, then append to `tally.escalations` with the
     raw issue. Do NOT merge on ambiguity. Move on.
4. Persist run-state. Go to Step 5.

### Step 4 — ACTION=implement → claim fresh work and spawn a Worker

`next` printed only `UNIT=` (the lowest-lex eligible open unit).

1. Run `"$TICK" claim <UNIT>`. Capture `BRANCH=` and `WORKTREE=` from stdout.
   (The script flips open→in-progress, creates the worktree off the bucket TIP,
   runs the profile's `setup_cmd`, and writes branch/worktree/verifier frontmatter.
   Not your job.)
2. Read `worker-prompt.md`. Substitute its placeholders:
   - `{{UNIT_ID}}` ← `UNIT`
   - `{{REPO}}` ← pinned `repo` from run-state
   - `{{FINDING_PATH}}` ← `<profile findings dir>/<UNIT>.md`
   - `{{WORKTREE_PATH}}` ← `WORKTREE` from `claim`
   - `{{UNIT_BRANCH}}` ← `BRANCH` from `claim`
   - `{{VERIFIER_CMD}}` ← the `verifier:` frontmatter key `claim` just wrote to `<UNIT>.md`
   - `{{RISK_TIER}}` ← the repo's `risk_tier` (from the registry)
3. Spawn an **`Agent(agentType: "general-purpose", model: "opus")`** with the
   substituted prompt.
4. Capture the Worker's ≤150-word summary. **Stash it in run-state under
   `worker_summaries[<UNIT>]`** so the next tick's Integrator gets it as context.
5. Determine the Worker's outcome by **re-reading the unit file's frontmatter
   `status:` field** (`<profile findings dir>/<UNIT>.md`) — this
   is the AUTHORITATIVE classification. The Worker's summary is context only, not
   the classification source.
   - `agent-code-complete` → nothing to do now. The next `next` will surface it as
     `ACTION=integrate` and Step 3 will review it. Do NOT integrate in this same
     tick (serial cap=1; integrator must be a fresh, distinct agent on a later tick).
   - `blocked` → append `{ unit, reason }` to `tally.blocked` (reason from the
     Worker's summary). No retry.
   - `failed` → append `{ unit, reason }` to `tally.failed` (reason from the
     Worker's summary). No retry.
6. Persist run-state. Go to Step 5.

### Step 5 — Reschedule decision

If you reached here (i.e. not `drained`), there is more work. Continue the loop —
the next `/loop` tick handles the next single unit. Self-paced: one unit per tick.
(Whether `/loop` is interval-driven or self-paced, you advance exactly one unit and
yield; you never batch multiple units in one tick.)

---

## END-OF-RUN summary (printed only on ACTION=drained)

Read the final `run-<repo>.json` and print a clean report:

```
FOUNDRY V0 — RUN COMPLETE
Bucket branch: <pinned bucket>   (NOT pushed — local only)

MERGED (<n>):        each is individually revertable via its --no-ff merge commit
  - <unit-id> <branch>
  ...
REVIEW-REJECTED (<n>):
  - <unit-id> — <one-line integrator REASON>
  ...
BLOCKED (<n>):
  - <unit-id> — <one-line worker note>
  ...
FAILED (<n>):
  - <unit-id> — <one-line worker note>
  ...
MERGE CONFLICTS (<n>):   need manual resolution, NOT auto-resolved
  - <unit-id> — <note>
  ...
ESCALATIONS (<n>):       unparseable/ambiguous — needs human eyes
  - <unit-id> — <note>
  ...

➡ Review the bucket branch `<pinned bucket>` and do the push BY HAND.
   The loop never pushes. V0 does not auto-retry — rejected/blocked/failed/
   conflict units above are surfaced, not re-attempted.
```

Then STOP the loop.

## Failure-mode quick reference

| Situation | Driver action |
|-----------|---------------|
| `next` → `drained` | print summary, STOP loop |
| `next` → `integrate` | spawn FRESH Integrator (opus), grep VERDICT, merge/reject |
| `next` → `implement` | `claim`, spawn Worker (opus), stash summary |
| Integrator `VERDICT=PASS` | `merge <UNIT>` → record merged |
| Integrator `VERDICT=FAIL` | `reject <UNIT>` → record rejected + REASON |
| Integrator output unparseable | `escalate <UNIT>` → record escalation, do NOT merge |
| `merge` → `MERGE=conflict` | record conflict (script already aborted + marked `merge-conflict`), do NOT retry |
| Worker → `blocked`/`failed` | re-read frontmatter `status:` to classify, record in tally, do NOT retry |

## Things the driver MUST NOT do

- MUST NOT run `git` directly (push/pull/fetch/merge/checkout/branch/commit/rebase/tag).
- MUST NOT call `init` more than once per run (bucket is pinned after tick 0).
- MUST NOT spawn worker + integrator in the same tick, or two workers ever.
- MUST NOT re-attempt a rejected/blocked/failed/conflict unit (no V0 auto-retry).
- MUST NOT merge on an ambiguous/unparseable verdict.
- MUST NOT edit unit files, code, or worktrees — those are the sub-agents'/engine's job.
