---
name: strangler-fig
description: Use when rebuilding a scoped section of legacy code clean-room — when the existing implementation is polluting attempts to improve it and a from-scratch rewrite is wanted. Distills the legacy code to pure functional requirements, builds a firewalled greenfield reimplementation that a separate agent designs WITHOUT ever seeing the legacy code, verifies behavioral parity, and optionally cuts over. Triggers on /strangler-fig, clean-room rewrite, rebuild this module from scratch, strangle this legacy code, the old code keeps leading the rewrite astray.
---

# Strangle — Clean-Room Legacy Reimplementation

## Overview

`/strangler-fig` rebuilds a scoped section of legacy code by distilling it to pure functional
requirements, then having a **separate, firewalled agent** design and build a greenfield
reimplementation that never sees the legacy code. The premise: adjacent and inline legacy
code pollutes code generation — an agent shown a flawed implementation anchors to it.
The fix is a structural context firewall, not a polite request to "ignore the old code".

## Quick Reference

| Run mode | Phases | Use when |
|----------|--------|----------|
| `distill` | 0–2 | Cheap first pass — produce requirements spec + characterization harness, no rebuild. Size the job. |
| `artifact` *(default)* | 0–4 | Full firewalled greenfield build, proven against the harness, in an isolated directory. Hands back a verified artifact + cutover plan. Nothing touches live code. |
| `cutover` | 0–5 | Continues into a gated phase that wires the swap and removes legacy in-repo. Resumes cleanly from a prior `artifact` run. |

| Harness tier | Meaning | Parity guarantee |
|--------------|---------|------------------|
| `live` | Legacy code is executable in isolation; harness pins real observed behavior. | **Proven** — behavioral diff is a real test. |
| `spec` | Execution infeasible (DB/services/env); harness degrades to spec-conformance + static parity analysis. | **Reasoned argument**, not proof. Residual risk flagged in the final report. |

The skill auto-detects the tier, announces it, and never silently downgrades.

## The Context Firewall (core mechanism)

The skill is multi-agent so that isolation is *enforced by structure*, not by instruction:

```
DISTILLER agent  ──reads legacy code──►  produces two artifacts:
                                          • Functional Requirements Spec  (whitebox: intended behavior)
                                          • Characterization Harness      (blackbox: behavior oracle)
                                                   │
                                                   ▼
                              BUILDER agent  — FIREWALLED —
                  fresh context, never given the legacy repo path,
                  receives ONLY the spec + harness + interface contract.
                  Designs from industry patterns, builds to pass the harness.
```

Two hard rules that make the firewall real:
1. **The builder is never given a path to the legacy code**, and the greenfield is built in
   a clean directory that does not contain the legacy code. The builder *cannot* read it.
2. **The harness is the backstop.** If the distiller misses a requirement, the spec won't
   carry it — but the harness will catch the behavioral gap. So the distiller (who saw the
   code) builds the harness; it crosses the firewall as a sealed black-box oracle.

## Workflow

Copy this checklist and track progress:

```
Strangle Progress:
- [ ] Phase 0: Scope, intake, run mode, harness tier, workspace
- [ ] Phase 1: Distillation — Functional Requirements Spec
- [ ] Phase 2: Characterization harness (proven against legacy first)
- [ ] Phase 3: Firewalled greenfield design & build
- [ ] Phase 4: Parity verification
- [ ] Phase 5: Cutover  (cutover mode only)
```

### Phase 0 — Scope, intake, workspace

1. Pin the **boundary**: exact files / module / function set in scope. Anything outside is
   off-limits to all phases.
2. Pin the **interface contract** — the public entry points callers depend on, plus the
   outbound dependencies the scoped code calls. This contract must survive the rebuild
   unchanged; it is the one thing greenfield may NOT redesign.
3. Gather intake facts: language/stack, how the scoped code is built and tested, whether it
   can be executed in isolation, business criticality, known pain points.
4. Decide the **run mode** (`distill` / `artifact` / `cutover`) — confirm with the user via
   the host's structured clarification mechanism when available if not specified.
5. Decide the **harness tier**: probe whether the scoped code can be executed in isolation.
   If yes → `live`. If no → `spec`. Announce the tier explicitly.
6. Create the workspace:
   ```bash
   uv run scripts/init_workspace.py <repo-path> <scope-slug>
   ```
   This creates the artifact directory under `.strangler-fig/runs/<scope-slug>/` and a clean, empty
   greenfield directory under `.strangler-fig/greenfield/<repo-name>-<scope-slug>/` (relative to the
   current working directory by default; override the base with `--out-dir`).

### Phase 1 — Distillation

Spawn the **distiller** sub-agent (see `references/distiller-agent.md` for the full prompt).
It reads the in-scope legacy code with high scrutiny and produces the **Functional
Requirements Spec** in the artifact directory. The spec is purely behavioral — inputs,
outputs, side effects, error behavior, invariants, edge cases — and carries NO
implementation detail, structure, or naming from the legacy code.

