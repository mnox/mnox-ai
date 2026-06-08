# AIO Audit Report Template

Load this at Mode 1 Step 3 (Synthesize & Report). Collect all sub-agent findings and produce:

```
## AIO Audit Report

### Architecture Assessment
- Pattern: [identified pattern] — [appropriate / over-architected / under-architected]
- Tool Design: [score] — [key findings]
- Context Engineering: [score] — [key findings]

### Reliability Assessment
- Unit Tests: [present/absent] — [findings]
- Evals: [present/absent] — [findings]
- Integration Tests: [present/absent] — [findings]
- Metrics Coverage: [findings]
- Structured Output: [approach used] — [findings]
- Failure Attribution / Recovery: [findings]
- Escape Hatches / Gap Signals: [present/absent] — [findings]

### Safety & Guardrails Assessment
- Input Protection: [present/absent] — [findings]
- Flow Control: [present/absent] — [findings]
- Output Validation: [present/absent] — [findings]
- Injection Defense / Impact Containment: [findings]
- Tool-Execution Sandboxing: [findings]
- Agent Identity / MCP Auth: [findings]
- Human-in-the-Loop: [pattern used] — [findings]
- Compliance Readiness (EU AI Act / NIST): [findings if applicable]

### Production Readiness Assessment
- Cost Optimization: [findings]
- Observability: [findings]
- Compliance: [findings if applicable]

### Priority Recommendations
1. [Highest impact recommendation]
2. [Second highest]
3. [Third highest]
...

### Reference
[Relevant KB claim-ids / papers for identified gaps]
```

Severity scale for each finding: **CRITICAL / HIGH / MEDIUM / LOW**.
