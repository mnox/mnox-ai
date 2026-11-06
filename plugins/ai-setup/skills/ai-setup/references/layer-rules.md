# Layer Rules — which mechanism fills a slot

Phase 4 uses this to turn "the role needs X" into "X lives *here*". The goal is
the cheapest mechanism that reliably meets the need.

**Contents**
- [The placement test](#the-placement-test)
- [Scope](#scope)
- [Budgets](#budgets)
- [Guards: hooks, lint, CI](#guards-hooks-lint-ci)
- [Subagent definitions](#subagent-definitions)
- [Permissions](#permissions)
- [External access: CLI before MCP](#external-access-cli-before-mcp)

## The placement test

Take the need and ask these in order. The first yes decides.

| # | Question | Mechanism | Standing cost |
|---|---|---|---|
| 1 | Can an existing tool enforce it — formatter, linter, type checker, CI? | Configure the tool. Write nothing for the agent | None |
| 2 | Must it happen every time, with no exceptions? | Hook on the host's lifecycle, pre-commit, or CI | None in context; latency per event |
| 3 | Does it repeat a prompt the engineer keeps approving or must never approve? | Permission rule | None |
| 4 | Is it true for every task in scope and impossible to infer from the code? | A line in an instruction file | Paid every turn |
| 5 | Is it true only under some paths? | Path-scoped rule or a nested instruction file | Paid when those paths are touched |
| 6 | Is it a procedure or body of knowledge needed for some tasks? | Skill | A one-line description until triggered |
| 7 | Does it need a system outside the workspace? | A CLI the agent can already run; otherwise an MCP server | CLI: none. MCP: tool definitions |
| 8 | Does it need isolation — noisy output, different permissions, parallelism, an independent opinion? | Subagent definition | A description until used |
| 9 | Is it an explicit kickoff the engineer types? | User-invoked skill or command | A description |

Reading the table as a rule of thumb: **enforce before you instruct, and
instruct before you install.** Prose is advisory; it competes with everything
else in context and loses more often as context fills. Anything the engineer
would be upset to see skipped belongs in rows 1–3.

Worked through for a few common needs:

| Need | Wrong placement | Right placement | Why |
|---|---|---|---|
| "Code is formatted" | Instruction line | Formatter + edit hook | Row 1 then 2 |
| "Use the repo's package manager" | Skill | Instruction line | Always true, not inferable from one file, one line |
| "Server components by default under `app/`" | Root instruction file | Path-scoped rule | True only under one path |
| "How we write data-fetching code in this framework version" | Instruction file | Practice skill | Needed for some tasks, too long for every turn |
| "Check the deploy preview" | MCP server | The hosting provider's CLI | A CLI exists; no standing cost |
| "Never run migrations against the shared database" | Instruction line | Permission deny rule, plus one instruction line explaining why | Must hold every time |

## Scope

| Scope | Belongs here | Never here |
|---|---|---|
| Global (user) | How this person works in any repo: communication, style preferences no tool enforces, workflow etiquette, environment facts | Facts about one codebase |
| Repo, committed | What is true for every contributor: commands, layout, conventions, boundaries, shared guards | One person's preferences; machine-specific paths; secrets |
| Repo, local (git-ignored) | Personal overrides for this repo: sandbox URLs, a preferred test filter | Anything teammates need |

Three checks before writing to a scope:

1. Would a teammate cloning the repo want this? If no, it is not repo-committed.
2. Would it still be true in a different repo? If no, it is not global.
3. Does it contain a credential, token, or personal path? Then it goes nowhere;
   it becomes a human step.

## Budgets

Defaults, not laws. Exceed one only with a reason recorded in the plan.

| Resource | Default budget | When over |
|---|---|---|
| Root repo instruction file, including what it imports | About 150 lines | Move procedures to skills, path-specific lines to scoped rules, enforceable lines to tools |
| Global instruction file, including imports and managed bundles | About 60 lines of this skill's own additions | Keep only what changes behavior in every repo |
| Authored practice skills per role | 3 to 6 | Merge facets that trigger together; drop facets the model already handles well |
| Practice skill body | About 200 lines; hard ceiling 500 | Push depth into the skill's own `references/` |
| Active MCP servers | About 5, each used at least weekly | Prefer a CLI; scope rarely-used servers to the repos that need them |
| Subagent definitions | 0 to 3 | Fold into a skill unless isolation is the point |
| Edit-time hooks | Finish in a couple of seconds | Move slow checks to stop, pre-commit, or CI |

Count what already exists before adding: `inventory.json` reports
`always_loaded_lines` per scope (imports not followed — add those), installed
skills, enabled plugins, and configured servers. Where the host can report a
plugin's projected context cost, read it before recommending the plugin.

When the setup does not fit, cut optional slots first, then useful ones. Never
cut a core slot to make room for a nice-to-have.

## Guards: hooks, lint, CI

A guard earns its place when the check is fast, deterministic, and its failure
is actionable.

| Trigger | Good for | Avoid |
|---|---|---|
| After an edit | Format the changed file; lint the changed file with autofix | Whole-project typecheck or test runs — every edit pays the cost |
| When the agent finishes a turn | Typecheck; the affected tests | Checks that fail for reasons unrelated to the change — they trap the agent in a loop |
| Before commit | Secret scan; staged-file lint | Anything needing network |
| CI | Full suite, build, slow analysis | — |

Rules for writing one:

- Scope it to the changed file when the tool supports it.
- Make failure output short and specific; the output is fed back to the agent.
- A guard that blocks must describe how to fix the problem, or it produces
  retries rather than repairs.
- Prefer the repo's existing scripts over new commands so local, hook, and CI
  behavior match.
- Hosts without a hook surface fall back to pre-commit and CI
  (`host-matrix.md`).

A practice author returns lint recommendations with each skill. Each one the
engineer accepts becomes a tool configuration here, and the skill then only says
"the linter enforces this — fix the finding, do not suppress it."

## Subagent definitions

Define one only when a slot needs what a skill cannot give:

| Reason | Example |
|---|---|
| Output too noisy for the main thread | A test-failure triager that reads long logs and returns the cause |
| Narrower permissions than the main session | A read-only reviewer |
| An opinion not anchored on the author's reasoning | A fresh-context review before a PR |
| Parallel independent work | Per-package checks in a monorepo |

Give each a single job, a description that says when to delegate to it, and the
minimum tool set. A "senior `<stack>` engineer" persona agent is not a slot — it
duplicates the practice skill and splits context for no gain.

## Permissions

Permissions are security configuration. This skill proposes them, shows the
exact rules and the file they go in, and writes them only on a separate,
explicit confirmation.

**Allow** — only when all hold:

- The command was run successfully during this setup.
- It is non-destructive and local: test, lint, typecheck, build, format, and
  read-only VCS queries.
- The rule is as narrow as the host's syntax permits — the specific script, not
  the whole package manager or shell.

**Ask** — outward-facing or hard to undo: push, publish, deploy, dependency
changes, anything that sends data out.

**Deny** — the role's blast radius (`role-profiles.md`) and reads of secret
material: environment files, key directories, credential stores.

Never propose a bypass or "accept everything" mode, and never widen an existing
deny rule. If the inventory shows the engineer already has a deliberate
permission setup, add only the stack-specific rules and leave their posture
alone. Where a dedicated permission skill is installed, its posture is the
baseline and its rule about who performs the write applies.

## External access: CLI before MCP

| Situation | Choose |
|---|---|
| A maintained CLI exists and the agent can run it | The CLI, plus one instruction line naming it |
| No CLI, or the system needs structured, authenticated, multi-step access | MCP server |
| The server offers a remote endpoint with a browser sign-in | That, over a local server holding a long-lived token |
| The capability is needed in one repo | Repo-scoped configuration |
| The capability is needed everywhere | User-scoped configuration |

Credentials are always a human step. Configuration that must be committed
refers to an environment variable by name and never contains the value.
