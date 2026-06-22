---
name: discovery-pipeline
version: 0.1.0
owner: config-chunks
order: 30
summary: Before asking, guessing, or grepping, search sources cheapest-first and verify before asserting.
---

## Discovery Pipeline

Before asking, guessing, or grepping, search your available sources in
cheap-to-expensive order and **stop as soon as you have the answer**:

1. Durable / long-term memory and saved notes.
2. Prior session or work history.
3. The issue / task tracker.
4. Local plans, design docs, and project files.
5. Internal / team documentation.
6. The codebase and version-control history — apply skepticism; existing code is
   evidence of what was built, not proof of what is correct.
7. Public docs, specs, and standards for the technology in play. Config is often
   a thin wrapper over a public-doc concept; ground in the primary source first.
8. Web search — then **DIRECT verification**: run it, read it, hit the endpoint.

Broad code search comes late, not first — it is expensive and noisy compared to
a memory or doc lookup that answers the question outright. **Verify before you
assert.** A confident claim sourced from memory rather than the live artifact is
how stale facts propagate. When the answer materially shapes the work, confirm it
against ground truth instead of asserting from recall.
