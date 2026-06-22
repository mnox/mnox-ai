---
name: strangler-fig
description: Use when rebuilding a scoped section of legacy code clean-room — when the existing implementation is polluting attempts to improve it and a from-scratch rewrite is wanted. Distills the legacy code to pure functional requirements, builds a firewalled greenfield reimplementation that a separate agent designs WITHOUT ever seeing the legacy code, verifies behavioral parity, and audits each firewall crossing for leaked legacy structure (taint / provenance audit) so no legacy implementation detail becomes load-bearing in the clean design, and optionally cuts over. Triggers on /strangler-fig, clean-room rewrite, rebuild this module from scratch, strangle this legacy code, the old code keeps leading the rewrite astray, audit the port for taint, is the rewrite clean of legacy structure.
---

# Strangle — Clean-Room Legacy Reimplementation

## Overview

`/strangler-fig` rebuilds a scoped section of legacy code by distilling it to pure functional
requirements, then having a **separate, firewalled agent** design and build a greenfield
reimplementation that never sees the legacy code. The premise: adjacent and inline legacy
code pollutes code generation — an agent shown a flawed implementation anchors to it.
The fix is a structural context firewall, not a polite request to "ignore the old code".

But the firewall only stops the *builder* from anchoring. Legacy structure can still ride
across inside the spec or harness — a normalized-out table, an algorithm shape, a naming idiom
the distiller copied without noticing — or be reconstructed independently by the builder, and
become load-bearing in the "clean" design. So the skill also runs a **leakage audit** (a.k.a.
taint / provenance audit): it captures the legacy's structural fingerprints up front and
verifies, at each firewall crossing, that nothing structural leaked into the artifacts or the
port. **Behavior crosses the firewall; structure does not.**

## Quick Reference

| Run mode | Phases | Use when |
|----------|--------|----------|
| `distill` | 0–2.5 | Cheap first pass — produce requirements spec + characterization harness, screened clean of legacy structure, no rebuild. Size the job. |
| `artifact` *(default)* | 0–4.5 | Full firewalled greenfield build, proven against the harness AND screened for leaked legacy structure, in an isolated directory. Hands back a verified artifact + cutover plan. Nothing touches live code. |
| `cutover` | 0–5 | Continues into a gated phase that wires the swap and removes legacy in-repo. Resumes cleanly from a prior `artifact` run. |

| Harness tier | Meaning | Parity guarantee |
|--------------|---------|------------------|
| `live` | Legacy code is executable in isolation; harness pins real observed behavior. | **Proven** — behavioral diff is a real test. |
| `spec` | Execution infeasible (DB/services/env); harness degrades to spec-conformance + static parity analysis. | **Reasoned argument**, not proof. Residual risk flagged in the final report. |

The skill auto-detects the tier, announces it, and never silently downgrades.

## The Context Firewall (core mechanism)

The skill is multi-agent so that isolation is *enforced by structure*, not by instruction:

```
DISTILLER agent  ──reads legacy──►  • Functional Requirements Spec   (behavior — CROSSES the firewall)
(sole legacy reader)                • Characterization Harness        (behavior oracle — CROSSES)
                                    • Legacy Surface Inventory        (structural fingerprints — QUARANTINED)
                                              │
              ┌────────────────────────────────┴───────────────────────────────┐
              ▼                                                                  ▼
   BUILDER agent — FIREWALLED —                            LEAKAGE AUDITOR — peer to distiller —
   fresh context; given ONLY spec + harness +              MAY read legacy + the inventory; screens
   interface contract. Never given the legacy              the spec, harness, and final port for
   path or the inventory. Cannot anchor.                   leaked legacy fingerprints. Never feeds
                                                           legacy detail to the builder.
```

Three hard rules that make the firewall real:
1. **The builder is never given a path to the legacy code**, and the greenfield is built in
   a clean directory that does not contain the legacy code. The builder *cannot* read it.
2. **The harness is the backstop.** If the distiller misses a requirement, the spec won't
   carry it — but the harness will catch the behavioral gap. So the distiller (who saw the
   code) builds the harness; it crosses the firewall as a sealed black-box oracle.
3. **Structure is quarantined, behavior is not.** The distiller also records a *legacy surface
   inventory* — the fingerprints that must NOT cross (table/column names, module decomposition,
   algorithm shapes, magic constants, naming idioms). The leakage auditor (a distiller-peer that
   may read legacy, but is firewalled *from* the builder) uses it to verify the spec, harness, and
   final port carry none of them. The inventory and the legacy path go to the auditor only —
   never to the builder.

## Workflow

Copy this checklist and track progress:

