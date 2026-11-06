# Role Profiles — from a role statement to capability slots

How Phase 1 and Phase 2 turn "I'm a `<role>` in `<stack>`" into the slot table
that drives everything else.

**Contents**
- [Intake](#intake)
- [Profile fields](#profile-fields)
- [Universal slots](#universal-slots)
- [Role families](#role-families)
- [Unlisted roles](#unlisted-roles)

## Intake

### Reading the statement

A role statement carries up to four signals. Extract each; do not ask for what
is already there.

| Signal | Example | Drives |
|---|---|---|
| Role family | "frontend", "platform", "data" | Family slots, verification loop, blast radius |
| Stack facets | "React", "Next", "Postgres" | Practice slots |
| Seniority or scope | "staff", "lead", "on-call" | Weight toward review, architecture, incident slots |
| Domain | "fintech", "healthcare" | Extra blast-radius rules; compliance-adjacent skills |

### Evidence precedence

- **What is installed, and at which version** — the repo's manifests win over
  the statement. Versions always come from `stack.json`, never from the
  statement and never from memory.
- **What the engineer works on** — the statement wins over the repo. A frontend
  engineer in a full-stack monorepo cares about the web package; scope the setup
  to their part and say so.
- **Conflict** (statement says React, manifests say Vue) — ask; it is the first
  question.

### Question bank

Ask at most four, in one round, only where the evidence leaves the answer open.
Listed in priority order. Every question carries a recommended default so the
engineer can accept with a word.

| # | Ask when | Question | Default |
|---|---|---|---|
| 1 | No statement, statement conflicts with evidence, or a monorepo where their part is unclear | Which role and which part of the codebase? Offer the detected candidates | The detected primary family and root package |
| 2 | In a repo and scope not stated | Scope: personal (follows you everywhere), this repo (committed, the team gets it), or both? | Both |
| 3 | The family implies outside systems and none are configured | Which of these do you use? Multi-select, categories relevant to the family only (tracker, design tool, monitoring, CI or hosting, database) | None — skip the slot rather than guess |
| 4 | No permission rules exist in the inventory | Autonomy: cautious, balanced, or hands-off behind a gate? | Balanced |
| 5 | The statement is generic ("backend engineer") | What fills most of your week? Pick two or three: building features, fixing bugs, reviewing, refactoring or migrating, performance, testing, on-call | Features, bugs, review |
| 6 | Repo scope and authoritative docs conflict or are absent | Is there a style guide, ADR folder, or contributing doc to treat as authoritative? | Whatever the surveyor finds |
| 7 | High blast-radius family and no boundaries found | Anything the agent must never do here? | The family's blast-radius list |

When permission rules already exist, do not ask question 4 and do not replace
their posture — add only stack-specific rules, in Phase 5.

### Autonomy postures

| Posture | Runs without asking | Always asks | Never |
|---|---|---|---|
| Cautious | Reads | Every command and edit | Bypass modes |
| Balanced | Reads; verified non-destructive stack commands (test, lint, typecheck, build, format) | Push, deploy, migrate, delete, installs from the network | Bypass modes |
| Hands-off behind a gate | As balanced, plus the host's auto-accept for edits | The role's blast-radius operations | Bypass without a deterministic command gate in front |

## Profile fields

Written to `manifest.json` under `profile`.

| Field | Content |
|---|---|
| `role` | The statement, verbatim |
| `slug` | Kebab-case of the role; names the state directory |
| `family` | One family below, or `custom` |
| `stack` | One entry per facet: `facet`, `name`, `version`, `source` |
| `work_types` | The work mix, most frequent first |
| `systems` | Outside systems in use, by category |
| `hosts` | Hosts being configured; first is primary |
| `scope` | `personal`, `repo`, or `both` |
| `posture` | `cautious`, `balanced`, or `gated` |
| `repo` | Absolute path, or null |
| `part` | Sub-path the engineer owns in a monorepo, or null |

## Universal slots

Every profile gets these. Priority is the default; adjust for scope and work mix.

| Slot id | Need | Priority | Usual mechanism |
|---|---|---|---|
| `verification-loop` | Run the work and observe the result in the role's medium | core | A CLI or dev server plus a way to observe (browser, HTTP client, test runner); MCP only when no CLI exists |
| `repo-facts` | This codebase's commands, layout, conventions, boundaries | core in repo scope | Repo instructions |
| `working-agreements` | How this engineer wants the agent to work | core in personal scope | Global instructions |
| `practice:<facet>` | Current best practices for each core stack facet | core | Practice skill, adopted or authored |
| `guards` | Format, lint, typecheck happen every time | core where the repo has the tools | Hooks, pre-commit, CI |
| `blast-radius` | The role's dangerous operations cannot run unasked | core | Permission ask and deny rules |
| `friction` | Verified safe commands run unprompted | useful | Permission allow rules |
| `code-intelligence` | Definitions, references, and type errors without grepping | useful | Language-server integration |
| `current-docs` | Look up the API of the *installed* version | useful | Docs server or skill; often covered by the practice skill's sources |
| `review` | A review pass before a PR | useful | Existing review skill or plugin |
| `vcs-workflow` | Branch, commit, and PR conventions; the VCS host | useful | Repo instructions plus the host's CLI |
| `work-tracking` | Read and update tickets | optional | Tracker CLI or MCP server |

`practice:<facet>` expands to one slot per core facet. Cap authored practice
skills at about six; merge facets that always trigger together.

## Role families

Each family adds its own slots, names the verification loop, and lists the
operations that go into `blast-radius`. Named technologies are examples of a
facet, not a recommendation.

### Frontend web

- **Verification loop.** Dev server plus a browser the agent can drive: navigate,
  read the DOM, console, and network, take a screenshot. Component tests are
  necessary and not sufficient — a passing test does not show the page renders.
- **Practice facets.** UI framework (and meta-framework), language and type
  system, styling system, component testing, accessibility; web performance when
  it is in the work mix.
- **Family slots.** `visual-verification` (core): browser automation.
  `a11y-check` (useful): automated audit inside the loop. `design-handoff`
  (useful): read frames and tokens from the design tool. `e2e` (useful).
  `component-catalog` (optional): isolated component rendering.
- **Systems.** Design tool, component-library docs, browser error monitoring,
  feature flags, preview deployments.
- **Blast radius.** Production deploys; publishing packages; secrets in
  client-exposed environment files; deleting lockfiles; bulk dependency upgrades.
- **Guards.** Format and lint on edit; typecheck on stop; accessibility lint rules.

### Backend / API

- **Verification loop.** Start the service or a test harness, send a real
  request, read the response and logs; integration tests against real
  dependencies in containers.
- **Practice facets.** Service framework, language, data access and migrations,
  API contract style, testing, observability; concurrency model where it matters.
- **Family slots.** `api-exercise` (core): an HTTP or RPC client the agent can
  script. `schema-migrations` (core with a database): conventions and safety.
  `db-access` (useful): read-only queries against a development database.
  `contract` (useful): the schema as source of truth. `local-deps` (useful).
- **Systems.** Database, queue, cache, error monitoring, log search.
- **Blast radius.** Migrations against shared databases; destructive SQL;
  production credentials; deploys; force-push; reading environment files with
  secrets.
- **Guards.** Format, lint, typecheck; migration linting; secret scanning before
  commit.

### Full-stack

The union of the two above. Pick the primary side from the work mix, keep
practice skills separate per side, and make the verification loop cross the
boundary: a UI action, the request it causes, and the stored result.

### Mobile

- **Verification loop.** Build and run on a simulator or emulator, capture the
  screen and logs; unit and UI tests.
- **Practice facets.** UI framework, language, navigation and state, platform
  guidelines, testing, release and signing conventions.
- **Family slots.** `simulator-control` (core). `device-logs` (useful).
  `store-release` (optional).
- **Blast radius.** Signing keys and provisioning; store submissions; build
  numbers; entitlements.
- **Guards.** Format and lint on edit. Full builds are slow — put them in
  pre-push or CI, not an edit hook.

### Data / analytics engineering

- **Verification loop.** Compile or parse the model, run it on a development
  target with a row limit, inspect results and data tests; read the query plan or
  cost estimate before running anything large.
- **Practice facets.** Transformation framework, the warehouse's SQL dialect,
  orchestration, data testing, modeling conventions.
- **Family slots.** `warehouse-read` (core): read-only, cost-capped development
  access. `cost-guard` (core): dry-run and scan limits. `lineage` (useful).
- **Blast radius.** Writes to production schemas; full refreshes and backfills;
  unbounded scans; exporting personal data; dropping tables.
- **Guards.** SQL lint and format; compile on edit. Enforce the development
  target in the tool's own profile, not in prose.

### ML / AI engineering

- **Verification loop.** A small, fast evaluation or a smoke run on a tiny
  subset, then compare a metric. For LLM applications: run eval cases and read
  the traces.
- **Practice facets.** Training or inference framework, experiment tracking,
  data loading, evaluation method; for LLM applications, the provider SDK and
  its prompt, caching, and tool-use conventions.
- **Family slots.** `eval-harness` (core). `experiment-tracking` (useful).
  `notebook` (optional). `compute-jobs` (optional).
- **Blast radius.** Launching expensive compute; overwriting checkpoints or
  datasets; leaking evaluation data into training; uncapped API spend.
- **Guards.** Format, lint, typecheck; seeds and config recorded with every run.

### Platform / infrastructure / SRE

- **Verification loop.** Format, validate, then **plan, diff, or dry-run** and
  read the output; policy checks. Applying is never the verification step.
- **Practice facets.** Infrastructure-as-code tool, the cloud services in use,
  container orchestration, CI/CD system, observability stack, incident process.
- **Family slots.** `plan-review` (core). `cloud-read` (useful): read-only
  access. `policy-check` (useful). `runbooks` (useful). `incident` (optional).
- **Blast radius.** Apply and destroy; state manipulation; cluster commands
  against production contexts; identity and access changes; secret stores; DNS.
  Deny by default and require explicit human invocation.
- **Guards.** Format and validate on edit; plan in CI; context and profile guards.

### QA / test automation

- **Verification loop.** Run the specific test, read the failure output, traces,
  screenshots; rerun to separate flakes from failures.
- **Practice facets.** Test frameworks, test design (isolation, fixtures,
  selectors), CI integration.
- **Family slots.** `test-run` (core). `trace-view` (useful). `flake-triage`
  (optional).
- **Blast radius.** Tests pointed at shared or production environments;
  data-cleanup scripts.

### Security engineering

- **Verification loop.** Run analysers on a target and read the findings;
  reproduce in an isolated environment.
- **Practice facets.** The languages under review, the threat-modeling method,
  the scanner toolchain, the secure-coding standard in force.
- **Family slots.** `static-analysis` (core). `secrets-scan` (core).
  `dependency-audit` (useful).
- **Blast radius.** Testing systems without authorization; handling real
  credentials; publishing findings.

## Unlisted roles

Set `family: custom` and derive the slots with five questions — answer them from
the statement and the repo before asking the engineer anything:

1. What is the artifact this role produces?
2. In what medium is "it works" observed? → `verification-loop`
3. Which three to five technologies carry most of the decisions? → practice facets
4. Which outside systems does the work touch weekly? → systems slots
5. Which single action would be most expensive to get wrong? → `blast-radius`
