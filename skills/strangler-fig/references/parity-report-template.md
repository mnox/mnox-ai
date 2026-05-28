# Parity Report Template

Produced in Phase 4, written to the artifact directory as `parity-report.md`. Fill every
section. The report is the deliverable that tells the user whether the greenfield is safe to
cut over.

```markdown
# Strangle Parity Report — <scope-slug>

## Summary
- Run mode: <distill | artifact | cutover>
- Harness tier: <live | spec>
- Verdict: <PARITY PROVEN | PARITY ARGUED | PARITY FAILED>
- Date: <YYYY-MM-DD>

## Scope
- In-scope files (legacy): <list>
- Interface contract: <restate the frozen entry points + outbound calls>
- Greenfield location: .strangler-fig/greenfield/<repo-name>-<scope-slug>/

## Requirement coverage
| Requirement | Harness covers it | Greenfield result |
|-------------|-------------------|-------------------|
| <req> | yes/no | pass/fail |

## Quirk rulings
| Observed quirk | Human ruling | Honored in greenfield |
|----------------|--------------|-----------------------|
| <quirk> | keep / fix | yes/no |

## Behavioral diff (live tier)
Identical inputs through both arms. List every delta:
| Input case | Legacy output/effect | Greenfield output/effect | Expected? |
|------------|----------------------|--------------------------|-----------|
| <case> | <...> | <...> | yes (quirk-fix ruling) / NO — bug |

## Residual risk
- <spec tier: state plainly that parity is a reasoned argument, not a proof. Name the
  surface the harness could not execute and what a missed requirement there would cost.>
- <live tier: name any behavior the harness could not feasibly cover — non-determinism,
  external side effects, timing.>

## Cutover plan
- Strategy: <facade + feature flag | inline replacement>
- Steps: <ordered, gated>
- Rollback: <how to revert>
- Legacy removal: only after parity green and cutover verified.
```