```
Strangle Progress:
- [ ] Phase 0: Scope, intake, run mode, harness tier, workspace, legacy surface inventory
- [ ] Phase 1: Distillation — Functional Requirements Spec
- [ ] Phase 2: Characterization harness (proven against legacy first)
- [ ] Phase 2.5: Leakage audit — screen spec + harness before the firewall crossing
- [ ] Phase 3: Firewalled greenfield design & build
- [ ] Phase 4: Parity verification
- [ ] Phase 4.5: Port leakage audit — screen greenfield for reconstructed legacy structure
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
7. Plan the **legacy surface inventory**. While the distiller reads the in-scope code (Phase 1)
   it records `legacy-surface-inventory.md` — the structural fingerprints that must NOT cross the
   firewall (table/column/type names, module & function decomposition, class hierarchy, key
   algorithm choices, magic numbers/constants, naming idioms). This is the *anti-spec*: the spec
   is what should cross, the inventory is what must not. It is the baseline the leakage audit
   diffs against, and it is **auditor-only** — never handed to the builder.

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

### Phase 2.5 — Leakage audit (firewall crossing)

Before anything crosses into the build, screen the two artifacts that *do* cross. Spawn the
**leakage auditor** sub-agent (see `references/leakage-auditor-agent.md`). It is a peer to the
distiller — permitted to read the legacy code and the inventory — and runs two layered passes:

- **Blind smell pass** (no legacy access): reads only the spec + harness and flags anything that
  reads like leaked *implementation* rather than *behavior* — schema-shaped requirements,
  implementation nouns, suspiciously specific decomposition, magic constants with no behavioral
  justification. Cheap; the lens that catches "this requirement is describing a table, not a rule."
- **Legacy-reading deep diff** (the gate): diffs the spec + harness against
  `legacy-surface-inventory.md`, confirming whether each smell is a real fingerprint leak.

Output: `taint-audit-spec.md` (see `references/taint-audit-template.md`) with a CLEAN/LEAKED
verdict. A LEAKED verdict **blocks the crossing** — rewrite the offending spec/harness section to
express the *behavior* without the leaked structure, then re-audit. Do not start the build over a
leaky spec; that is exactly how legacy structure becomes load-bearing in the "clean" design. The
auditor's rewrite instructions describe the behavior to state, never the legacy detail to avoid —
that detail stays quarantined from the builder.

`distill` mode stops here: deliver the spec + harness + inventory + leakage audit + a job-sizing
summary.

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

### Phase 4.5 — Port leakage audit

Parity proves the greenfield *behaves* right; it does not prove the greenfield is *clean*. A
builder can independently reconstruct a legacy shape (convergent evolution), or a leak can have
ridden a tainted spec/harness past Phase 2.5. Re-spawn the **leakage auditor** against the
greenfield port:

- **Blind smell pass:** reads the greenfield code alone for implementation smells and structural
  over-fitting.
- **Legacy-reading deep diff:** diffs the greenfield structure against
  `legacy-surface-inventory.md` for reconstructed fingerprints.

Output: `taint-audit-port.md` with a verdict. A confirmed fingerprint match is **not always a
bug** — sometimes the convergent design is genuinely the only sane one. Treat each match like a
quirk: surface it for an explicit human keep/rework ruling rather than silently rejecting it.
Unruled high/medium leaks block cutover.

`artifact` mode stops here: deliver the proven, screened greenfield directory + parity report +
port leakage audit + cutover plan.

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

### ❌ Assuming a firewalled build is automatically a clean build

**Problem:** Treating the greenfield as taint-free because the builder never saw the legacy
code — skipping the leakage audit.

**Why it's wrong:** The firewall stops the builder *anchoring*, but legacy structure leaks
through other doors: the distiller copies a table shape into the spec, the harness encodes an
implementation idiom, or the builder independently reconstructs a legacy shape. The firewall
guards one path in; the leakage audit guards the rest. (This is the failure that motivated the
audit: a normalized-out legacy table rode the spec into a "clean" schema and became load-bearing.)

**Fix:** Capture the legacy surface inventory in Phase 0/1; run the leakage audit at both
firewall crossings — Phase 2.5 on the artifacts, Phase 4.5 on the port. Behavior crosses;
structure does not.

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

- Artifacts (spec, harness, legacy surface inventory, leakage audits, parity report, cutover
  plan) live under `.strangler-fig/runs/<scope-slug>/`. Greenfield code builds in
  `.strangler-fig/greenfield/<repo-name>-<scope-slug>/`.
- The `legacy-surface-inventory.md` and the leakage audits are **auditor-only** — they contain
  legacy structural detail and must never be handed to the builder.
- `spec`-tier runs carry real residual risk: with no behavioral backstop, a requirement the
  distiller misses is genuinely lost. The final report must say so.
- The skill never commits or pushes without explicit user permission (Phase 5 included).
- Higher run modes are supersets — `cutover` resumes from a prior `artifact` run rather than
  redoing phases 0–4.
