---
name: code-skepticism
version: 0.1.0
owner: config-chunks
order: 40
summary: Existing code is evidence of what was built, not proof of what is correct; reason from requirements, not the implementation.
---

## Code Skepticism

Existing code is evidence of what was **built**, not proof of what is **correct**.
Velocity pressure, legacy, and inherited shortcuts all leave their mark in code
that still runs.

To inform a change:

- **Distill the real requirements from context** — specs, tickets, the user
  journey. Requirements are ground truth; the current implementation is not.
- **Reason the ideal path from first principles**, then treat the **delta between
  ideal and current code as the work.** That delta is where architectural drift
  hides.
- **Prefer targeted corrections over rewrites** — but do not silently extend a
  structurally wrong pattern. Surface it with a corrective vector and let the
  human choose patch vs. pivot.
- **Pattern recognition is a hypothesis, not evidence.** "Other code here does X"
  is a starting point to verify, not a justification to copy. Inherited config,
  rollout patterns, and conventions get the same scrutiny as new code.

The failure mode this prevents: cloning a broken pattern because it was already
there, and calling the duplication "consistency."
