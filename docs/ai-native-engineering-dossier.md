# The AI-Native Engineering Dossier

A short curriculum for strong engineers who already use AI tools but haven't yet
crossed into *AI-native* engineering — designing the context, harness, and
verification systems that let models do real work, increasingly autonomously.

**The one-sentence goal:** by the end, you should be able to look at any agentic
system and say *where the intelligence should live, what the model must never be
trusted to decide, and what has to be built around it* — and then build that.

**How to use it:** eight modules plus a capstone. Each has the core ideas, an
exercise, and — where a public repo demonstrates the pattern — a *field trip*
into a real working system. Field trips reference two public repos:

- **[mnox/mnox-ai](https://github.com/mnox/mnox-ai)** — a portable,
  provider-agnostic library of agent skills, including the AIO
  ("Agentic Implementation Optimizer") skill this curriculum leans on heavily.
- **[mnox/codex](https://github.com/mnox/codex)** — a personal fork of
  OpenAI's Codex CLI ("Dinglehopper") that customizes the harness itself.

Everything else here is distilled from private production systems and is
included **inline** — templates, checklists, and contracts you can lift
directly into your own tooling. Do the exercises; reading alone won't rewire
the instincts. Pace: roughly two modules a week.

Where a claim has research behind it, the evidence trail lives in
`mnox-ai: plugins/aio/skills/aio/references/knowledge-base.md` (cited below as
**KB**), which keeps rules and evidence in separate layers on purpose — you'll
see why in Module 4.

---

## Module 1 — The Reframe: The Harness Is the Product

The single mindset shift that separates "engineer who uses AI" from AI-native
engineer:

- **The model is not the system.** Roughly 98% of a production coding agent's
  lines of code are harness and infrastructure, not model interaction (KB:
  harness-design). The prompt is a config file; the product is the scaffold
  around it: tool contracts, context assembly, permissions, telemetry,
  verification, recovery.
- **The harness, not the weights, is your optimization surface.** You can't
  retrain the model. You *can* redesign what it sees, what it's allowed to do,
  what happens when it's wrong, and how you find out. That's where all your
  leverage is.
- **Capability ≠ reliability.** Models keep getting more capable; reliability
  lags capability, and scaling alone never closes the gap (KB:
  reliability-lags-capability). The gap is closed by engineering. That gap is
  your job description.
- **Own your harness.** Treat your agent tooling the way you'd treat any
  critical dependency: understand it, instrument it, and be willing to fork it.
  Compaction, dispatch, and telemetry are runtime concerns, not prompt hacks.

**Field trip:** `mnox/codex: DINGLEHOPPER.md` — the fork replaces
transcript-summarization compaction with a typed "context compiler," adds
bounded sub-agent dispatch behind blessed worker profiles, and measures its
own ROI against stock baselines. Note especially
`dingle/evals/dispatch-runs/2026-07-09-value-assessment-notes.md`: an honest
self-audit that recommends *time-boxing the fork rather than expanding it*.
Measuring your own tooling honestly is part of the discipline.

**Exercise:** take an agent workflow you already use (Claude Code, Cursor,
Codex, anything). List every component that is *not* the model: context
sources, tool definitions, permission gates, retry logic, output validation.
That list is the harness. Rank each item by how much you actually control it
today.

---

## Module 2 — Models: What They're Actually Bad At (and Why It's Your Problem)

You cannot design around a model's weaknesses if you've internalized the wrong
theory of why it fails.

- **Most production "hallucination" is a resourcing failure, not a model
  defect.** An agent forced to act without the resources to act correctly —
  and with no sanctioned way to decline — *will* act, wrongly. If the only
  available action is "answer," the agent will answer (KB: abstention).
- **Abstention is an architectural primitive.** Every high-stakes decision
  point needs a safe default: escalate, return a typed
  insufficient-context result, fall back to a deterministic path, or no-op.
  Design the exit before you design the happy path. Prefer *hedged
  specificity* (a narrower claim at stated confidence) over binary refusal.
- **Calibration doesn't transfer.** Confidence thresholds tuned on one model,
  one prompt, or one UI do not survive the move to another. Re-calibrate on
  the target system (KB: abstention).
- **Diagnosis and recovery are different skills, and recovery is much
  harder.** Agents can identify what went wrong ~65% of the time but recover
  successfully only ~22% of the time (KB: diagnosis-recovery-gap). Never
  accept "it noticed the error" as evidence of a working recovery loop.
- **Agents fail by drifting, not by hitting a wall.** Collapse comes from
  compounding slightly-off-path tool calls across a trajectory, not from one
  hard step (KB: failure-attribution). This is why long-horizon reliability —
  not pass@1 — is the metric that matters (KB: reliability-decay).
- **Never trust a model's self-assessment as a gate.** Models game verifiers
  while disavowing it. Anything that grants autonomy, merges code, or spends
  money must be gated by a check the model cannot edit (Module 7).

**Field trip:** `mnox/mnox-ai: plugins/aio/skills/aio/SKILL.md` (the
escape-hatch section near the top) — the resourcing thesis stated as
operational rules, including the requirement that every abstention emit a
structured, queryable event: *"a hatch with no durable sink is theater."*
Aggregate hatch trips by decision point, rank by frequency × cost, and you
have your roadmap for free.

**Exercise:** find a place in any workflow where a model is asked a question
it sometimes can't answer correctly. Enumerate what it would *need* to answer
correctly (data, tool, permission, definition). Then add one escape hatch:
a typed "insufficient context" output plus a log line. You've just built your
first gap-signal loop.

---

## Module 3 — Context Engineering

Context is not a bucket you fill. It's a budget you spend, and overspending
makes the model *worse*.

- **More context is not more capability.** The same added context can produce
  up to 20× gains or 46% degradation depending on the task; whether the model
  could already do the task without the context predicts which way it goes
  (KB: progressive-disclosure). When in doubt, run a cheap context-free trial
  first to learn the sign.
- **Just-in-time beats accumulate-everything** — dramatically. Agents that
  fetch context at the moment of need complete more work with a third of the
  tokens (KB: context-eng).
- **The main thread is a coordination layer, not a research layer.** Grepping,
  tracing, and file-dump reading belong in sub-agents that return distilled
  conclusions. A task that will read twenty files is a delegation, not an
  inline action.
- **Budget with a hard stop and a defined exit.** Set a numeric context
  ceiling; at the ceiling, stop and write a structured handoff — including
  open questions *parked inside the handoff with recommendations*, rather than
  interrupting a human. "A task finished in an exhausted context is finished
  badly."
- **Engineer what agents read before they act.** A repo can be built so a
  fresh, memoryless session picks up mid-program work correctly: decided
  structure ("canon") kept separate from undesigned ideas and from accepted
  work programs, each with explicit status markers so an agent can tell
  settled from live.
- **Handoffs should carry negative space.** The most valuable sections of a
  cross-session handoff are "known friction — do not re-diagnose" and
  "decisions made — do not re-propose." Without them, every fresh session
  re-derives the same dead ends at full price.

**Portable template — the session handoff.** This shape is battle-tested in
private production systems; steal it verbatim:

```markdown
# HANDOFF — <task> — <date>

## TL;DR
One paragraph. Tag each load-bearing statement:
[CONSTRAINT] [SETTLED] [OBSERVED] [HYPOTHESIS]

## Done
Completed work with commit SHAs and test counts. Verifiable, not vibes.

## Files to read, in order
| Path (absolute) | Why |

## Decisions made — do NOT re-propose
Each with a one-line rationale.

## Known friction — do NOT re-diagnose
Dead ends already hit; expected-but-alarming behaviors ("X skips when
$VAR unset — expected, not a regression").

## Live issues
Each with copy-paste recovery commands.

## Next steps, in order
## Out of scope / follow-ups
## Open questions — parked, each with ONE recommendation + confidence
## Progress ledger (append-only)
[PROGRESS] [DECISION] [CORRECTION] [FINDING] entries as work proceeds.
```

**Exercise:** write a handoff for something you're mid-way through using the
template, as if the reader is a competent stranger with zero access to your
head. Then give it to an agent in a *fresh* session and see how far it gets.
Every place it stumbles is a gap in your context engineering, not in the
model.

---

## Module 4 — Progressive Disclosure

The design discipline that keeps context spend proportional to need. It shows
up at every scale of an AI-native system.

- **Layer knowledge by loading cost.** Always-on context carries only
  imperative rules. Evidence, procedures, and templates live in referenced
  files loaded at the moment of use. A skill's trigger description is its
  only always-on cost; the body is free until invoked.
- **Make disclosure a typed, per-item decision.** For every piece of standing
  guidance ask: does the agent need this in *every* session (inline), or does
  it only need to know a fuller procedure *exists* (a one-line pointer that
  hands off to an on-demand doc)?
- **Generate your always-on context; don't hand-write it.** Small, versioned,
  single-topic chunks assembled by a reconciler into the actual prompt file —
  reviewable, diffable, drift-detectable via a content hash. Your system
  prompt is a build artifact.
- **Consolidate, don't accrete.** When new evidence arrives, it *replaces*
  the headline and demotes the old source to a compressed trail line. A
  knowledge base that only appends grows until it poisons its own context.
- **Enforce the structure with deterministic checks.** Size budgets, pointer
  integrity, tier discipline ("no citations in the rules layer") — all
  checkable by a stdlib script in CI. Structure that isn't enforced erodes.
- **Apply it recursively to agents:** every sub-agent should see *strictly
  less* than its parent — the minimum context to execute its brief. Never
  more.

**Field trip:** `mnox/mnox-ai: plugins/aio/skills/aio/` — the whole skill is
a worked example: rules in `SKILL.md` (each tagged with a KB claim id),
evidence in `references/knowledge-base.md` (each claim as Rule / Evidence /
Trail), templates loaded only at the step that needs them, and
`evals/check_structure.py` enforcing the tiering deterministically — its
checks exist specifically to prevent evidence bleeding back into the
always-on rules tier.

**Exercise:** take your longest prompt, system prompt, or CLAUDE.md. Split
every line into three piles: (1) imperative rule needed every session,
(2) procedure needed occasionally, (3) evidence/rationale. Move pile 2 into
on-demand files behind one-line pointers, pile 3 behind the rules it supports.
Measure the size reduction of the always-on layer.

---

## Module 5 — Harness Engineering

The load-bearing engineering around the model. This is where classic systems
instincts — the ones you already have — compound hardest.

- **Doctrine that isn't compiled or tested is decoration.** Agents ignore
  prose guidance under pressure, just like humans. Enforce invariants
  structurally: visibility walls that make violations a compile error, guard
  tests that fail when an invariant is reintroduced, contracts with forbidden
  markers scanned by CI. Make the wrong thing impossible, not discouraged.
- **One writer, many projections.** Give the system a single choke point that
  every surface already passes through (one kernel, one DB-writer authority).
  Then authz, validation, telemetry, and event emission come free for every
  surface — including ones that don't exist yet. Mirrors and caches subscribe
  to the event log; they never co-write, because dual writes fork truth.
- **Tool specs are contracts.** Action-verb openings, typed parameters with
  units, semantic field names, few-shot examples, pagination (KB:
  tool-design). Prefer constrained decoding over validate-and-retry: invalid
  output that *cannot generate* beats invalid output you catch (KB:
  structured-output).
- **Instrument the serving path before you need the data.** Per-turn tokens,
  timing, tool calls, file changes. Product decisions about agents become
  undecidable without usage telemetry; one seam at the choke point beats
  per-subsystem instrumentation. Err on tracking more.
- **Automate away permission friction — then constrain the automation.** A
  rules engine that auto-allows provably-safe commands (parsed, segmented,
  cwd-tracked, every segment must pass) with a fixture test suite and an
  explain mode turns a hundred daily prompts into a governed, extensible
  system. Guardrails belong *outside* the agent loop (KB: guardrail-stack),
  and no filter is a complete answer to prompt injection — there are
  impossibility results; design for blast-radius containment instead (KB:
  injection-impossibility).

**Portable contract — hooks on the agent's critical path.** Any code that
runs on every turn (session-start, pre-tool, post-turn) must obey:

1. A hook is an **event-dispatch shim, never a worker** — it publishes a
   bounded payload and returns; a durable consumer does the real work.
2. Return in **milliseconds**; zero business logic inline.
3. Real work forks **detached with stdio severed**
   (`</dev/null >/dev/null 2>&1 &`) — a bare `&` keeps the pipe open and
   blocks the harness until timeout, the classic non-fix.
4. **Exit 0 no matter what.** A hook must never block or break a turn.
5. Hooks are never authoritative over state — the kernel/consumer owns
   idempotency, retries, and reconciliation.
6. Never fall back to a stale binary or path: resolve explicitly and *fail*
   if missing — "a stale binary that still runs fails invisibly, which is
   strictly worse than a missing one."

**Exercise:** pick one invariant you currently enforce by telling the agent
about it in a prompt. Re-enforce it structurally: a pre-tool-use hook, a
lint/test that fails, or an API that makes the violation unrepresentable.
Then delete the prompt line.

---

## Module 6 — Delegation: Briefing the Stranger

Multi-agent isn't sophistication — it's a cost you pay when you must. When you
do pay it, the brief is everything.

- **Justify every step up the ladder.** Single agent + retrieval → prompt
  chaining → routing → parallelization → orchestrator-workers →
  evaluator-optimizer → full agent loop (KB: pattern-hierarchy). Single
  agents match or beat multi-agent at equal compute, because handoffs lose
  information. Fan out only for genuinely parallel, independent work.
- **A sub-agent is a stranger in a clean room.** It knows *only* what the
  dispatch tells it. Every gap in the brief gets filled with a confident,
  plausible, wrong guess — the most expensive failure mode in delegated work.
- **Put the intelligence upstream.** In a pipeline, the admission-controller
  and orchestrator do the thinking — distill requirements, bound scope, mint
  the verification criteria — and the implementor is deliberately the
  scope-*dumbest* rung: narrowest decision space, no mid-task pivots (the #1
  autonomous failure mode). Separate *mandate* (what it may decide) from
  *mechanism* (it can still delegate read-only discovery downward without
  widening its mandate).
- **Fold results back as hypotheses, not facts.** And treat prior
  memory/context as priors to verify, not truth to obey.
- **Escalate to humans like it costs money — because it does.** Exhaust your
  sources first, cheap to expensive: memory → session history → plans →
  internal docs → codebase → public specs → web. (Broad code search comes
  late, not first.) Then bring ELI5 background and commit to ONE
  recommendation with a confidence and a what-settles-it condition. No a/b/c
  menus. "Can't confidently recommend" means "haven't researched enough,"
  not "time to ask."

**Portable template — the seven-part brief.** Before dispatching any
sub-agent (or, honestly, any contractor):

```markdown
1. OBJECTIVE      — stated as a result, not an activity.
2. PROVENANCE     — why this exists, why now, what it feeds into.
3. PAYLOAD        — everything needed, inlined; absolute paths only.
                    Never assume shared context. There is none.
4. BOUNDARIES     — explicitly in scope AND explicitly out of scope.
5. KNOWN TRAPS    — dead ends already hit; do-not-repeat list.
                    (The highest-leverage, most-omitted section.)
6. DEFINITION OF DONE + RETURN CONTRACT — exact shape/length/format
                    of what comes back.
7. ROUTING        — which model/agent tier and why (cheap for discovery,
                    expensive for synthesis and validation).
```

The gate before sending: *could a competent stranger with zero access to this
conversation execute this brief and return exactly what I need?* If not, the
failure that follows is yours, not the agent's. When a result comes back thin
or off-target, the failure is usually the brief, not the agent.

**Field trip:** `mnox/codex: AGENTS.md` and the dispatch sections of
`DINGLEHOPPER.md` — bounded dispatch behind blessed worker profiles with hard
caps (timeouts, output-size limits), per-run artifacts, and standing scope
limits (workers can't push, can't touch external APIs, can't edit the
harness's own tree).

**Exercise:** next time you're about to delegate to a sub-agent (or a
teammate!), write the seven-part brief first. Send *only* the brief. Score
the result: every deficiency traces to a brief section you skimped on.

---

## Module 7 — The Groundwork for Autonomy: Verify, Bound, Meter

Autonomy is not a model property. It's a property of the system you build
around the model — and it extends exactly as far as three things:

- **Verify: gate autonomy on verifiability, not confidence.** A
  *deterministic predicate* — a tamper-proof check the worker cannot edit —
  decides whether a unit of work is defined well enough to run unsupervised.
  Write the verifier *before* dispatching. If you can't write one, the unit
  isn't ready; it escalates. And every escalation is a structured signal
  telling you what to build next. Never let an LLM self-assessment stand in
  for the predicate.
- **Bound: make every autonomous action reversible by construction.**
  Isolated workspaces/worktrees; no push, no merge, no deploy from inside
  the loop. Crossing to the shared world is always a human gate — and that
  gate is a design *feature*, not a compromise: it's what makes everything
  upstream safe to automate aggressively. Containment must bind the whole
  agent subtree (sub-agents inherit the sandbox and the denials). Process
  isolation, not language-level sandboxing, is the trust boundary (KB:
  tool-exec-sandbox).
- **Meter: treat dispatch as a budget with structural enforcement.** Bounded
  concurrency, timeouts, output-size caps, strict output schemas, resumable
  state files, and a dry-run before the first real token. Budgets should be
  transition guards — a breach structurally *blocks* dispatch rather than
  warning about it. Unmetered fan-out is how agentic systems fail
  expensively. And consolidate your dispatch primitive: the canonical
  failure is hand-rolling it three times in three places.
- **Recovery is a designed loop, not an assumed capability.** Given Module
  2's diagnosis/recovery gap: plan for the mostly-failed fleet run *before*
  the run — salvage manifests, per-unit merge verdicts, human-review flags,
  and a rollback bundle. Resource exhaustion is a harness concern too:
  admission control that defers (never refuses), single-flight locks, and
  heartbeats — because a queued job looks exactly like a wedged one.

**Portable checklist — defining one autonomous work unit:**

```markdown
- [ ] Objective as a verifiable result
- [ ] Deterministic verifier, written first, worker cannot edit it
- [ ] Containment boundary (isolated workspace; what it may never touch)
- [ ] Budget: max tokens / time / sub-agents / retries — enforced, not advisory
- [ ] Escalation path: the typed abstention it returns when under-resourced
- [ ] Recovery plan: what "failed" produces (salvage, verdict, rollback)
- [ ] Provenance: where its decisions get logged (Module 8)
```

**Field trip:** `mnox/codex: dingle/` — the dispatch runs and eval
directories show metered dispatch in practice: per-run artifact bundles,
sealed manifests, canary trajectory tests, and honest baseline comparisons.

**Exercise:** design (on paper) one task from your last job as an autonomous
work unit using the checklist. If you can't write the verifier, write down
precisely *why* — that gap is the actual state of the art.

---

## Module 8 — Provenance and Memory

Autonomous systems generate decisions faster than humans can audit them. The
counterweight is provenance discipline — and deep skepticism about memory.

- **Record interpretation, not just instruction.** Keep the human's verbatim
  words immutable and separate from the agent's *interpretation written at
  the time*, and from what got built. Drift enters exactly at the
  interpretation layer, and almost nobody records it. Corollary: "we built
  exactly what was said" is not validation — fidelity and correctness are
  independent axes.
- **Log decisions with type and altitude.** This enables the inverse query —
  *which decisions caused this fault?* — and closes a learning loop where
  confirmed fault-causing decisions become negative training signal. Include
  an honesty guard: report "no decision record found — likely a manual
  change" rather than fabricating a culprit. A portable decision-record
  shape:

  ```markdown
  decision:
    type: autonomous | user-directed | prompted
    altitude: foundational | architectural | tactical
    rationale: <one paragraph>
    alternatives_considered: [...]
    files_touched: [...]
    anchor: commit_sha (or files+timestamp when no commit exists)
  ```

- **Supersede, never delete.** Mark dead sections `archaeology_only` with a
  banner naming what replaced them; keep the reasoning record. A clean doc
  can still be stale — and a deleted rationale guarantees the debate gets
  re-run from scratch. Never create `-v2` sibling docs.
- **Divergence is not failure; *undetected* divergence is.** Keep an open
  ledger of places where implementation drifted from intent, adjudicated by
  a human — never silently edit the intent to match the code.
- **Be deeply suspicious of agent memory.** Don't add a memory system by
  default — long-context baselines often beat them, and naive
  write/consolidation actively *propagates errors*, sometimes below the
  no-memory baseline (KB: memory-justify, memory-harms). The dominant lever
  is agent-controlled read/write, not storage topology; and memory needs a
  governance model (who writes, who reads, who forgets) before any
  vector-vs-graph debate.

**Field trip:** `mnox/codex:
dingle/evals/context-management/state-ownership-contract.md` — memory as an
ownership problem, not a summarization problem: a claim = statement + owner +
authority + evidence + lifecycle + freshness + invalidation rule, with
agent / tool-observed / verifier / human kept as distinct trust levels.
"Compaction quality is mostly a lifecycle test: did the agent forget
correctly?"

**Exercise:** for your next agent-assisted change, keep a decision log using
the record shape above. A week later, pick one odd line of code and try to
answer "which decision caused this?" from the log alone.

---

## Module 9 — Evals, Telemetry, and Cost (read alongside Modules 5–7)

You cannot iterate on what you cannot measure, and most of the measuring
tools lie.

- **Three-layer testing:** mocked-LLM unit tests in CI (fast, free,
  deterministic) → eval suites with threshold assertions → integration/E2E
  targeted at known failure modes (KB: three-layer-testing).
- **Validate the judge.** LLM judges are highly self-consistent *and*
  frequently invalid — consistency is not validity; rankings can swing wildly
  under judge changes (KB: judge-validity). Public agent benchmarks are
  effectively all exploitable to near-perfect scores (KB:
  benchmark-contamination). Build small, held-out, adversarial evals from
  your own failures.
- **Split deterministic from behavioral evals.** Structural invariants get a
  stdlib script; behavior gets golden scenarios with must-include /
  must-NOT-do rubrics. Run the cheap layer constantly, the judged layer
  deliberately.
- **Instrument abstentions and near-misses**, not just successes — Module 2's
  gap signals are your highest-information telemetry and your roadmap.
- **Cost is a co-equal axis.** Optimizing accuracy alone costs 4–10× more
  (KB: cost-accuracy); output tokens dominate agent spend; cache only stable
  layers (naive full-context caching can *increase* latency); a tuned static
  routing threshold often beats clever cascades (KB: cache-pitfall,
  routing-cascades).
- **Measure your own tooling's ROI** against a stock baseline, and be willing
  to conclude it isn't worth it.

**Field trips:**
- `mnox/mnox-ai: plugins/aio/skills/aio/evals/` — the
  deterministic/behavioral split in miniature: `check_structure.py`,
  `scenarios.md`, and the README explaining why both layers exist.
- `mnox/mnox-ai: plugins/aio/skills/aio/references/readiness-checklist.md` —
  a 23-item production gate; the best "did I actually do the work" artifact
  in either repo.

**Exercise:** write five eval cases for any agent behavior you rely on —
including two adversarial ones drawn from real failures you've seen. Add one
deterministic structural check. Wire them to run on every change.

---

## Capstone — Make the Title True

The credential in "AI-native product engineer" isn't the phrase — it's that
every syllable is backed by artifacts. Build yours:

1. **Build a harness, however small.** A skill/command system with
   progressive disclosure, a permission hook obeying the Module 5 contract,
   per-session telemetry. It can be personal tooling — personal tooling is
   where these instincts form fastest, because you feel every failure
   yourself.
2. **Run the audit.** Take any agentic implementation — yours, open-source,
   a take-home — and audit it against the readiness checklist: resourcing,
   escape hatches, context discipline, verification gates, containment,
   telemetry, cost. Write findings with evidence. (The audit methodology
   itself is `mnox/mnox-ai: plugins/aio/skills/aio/SKILL.md`, Mode 1 — it's
   a runnable skill; install the plugin and point it at a codebase.)
3. **Ship one bounded autonomous loop.** One work type, one deterministic
   verifier, one containment boundary, one budget, one escalation path, with
   provenance. Small and real beats large and aspirational.
4. **Write it up.** The write-up — what you bounded, what you refused to
   automate, what the gap signals taught you — is exactly the artifact that
   separates you in interviews. Anyone can say "I use AI." Almost nobody can
   show a verifier they wrote, a blast radius they bounded, and a telemetry
   trail proving it worked.

**The interview-ready summary of this whole dossier, in five sentences:**
The harness is the product, and the model's weaknesses are the engineer's
requirements. Context is a budget where more is often worse, so disclose
progressively and delegate to strangers with complete briefs. Autonomy
extends exactly as far as deterministic verification, bounded blast radius,
and metered dispatch. Every decision needs provenance; every abstention needs
a sink; every judge needs judging. And none of it is prompt magic — it's
systems engineering, which is what you already know how to do.
