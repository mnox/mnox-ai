# Leakage (Taint) Audit Template

Produced by the leakage auditor at the two firewall crossings:
- **Phase 2.5** → `taint-audit-spec.md` (audits the spec + harness before the build).
- **Phase 4.5** → `taint-audit-port.md` (audits the greenfield port before cutover).

Both use this structure. The audit proves that legacy *structure* did not cross the firewall —
behavior should, structure must not. Fill every section.

```markdown
# Strangle Leakage Audit — <scope-slug> — <spec+harness | port>

## Summary
- Crossing audited: <Phase 2.5 spec+harness | Phase 4.5 port>
- Verdict: <CLEAN | LEAKED>
- Leaks by severity: high <n> · medium <n> · low <n>
- Rulings required before crossing/cutover: <n>
- Date: <YYYY-MM-DD>

## Baseline
- Legacy surface inventory: .strangler-fig/runs/<scope-slug>/legacy-surface-inventory.md
- Artifact(s) audited: <spec + harness paths | greenfield path>

## Blind smell pass (no legacy access)
Implementation smells found by reading only the audited artifact:
| Location | Smell | Reads like implementation because… |
|----------|-------|------------------------------------|
| <file:section> | <e.g. requirement names a child table> | <why it encodes HOW, not WHAT> |

## Legacy-reading deep diff
Each smell (and anything the smell pass missed) confirmed against the legacy + inventory:
| Location | Legacy fingerprint category | Confirmed match? | Severity | Evidence |
|----------|----------------------------|------------------|----------|----------|
| <file:section> | persistence / structure / algorithm / magic-value / naming | yes — LEAK / no — style nit | high/med/low | <what in legacy it mirrors> |

## Required rewrites (Phase 2.5) — behavioral, never legacy detail
For each confirmed leak, the behavior to express instead of the leaked structure:
| Leak | Rewrite instruction (state the behavior, not the legacy detail to avoid) |
|------|--------------------------------------------------------------------------|
| <leak> | <e.g. "State: the system associates 0..N email addresses with a contact." NOT "avoid the emails table."> |

## Convergence rulings (Phase 4.5) — keep or rework
Confirmed fingerprint matches in the port are not automatically bugs — a convergent design may
be the only sane one. Each needs a human ruling:
| Match | Why it converged | Human ruling | Rationale |
|-------|------------------|--------------|-----------|
| <match> | independent design / leaked via spec/harness | keep / rework | <...> |

## Verdict & gate
- <CLEAN: nothing structural crossed; proceed.>
- <LEAKED: list the high/medium leaks that BLOCK the crossing/cutover. Phase 2.5 — rewrite the
  spec/harness and re-audit before the build. Phase 4.5 — obtain keep/rework rulings; rework the
  port for any "rework" ruling and re-audit before cutover.>
```
