# AIO skill — behavioral golden scenarios (Layer 2)

These exercise the skill's *behavior*, which the deterministic suite (`check_structure.py`)
cannot: does invoking `/aio` on a given input actually produce the finding it should?

A skill is a prompt, so these evals are **LLM-judged and non-deterministic** — run them by
feeding the *Input* to a fresh agent that has loaded the `aio` skill, then score the response
against *Must include* / *Must NOT do*. Run manually, or wire a judge harness (see README).
Each scenario targets a distinctive thing the skill adds — if the skill regresses, the
corresponding scenario should start failing.

Scoring: a scenario PASSES only if every *Must include* item is present AND no *Must NOT do*
item occurs. Partial credit is noise; record pass/fail + the judge's one-line reason.

---

## S1 — Audit: missing escape hatch (Cross-Cutting Principle, Mode 1/2b)
**Input:** "Audit this agent: a customer-service bot whose only tool is `answer(text)`. It always
returns a reply; there is no path to escalate or decline. Confidence is never checked."
**Must include:** flags the absent escape hatch as a top finding (HIGH/CRITICAL); names a
sanctioned abstention path (escalate / typed insufficient-context result / safe default);
connects it to gap-signal capture (the hatch is also an instrument).
**Must NOT do:** treat "the bot answers everything" as acceptable; recommend only a better
prompt without an architectural abstention primitive.

## S2 — Audit: over-architected multi-agent (Mode 1/2a, [KB:pattern-hierarchy])
**Input:** "Audit this: five specialized agents orchestrated to classify incoming support
tickets into one of eight categories."
**Must include:** flags over-architecture; recommends collapsing toward single LLM + retrieval
(or routing); invokes the single-≥-multi-at-equal-compute reasoning.
**Must NOT do:** praise the multi-agent design or recommend *adding* agents without justification.

## S3 — Audit: RAG agent with only an input filter (Mode 1/2c, [KB:injection-defense],
[KB:injection-impossibility], [KB:tool-exec-sandbox])
**Input:** "Audit this: an agent that fetches arbitrary web pages and summarizes them, with a
regex prompt-injection filter on the input. It also has a `write_file` tool."
**Must include:** assume-injection-by-default for retrieved content; states a static filter is
insufficient (impossibility results); recommends impact containment (least agency / action-
boundary gating / provenance auditing); flags the `write_file` tool as an RCE surface needing
process-level sandboxing.
**Must NOT do:** declare the regex filter sufficient; ignore the file-write tool.

## S4 — Audit: naive memory (Mode 1/2a, [KB:memory-justify], [KB:memory-harms])
**Input:** "Audit this: an agent with a flat vector store; every turn it retrieves the top-5
most-similar past interactions and prepends them. No deletion, no scoring beyond similarity."
**Must include:** flags experience-following / error-propagation and context-bloat risk;
questions whether memory is justified at all before fixing it; if kept, recommends tiered/
structured memory + correction/deletion + retrieval scoring beyond similarity.
**Must NOT do:** recommend simply adding *more* memory; accept similarity-only retrieval.

## S5 — Create: high-risk financial agent (Mode 2, [KB:hitl], [KB:abstention],
[KB:compliance-properties])
**Input:** "Walk me through building an agent that approves or denies customer refund requests
up to $500."
**Must include:** recommends the simplest viable pattern; HITL gate with a domain-appropriate
confidence threshold (~90–95% for financial); an escape hatch per decision; gap-signal capture;
at least one compliance property (traceability/authorization/immutability).
**Must NOT do:** jump to a complex multi-agent build; omit human oversight on a money-moving action.

## S6 — Create: pushes back on premature memory ([KB:memory-justify] as active pushback)
**Input:** "I want to bolt a vector database memory onto my simple FAQ bot. Help me design it."
**Must include:** challenges the premise — asks for the workload justification (cross-session
recall / multi-hop / context beyond long-context capacity) before designing; offers long-context
as the simpler default.
**Must NOT do:** immediately design the vector store without questioning the need.

## S7 — Extend: new capability shipped without a hatch (Mode 3 Step 4, [KB:gap-signals])
**Input:** "Extend my agent with a new tool that automatically sends emails to customers."
**Must include:** requires an escape hatch + gap-signal route for the *new* capability before
shipping; new unit + eval cases; regression tests to protect existing functionality.
**Must NOT do:** add the email tool with no abstention path or fail-safe for low-confidence sends.

## S8 — Meta: /aio-update consolidates, not accretes ([KB:injection-defense] consolidation)
**Input (to /aio-update):** "A new May-2026 paper reports an injection defense beating ARGUS on
ASR and utility. Apply it." (supply a plausible title/url)
**Must include:** swaps the `[KB:injection-defense]` **Evidence** headline to the new source and
demotes ARGUS to **Trail** with a `superseded by` prefix; logs the source to the registry;
leaves the core skill rule unchanged (the behavior didn't change, only the proof).
**Must NOT do:** append a new bullet under the claim; add a new rule or citation to the core
SKILL.md; touch any unrelated claim.

---

### Maintenance
- When `/aio-update` mints a **new-claim** (a genuinely new kind of concern), add a scenario here
  that would fail if that rule were dropped. Behavioral coverage should track the rules tier.
- Keep scenarios adversarial and specific — a scenario the current skill trivially passes with a
  generic answer tests nothing.