Critically, the spec separates two classes of behavior:
- **Intended behavior** — the genuine functional requirement.
- **Observed quirks / suspected bugs** — behavior that looks incidental or wrong.

Surface every quirk to the user for an explicit keep-or-fix ruling. Do not let greenfield
silently replicate a bug, and do not silently fix one — legacy code is not ground truth,
but callers may depend on its quirks.

### Phase 2 — Characterization harness

The distiller (same agent — it has seen the code) builds an end-to-end smoketest harness in
the artifact directory that pins the scoped code's observable behavior across the full
requirement set, including the edge cases and the user-ruled quirks.

- **`live` tier:** run the harness against the *legacy* code first. It MUST pass before it
  is trusted — that proves the oracle is accurate. A harness that fails against the code it
  characterizes is wrong; fix it before proceeding.
- **`spec` tier:** the harness becomes an executable spec-conformance suite the greenfield
  must satisfy, plus a documented static parity-analysis plan.

`distill` mode stops here: deliver the spec + harness + a job-sizing summary.

### Phase 3 — Firewalled greenfield build

Spawn the **builder** sub-agent (see `references/builder-agent.md`). It runs with its working
directory set to the clean greenfield directory and is given ONLY:
- the Functional Requirements Spec,
- the interface contract,
- the characterization harness.

It is **not** given the legacy repo path. It designs a clean architecture from first
principles and industry-standard patterns, and builds the implementation until the harness
passes. If the builder asks to see the legacy code, refuse — that request is the firewall
working as designed.

### Phase 4 — Parity verification

Run both arms through the harness with identical inputs; diff outputs and side effects.
- Resolve any quirk-related deltas against the Phase-1 user rulings.
- Genuine deltas (greenfield behaves differently on an *intended* requirement) are bugs in
  greenfield — send back to the builder.
- Produce the **parity report** (`references/parity-report-template.md`) in the artifact
  directory. On `spec` tier, the report states plainly that parity is a reasoned argument
  and names the residual-risk surface.

`artifact` mode stops here: deliver the proven greenfield directory + parity report +
cutover plan.

### Phase 5 — Cutover (cutover mode only)

Low-freedom, gated. Per the interface contract, integrate greenfield into the live repo —
either behind a facade/feature flag or as an inline replacement — then remove the legacy
code only after parity is green. This phase mutates shared code: present the exact plan and
get explicit user approval before any edit. Never commit without explicit permission.

## Common Mistakes

### ❌ Letting the builder see the legacy code

**Problem:** Giving the builder agent the legacy repo path, or building greenfield in a
directory that still contains the legacy files.

**Why it's wrong:** It collapses the firewall. The builder anchors to the flawed
implementation — the exact pollution the skill exists to prevent.

**Fix:** Build in a clean directory with no legacy code present. Give the builder only the
spec, harness, and interface contract. Refuse any request it makes to view the legacy code.

### ❌ Trusting an unverified harness

**Problem:** Writing the characterization harness and immediately using it as the parity
oracle without first running it against the legacy code.

**Why it's wrong:** A harness that doesn't actually pass against the code it characterizes
encodes wrong expectations — greenfield then "passes" a lie.

**Fix:** On `live` tier, the harness MUST pass against legacy before it is trusted.

### ❌ Silently replicating or fixing quirks

**Problem:** Treating every observed legacy behavior as a requirement, or quietly
"correcting" behavior that looks like a bug.

**Why it's wrong:** Legacy code is evidence of what was built, not what is correct — but
callers may depend on a quirk. Either silent choice can break consumers.

**Fix:** Separate intended behavior from quirks in the spec; get an explicit user ruling on
each quirk before greenfield is built.

### ❌ Redesigning the interface contract

**Problem:** Greenfield "improves" the public entry points or the outbound dependency calls.

**Why it's wrong:** The contract is what decouples this rebuild from everything else. Change
it and the blast radius escapes the scope — every caller now needs changes too.

**Fix:** Greenfield may redesign everything *inside* the boundary freely; the interface
contract is frozen. Interface changes are a separate, later decision.

## Notes

- Artifacts (spec, harness, parity report, cutover plan) live under
  `.strangler-fig/runs/<scope-slug>/`. Greenfield code builds in
  `.strangler-fig/greenfield/<repo-name>-<scope-slug>/`.
- `spec`-tier runs carry real residual risk: with no behavioral backstop, a requirement the
  distiller misses is genuinely lost. The final report must say so.
- The skill never commits or pushes without explicit user permission (Phase 5 included).
- Higher run modes are supersets — `cutover` resumes from a prior `artifact` run rather than
  redoing phases 0–4.
