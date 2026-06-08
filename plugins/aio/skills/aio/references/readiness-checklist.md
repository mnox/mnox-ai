# Production Readiness Checklist

Load this at Mode 2 Step 4, before declaring a new agentic implementation "done".

- [ ] Architecture pattern justified (simplest that works) `[KB:pattern-hierarchy]`
- [ ] Tools follow Anthropic's design guidance `[KB:tool-design]`
- [ ] Context engineering strategy in place (progressive disclosure — just-in-time, not front-loaded) `[KB:context-eng]` `[KB:progressive-disclosure]`
- [ ] Memory justified, not added by default `[KB:memory-justify]`
- [ ] Unit tests for tool routing / schema validation `[KB:three-layer-testing]`
- [ ] Eval suite with threshold assertions
- [ ] Integration tests for failure modes
- [ ] Structured output via constrained decoding where possible `[KB:structured-output]`
- [ ] Failure-attribution loop + a separately-measured recovery path `[KB:failure-attribution]` `[KB:diagnosis-recovery-gap]`
- [ ] Input guardrails (prompt injection prevention) + impact containment `[KB:injection-defense]` `[KB:injection-impossibility]`
- [ ] Output validation
- [ ] Tool-execution surfaces sandboxed (process-level isolation) `[KB:tool-exec-sandbox]`
- [ ] Agent identity / MCP auth scoped least-privilege `[KB:agent-identity]`
- [ ] Human-in-the-loop for high-risk operations `[KB:hitl]`
- [ ] Escape hatches: sanctioned abstention path at every high-stakes decision (never guess-only) `[KB:abstention]`
- [ ] Gap-signal capture wired to a queryable sink + a loop into the roadmap `[KB:gap-signals]`
- [ ] Cost optimization (model routing, caching) `[KB:cost-optimization]` `[KB:cache-pitfall]`
- [ ] Observability (tracing, logging, metrics; OTel GenAI conventions) `[KB:otel]`
- [ ] Error handling with actionable guidance
- [ ] Kill switch / circuit breaker
- [ ] Compliance requirements met — EU AI Act transparency (Aug 2026) / NIST, if applicable `[KB:eu-ai-act]` `[KB:nist]` `[KB:compliance-properties]`
