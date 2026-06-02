# debut — scoring rubric

Single source of truth for weights, penalties, verdict bands, and hard-block
overrides. The orchestrator and every domain agent score against this.

## Domain weights (sum = 100)

| Domain | Weight | Stakes |
|--------|:------:|--------|
| secrets-history | 30 | A leaked secret/PII that goes public is catastrophic and often irreversible. |
| community-health | 20 | README + health files ARE the "presentable" surface. |
| licensing | 15 | No/unclear license = legally unusable, reads as amateur. |
| code-quality | 15 | Sloppy public code is a reputational liability. |
| tests-ci | 10 | No green gate = quality is unverifiable. |
| deps-release | 10 | Supply-chain exposure + version hygiene. |

## How each domain sub-score is computed

Each agent **starts at its full weight** and subtracts penalties for the findings
it confirms, **floored at 0**. Penalties scale by severity, then by that finding's
share of the domain weight. Recommended per-finding penalty as a fraction of the
domain weight:

| Severity | Penalty (× domain weight) | Cap behavior |
|----------|:-------------------------:|--------------|
| 🔴 CRITICAL | 0.50–1.00 | a single critical can zero the domain |
| 🟠 HIGH | 0.25–0.40 | |
| 🟡 MEDIUM | 0.10–0.20 | |
| 🔵 LOW | 0.03–0.08 | |
| ⚪ NIT | 0.00–0.02 | cosmetic; near-zero |

Multiple findings stack until the domain floors at 0. The agent reports the
arithmetic (`weight − Σpenalties = sub-score`) so the orchestrator can audit it.

**Only VALIDATED findings count.** Findings demoted or dropped at the Phase 3
validation gate do not subtract from any sub-score.

## Overall score

`overall = Σ(domain sub-scores)` — already on a 0..100 scale because the weights
sum to 100. The report shows the breakdown table:

| Domain | Weight | Sub-score | Penalty notes |
|--------|:------:|:---------:|---------------|

## Verdict bands

| Band | Condition |
|------|-----------|
| 🟢 **SHIP IT** | overall ≥ 85 AND zero CRITICAL findings AND no hard-block tripped |
| 🟡 **NEEDS POLISH** | overall 60–84, OR a hard-block caps it here |
| 🔴 **NOT READY** | overall < 60, OR a NOT-READY hard-block tripped |

## Hard-block overrides (trump the numeric score)

These fire **regardless** of the computed total:

1. **Verified live secret / credential, or real PII, in working tree OR git
   history → 🔴 NOT READY.** No score can rescue it. (A *verified* secret is one
   confirmed live by trufflehog `verified`, or confirmed by the Phase 3 validation
   gate to be a real credential rather than a test fixture / placeholder.)
2. **No LICENSE file in repo root → cap at 🟡 NEEDS POLISH.** The repo can never
   be SHIP IT without a license, no matter how clean everything else is.

If both a hard-cap and a hard-block-to-NOT-READY apply, NOT READY wins (it is the
stricter outcome).

## PRE-PUSH (diff) mode scoring

In diff mode only a subset of domains run (secrets-history, code-quality on changed
files, licensing/deps delta). Score only the domains that ran, **renormalize the
verdict against the weights of the domains actually evaluated**, and state plainly
in the report that this is a partial (diff-scoped) score, not a full readiness
score. Hard-block overrides still apply in diff mode — a verified secret in the new
commits is still NOT READY.
