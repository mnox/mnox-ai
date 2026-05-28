# Distiller Agent

The distiller is spawned via the Agent tool (`general-purpose`, full tools). It is the only
agent permitted to read the legacy code. It produces the two artifacts that cross the
firewall: the Functional Requirements Spec and the Characterization Harness.

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
legacy structure from your spec, the spec leaks — rewrite it.

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

Return: a summary of the requirement count, the quirk list (each needing a human ruling),
the harness tier outcome, and a rough job-sizing estimate for the rebuild.
```

## Notes

- The distiller's output quality is the ceiling on the whole skill. Spend scrutiny here.
- The spec is whitebox (requirements); the harness is blackbox (behavior). Both cross the
  firewall — the harness as a sealed oracle the builder runs but does not study for design
  cues.
