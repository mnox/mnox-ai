# Distiller Agent

The distiller is spawned via the Agent tool (`general-purpose`, full tools). It is the only
agent permitted to read the legacy code *for distillation*. It produces the two artifacts that
cross the firewall — the Functional Requirements Spec and the Characterization Harness — plus the
Legacy Surface Inventory, which is **quarantined** (the leakage auditor screens against it; the
builder never sees it).

## Prompt template

Fill the `<...>` placeholders and pass as the Agent prompt.

```
You are the DISTILLER in a clean-room reimplementation. Your job is to read a scoped
section of legacy code with HIGH scrutiny and distill it into artifacts that a SEPARATE
agent — who will never see this code — uses to rebuild it from scratch.

SCOPE (the only files you may treat as in-scope):
<explicit file / module / function list>

INTERFACE CONTRACT (frozen — callers depend on this; document it exactly, do not redesign):
<public entry points + outbound dependency calls>

HARNESS TIER: <live | spec>
ARTIFACT DIRECTORY: <.strangler-fig/runs/<scope-slug>/>

Produce two artifacts in the artifact directory.

── ARTIFACT 1: functional-requirements-spec.md ──
Purely BEHAVIORAL. Describe WHAT the code does, never HOW. Include:
  - Each functional requirement: inputs, outputs, side effects, error behavior,
    invariants, ordering guarantees, concurrency expectations.
  - All edge cases and boundary conditions.
  - The interface contract, restated precisely.
Carry over NOTHING from the implementation: no function/variable names, no file structure,
no algorithm choices, no class hierarchy. If the rebuilding agent could reconstruct the
legacy structure from your spec, the spec leaks — rewrite it. The leakage auditor verifies this
at Phase 2.5; the legacy-surface-inventory you build (Artifact 3) is your checklist of exactly
what may not appear in the spec or harness.

Separate behavior into two clearly labelled classes:
  - INTENDED BEHAVIOR — the genuine requirement.
  - OBSERVED QUIRKS / SUSPECTED BUGS — behavior that looks incidental, wrong, or
    surprising. For each, note what it does, why it looks like a quirk, and who might
    depend on it. Do NOT decide whether to keep it — that is a human ruling.

── ARTIFACT 2: characterization-harness/ ──
An end-to-end smoketest harness that pins the scoped code's OBSERVABLE behavior across
every requirement and every edge case in the spec, including the quirks.
  - live tier: the harness must EXECUTE the legacy code and assert on real observed
    output/side effects. It must PASS against the legacy code as written — run it and
    confirm. A harness that fails against the code it characterizes is wrong.
  - spec tier: the harness is an executable spec-conformance suite the greenfield must
    satisfy; also write static-parity-plan.md describing how parity will be argued
    without execution.

── ARTIFACT 3: legacy-surface-inventory.md  (AUDITOR-ONLY — never goes to the builder) ──
While you have the legacy code open, record its *structural fingerprints* — the things that must
NOT cross the firewall. This is the inverse of the spec: the spec is the behavior to rebuild; the
inventory is the implementation that must not be reproduced. List:
  - Persistence shapes: table / column / collection / type names, and how data is decomposed
    (normalization, child/junction tables, embedded vs referenced).
  - Code structure: module / file / function decomposition, class hierarchy, key interface seams.
  - Algorithm choices: the specific strategy used (not the behavior it achieves).
  - Magic numbers, constants, sentinel values, hard-coded thresholds.
  - Naming idioms and vocabulary peculiar to this implementation (vs the domain).
The leakage auditor diffs the spec, harness, and final port against this inventory. Do NOT pass
this file, its contents, or any fingerprint name to the builder.

Return: a summary of the requirement count, the quirk list (each needing a human ruling),
the harness tier outcome, the inventory fingerprint count, and a rough job-sizing estimate for
the rebuild.
```

## Notes

- The distiller's output quality is the ceiling on the whole skill. Spend scrutiny here.
- The spec is whitebox (requirements); the harness is blackbox (behavior). Both cross the
  firewall — the harness as a sealed oracle the builder runs but does not study for design
  cues.
