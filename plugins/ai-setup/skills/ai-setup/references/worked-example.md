# Worked Example — "React frontend engineer"

One run, end to end, to calibrate judgment. **Illustrative, not a recipe**: the
named tools and the practice headlines were plausible when this was written and
must be re-derived at run time by the scouts and practice authors. Copy the
reasoning, not the list.

**Contents**
- [Intake](#intake)
- [Profile and slots](#profile-and-slots)
- [Plan](#plan)
- [What a practice skill came out as](#what-a-practice-skill-came-out-as)
- [Verify and handoff](#verify-and-handoff)

## Intake

Invocation: `/ai-setup react frontend engineer`, run inside a product repo.

`stack.json` (abridged): `react` major 19, `nextjs` major 15, `typescript` 5,
`tailwindcss` 4, `vitest`, `testing-library`, `playwright`, `eslint`,
`prettier`. Package manager `pnpm`. Declared commands: `dev`, `build`, `test`,
`lint`, `typecheck`. Family hint: `frontend`.

`inventory.json` (abridged): Claude Code only. A nine-line global instruction
file. No repo instruction file. One review skill installed. The official
marketplace configured. No MCP servers. Existing permission rules: none.

Questions asked — three, one round:

| Question | Answer |
|---|---|
| Scope | Both |
| Which of these do you use? (design tool, tracker, monitoring, hosting) | Design tool, tracker, hosting |
| Autonomy posture | Balanced |

Not asked, because detection answered them: framework, language, package
manager, test runner, which commands exist, which host.

## Profile and slots

Family `frontend`. Work mix defaulted to features, bugs, review.

| Slot | Priority | Decision | Mechanism |
|---|---|---|---|
| `verification-loop` + `visual-verification` | core | The declared `dev` command plus one browser-automation server, vendor-published | CLI + MCP |
| `repo-facts` | core | New `AGENTS.md`; thin `CLAUDE.md` importing it | Instructions |
| `working-agreements` | core | Role lines in the managed block of the global file | Instructions |
| `practice:react` | core | A framework-vendor skill existed but targeted performance only → author `react-practices`, cite it | Skill |
| `practice:nextjs` | core | Author `nextjs-practices` | Skill |
| `practice:testing` | core | Author `frontend-testing` | Skill |
| `practice:a11y` | core | Author `web-a11y`; accessibility lint rules recommended | Skill + lint |
| `practice:typescript` | core | Little delta on this version beyond the repo's strictness choices → waived; three lines in `AGENTS.md` instead | Waived |
| `practice:styling` | useful | Folded into `react-practices` "Local" (token usage) | — |
| `guards` | core | Format and lint the edited file on edit; typecheck when the agent stops | Hooks |
| `blast-radius` | core | Ask on push, publish, deploy; deny reads of environment files | Permissions |
| `friction` | useful | Allow the five verified scripts, narrowly | Permissions |
| `code-intelligence` | useful | The TypeScript language-server plugin; the binary is a human step | Plugin |
| `review` | useful | Already installed — reuse | — |
| `design-handoff` | useful | The design tool's own server; sign-in is a human step | MCP |
| `e2e` | useful | Already in the repo: one command line in `AGENTS.md`, a section in `frontend-testing` | Instructions |
| `work-tracking` | optional | The tracker's own server, repo scope | MCP |
| `current-docs` | useful | Covered by the practice skills' sources and web lookup | Waived |

## Plan

Presented as one table grouped by layer, then:

**Deliberately left out**

| Candidate | Reason |
|---|---|
| A second browser tool | Same slot as `visual-verification`; one filler per slot |
| A docs-lookup server | `current-docs` is covered; it would add standing tool definitions for no new capability |
| The hosting provider's server | Its CLI is already installed and the agent can run it |
| A "senior React engineer" persona subagent | Duplicates the practice skill and splits context |
| A popular community skill bundle | Tier T3 — unknown publisher. Listed as optional for the engineer to review |
| An error-monitoring server | Not selected in intake |

**Needs you:** sign in to the design tool and tracker servers; install the
TypeScript language-server binary; restart the session for plugins.

**Existing files that gain a managed block:** the global instruction file.

The engineer chose "apply all".

## What a practice skill came out as

`react-practices`, repo scope, about 180 lines plus three reference files.
Section headlines only — every row was sourced from the pinned version's docs
and upgrade guides at run time.

| Section | Headlines |
|---|---|
| Changed | Forwarding refs through a wrapper → `ref` as an ordinary prop. Context consumer and provider boilerplate → the newer read API and the context object as provider. Hand-written memoization → leave it to the compiler *because this repo enables it*. Hand-rolled pending and optimistic form state → the framework's action hooks. Effect workarounds for stale closures → effect events |
| Decisions | Derive during render, versus state, versus an effect. Server or client component. Where data loads. When a `key` should reset state |
| Footguns | Sources of hydration mismatch. Effects that mirror props into state. Index keys on reorderable lists. Context value identity causing tree-wide renders |
| Verify | Run the component test; load the route in the browser; read the console for hydration warnings; run the accessibility audit |
| Local | The repo's data-fetching wrapper, state library, and file naming — each with an exemplar path |
| Review checklist | Ten checks mirroring the sections above |

Returned alongside it: four lint recommendations (hook rules, compiler rule,
two accessibility rules) and three trigger probes — "add a controlled input to
the settings form" (loads), "review this component diff" (loads), "write a
Playwright test for login" (does not; `frontend-testing` does).

What it left out, by the tutorial test: what JSX is, how `useState` works,
component basics, formatting.

## Verify and handoff

- `verify_setup.py`: all `pass`, one `warn` (the root `AGENTS.md` was 162 lines
  against a budget of 150 → two conventions moved into a scoped rule).
- Command proof: `pnpm run typecheck` failed on a pre-existing error — surfaced
  to the engineer and kept, since the command itself was correct.
- Loop demonstrated: dev server started, home route loaded, screenshot and a
  clean console captured.
- Fresh-context verifier: picked the right skill for five of five role tasks;
  flagged that `AGENTS.md` and `nextjs-practices` named different directories
  for route handlers → fixed in the skill, the repo file being authoritative.
- Slot audit: sixteen filled, two waived with reasons, two `pending` on sign-in.

The playbook opened with the three needs-you steps, then "how to work here":
start a feature, fix a bug with the browser loop, run a pre-PR review, and
re-run `/ai-setup` after a major upgrade.
