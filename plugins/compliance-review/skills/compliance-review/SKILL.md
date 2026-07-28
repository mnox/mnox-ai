---
name: compliance-review
description: Use when auditing a target for regulatory compliance against SOC 2, HIPAA Security Rule, or PCI-DSS - reviewing code/config repos, ADRs/PRDs, IaC posture, or live cloud state for control gaps - OR when assessing organizational readiness for a SOC 2 examination. Triggers - /compliance-review, compliance audit, SOC 2 review, HIPAA review, PCI-DSS review, is this compliant, check compliance, audit against controls, PHI or CHD handling review, SOC 2 readiness, are we ready for SOC 2, Type I vs Type II, what will fail our audit, controls matrix, audit prep, evidence gaps. Auto-detects input mode, fans out parallel control-domain agents, and produces structured findings with control IDs, severity, evidence, remediation, confidence, plus an out-of-scope section for human-attestation controls.
context: fork
---

# Compliance Review

## Overview

Multi-agent compliance auditor that reviews a target against SOC 2, HIPAA Security
Rule, and/or PCI-DSS control catalogs. Auto-detects the input mode (code/config
repo, ADR/PRD, IaC posture, live cloud state, or organizational readiness), fans
out parallel control-domain agents, and produces structured findings with control
IDs, severity, evidence, remediation, confidence, and an explicit out-of-scope
section for controls that can only be satisfied by human attestation.

## Quick Reference

| Input | Detected mode | What the audit checks |
|-------|---------------|-----------------------|
| Repo path / git diff / branch | `code` | Encryption, access control, logging, secrets, dep CVEs, input handling |
| `.md` ADR or PRD (path or pasted) | `design` | Whether the *design* names required controls before build |
| `*.tf` / Helm charts / k8s manifests | `iac` | Encryption settings, network policy, retention, IAM posture |
| "live" / cloud / "check prod" | `runtime` | Actual cloud config via MCP — **see Runtime caveat below** |
| "are we ready" / audit prep / org-level | `readiness` | Whether the **organization** can pass an examination — governance, evidence, program deliverables, phasing, cost |

| Severity | Meaning |
|----------|---------|
| Critical | Active control failure with regulatory exposure (unencrypted PHI/CHD, no audit trail); in `readiness`, blocks the examination or forces a qualified opinion |
| High | Control gap likely to fail an audit; exploitable weakness; in `readiness`, an evidence gap that can force a window restart |
| Medium | Partial control; weak configuration; missing defense-in-depth |
| Low | Hardening opportunity; minor deviation from best practice |
| Info | Observation; no action required |

**`readiness` is a different question from the other four modes.** They ask "does
this artifact implement the controls." Readiness asks "can this organization pass
an examination," where most failures are evidentiary rather than technical: the
control runs, nobody records it, and there is nothing for an auditor to test.

## Workflow

### 1. Resolve scope

Determine three things before fanning out. Ask the user with **AskUserQuestion**
only if they cannot be inferred:

- **Target** — the path, diff, branch, document, "live" indicator, or the
  organization itself.
- **Frameworks** — one or more of `soc2`, `hipaa`, `pci-dss`. If the user did not
  say, infer from the target (PHI handling → hipaa; payment/card code → pci-dss;
  SaaS infra generally → soc2) and state the inferred set.
- **Mode** — auto-detect per the Quick Reference table; state the detected mode.

When `soc2` is active, also resolve and state **two SOC 2-specific parameters**:

- **TSC categories.** Security (Common Criteria) is mandatory. Add Availability,
  Confidentiality, Processing Integrity, or Privacy per the selection table in
  `references/soc2.md`. **Do not default Processing Integrity to out-of-scope** —
  when output correctness is the product (reporting, analytics, billing, data
  transformation, ML scoring), PI is in scope and its absence from the audit is
  itself a gap.
- **Report type.** Type I (design at a point in time) vs Type II (operating
  effectiveness over a 3–12 month window). This changes what counts as a failure:
  under Type I a criterion with no mapped control is a design gap; under Type II a
  control that runs but is never evidenced fails regardless of implementation
  quality.

### 2. Load control catalogs

Read only the catalogs for the active frameworks:

- `references/soc2.md` — Trust Services Criteria
- `references/hipaa.md` — HIPAA Security Rule §164.3xx safeguards
- `references/pci-dss.md` — PCI-DSS v4.0 requirements

Always read `references/scope-boundaries.md` — it defines which controls are
**out of scope** for an automated audit and must be reported as human-attestation
items rather than as findings.

In `readiness` mode, additionally read `references/readiness-program.md` — the
risk register, phase plan, hard time constraints, cost model, and public
resources. It also **inverts** `scope-boundaries.md`: governance and evidence
controls become first-class findings there rather than out-of-scope notes.

### 3. Fan out control-domain agents

Spawn parallel agents (one Agent call per domain, all in one message). Each agent
receives: the target, the detected mode, and the relevant control rows from each
active catalog for its domain. Domains:

| # | Domain | Primary controls |
|---|--------|------------------|
| 1 | Encryption & key management | At-rest / in-transit / key rotation |
| 2 | Access control & authentication | AuthZ, MFA, least privilege, session |
| 3 | Audit logging & monitoring | Tamper-evident logs, alerting, retention |
| 4 | Data classification & retention | PHI/PII/CHD identification, retention, disposal |
| 5 | Network & transmission security | TLS, segmentation, firewall/network policy |
| 6 | Secrets & credential management | Hardcoded secrets, vaulting, exposure |
| 7 | Vulnerability & dependency management | CVEs, patching, SCA |
| 8 | Availability & resilience | Backup, DR, redundancy |
| 9 | Change management & SDLC | Code review gates, CI controls, IaC review |
| 10 | Infrastructure & IaC posture | Cloud config hardening, IAM, public exposure |
| 11 | Governance, evidence & program controls | CC1–CC5/CC9, access-review evidence, policy stack, controls matrix, assertion & system description, endpoint posture — **`readiness` mode only** |

Domain 11 runs **only in `readiness` mode**. In every other mode its controls are
`program`-type and route to Out of Scope instead — see the first Common Mistake.

Skip a domain only if it is structurally impossible for the detected mode (e.g.
domain 8 availability for a `design` review of a doc that does not cover it — but
note its absence as an Info finding).

In `readiness` mode, one domain-11 check has no per-domain home and must run in
the skill context: **map every existing control to CC1–CC9 and flag any series
with zero entries.** Engineering-led programs reliably over-index on CC6/CC7/CC8
and leave governance series empty, and an empty series is a design gap that fails
at Type I.

Each agent must return findings in the **Finding schema** below and must not
invent control failures — every finding cites a concrete control ID and evidence.

### 4. Validate before reporting

Per the user's standing rule, **every Critical and High finding must be verified
in the main (skill) context** before it lands in the report. Re-read the cited
evidence (`file:line`, config block, or doc passage) and confirm the control
genuinely fails. Demote or drop anything that does not survive verification.

### 5. Assemble the report

Use the **Report template** below. Deduplicate findings that multiple agents
raised against the same evidence; keep the highest severity. Sort by severity.

## Finding schema

Each finding is a row with these fields:

```
- ID:          <CONTROL-ID> (e.g. SOC2-CC6.1, HIPAA-164.312(a)(1), PCI-3.5.1)
  Title:       <one line>
  Severity:    Critical | High | Medium | Low | Info
  Mode:        code | design | iac | runtime | readiness
  Evidence:    <file:line | config block | doc passage> — quoted, concrete
  Why:         <how this fails or weakens the control>
  Remediation: <specific, actionable fix>
  Confidence:  <1-100> — <one-line justification>
```

In `readiness` mode, two fields change and two are added:

```
  Evidence:    <the answer to the discovery question, or the artifact that is absent>
  Status:      absent | present but unevidenced | present and evidenced
  Discovery:   <the question asked or the check run to establish this>
  Cost:        <consequence of leaving it — exception, qualified opinion, window restart>
```

`Status` matters because "no control" and "control with no retained evidence" look
identical in a report and have different fixes. `Cost` is what makes the finding
legible to a decision-maker; without it the report reads as a chore list.

## Report template

```markdown
# Compliance Review — <target>

**Frameworks:** <soc2 / hipaa / pci-dss>   **Mode:** <code/design/iac/runtime/readiness>
**TSC categories:** <Security + …>   **Report type:** <Type I / Type II>  *(soc2 only)*
**Date:** <date>   **Scope:** <what was and was not examined>

## Summary
<2-3 sentences: posture, count by severity, the single biggest risk>

| Severity | Count |
|----------|-------|
| Critical | n |
| High | n |
| Medium | n |
| Low | n |

## Findings
<findings, sorted by severity, in the Finding schema>

## Out of Scope — Human Attestation Required
<controls from scope-boundaries.md relevant to the active frameworks that an
automated audit cannot verify — policies, BAAs, training, vendor management,
physical security. List each with its control ID and who must attest.>

## Coverage Notes
<domains skipped and why; data the audit could not reach; black-box walls>
```

### Additional sections in `readiness` mode

Append these after **Findings**, drawn from `references/readiness-program.md`:

```markdown
## CC Series Coverage
<CC1–CC9 with control counts; any zero-entry series called out as a design gap>

## Phase Plan
<dependency-ordered phases with an exit criterion each. Phase 2 — the evidence
machine — must complete BEFORE the Type II observation window opens.>

## Hard Time Constraints
<the constraints that cannot be compressed: observation window, quarterly
cadences, published end-to-end ranges. No invented calendar dates.>

## Cost Model
<auditor fee ranges, platform, pen test, readiness assessment, engineering time,
and the cost of delay>
```

In readiness mode the **Out of Scope** section shrinks to what the reviewer could
not reach (e.g. no access to the policy repository). Governance and evidence
controls belong in Findings — their absence is the subject of the review.

## Runtime mode caveat

`runtime` mode requires live cloud/observability access (AWS, GCP, Datadog) via
MCP tooling. For Podium, infrastructure is largely a black box owned by SRE /
platform. If the required MCP tools are unavailable, do **not** guess at live
config — report runtime controls as "unverifiable from this context; requires
SRE/platform" in the Coverage Notes section and audit the other modes normally.

## Common Mistakes

### ❌ Reporting human-attestation controls as findings

**Problem:** Flagging "no documented incident-response policy" or "no signed BAA"
as a Critical code finding.

**Why it's wrong:** An automated audit cannot see policies, contracts, training
records, or physical security. Reporting their absence as a finding produces false
failures and, worse, false *comfort* that the skill covered them.

**Fix:** Route every such control to the **Out of Scope — Human Attestation
Required** section with its control ID and the owner who must attest.

**Exception:** `readiness` mode inverts this. There, program controls *are* the
subject of the review and their absence is a first-class finding.

### ❌ Scoring a control clean because it works

**Problem:** "Access reviews happen quarterly — CC6.3 satisfied." "Backups are
configured — A1.2 satisfied."

**Why it's wrong:** A Type II examination tests evidence, not intent. A review
that happens and is never saved, and a backup that is never restored from, produce
nothing an auditor can sample. These are the two most common first-audit
exceptions precisely because they *feel* handled.

**Fix:** Ask what artifact the control leaves behind and who owns it. Report
**"present but unevidenced"** as a distinct status — and note that missing evidence
cannot be backfilled into an observation window, so the consequence is a restarted
window, not a quick fix.

### ❌ Treating a secret as remediated because history was scrubbed

**Problem:** A committed credential is rewritten out of git history and the finding
is closed.

**Why it's wrong:** History scrubbing is cosmetic. The credential was exposed and
is still valid — anyone who cloned the repo before the rewrite still holds it.

**Fix:** **Rotation is the fix.** Report "scrubbed but not rotated" as an
unremediated Critical. And scan the **full history**, not just HEAD — including
configs, IaC, CI variables, and seed files.

### ❌ Accepting a policy at face value

**Problem:** The policy stack exists and is exec-approved, so CC5.3 passes.

**Why it's wrong:** Auditors test the gap between what policies say and what the
team actually does. A policy that contradicts practice is **worse than no policy**
— it documents a control failure in the organization's own words.

**Fix:** Where a policy is verifiable against the target, verify it. Where it is
not, say so and route it to attestation rather than marking it satisfied. Templates
produce a draft, not a program.

### ❌ Findings without a control ID

**Problem:** "This code logs passwords — bad!" with no framework reference.

**Why it's wrong:** A compliance finding is only actionable if it maps to a
specific control an auditor will test. Generic security advice belongs in a
security review, not a compliance review.

**Fix:** Every finding cites a concrete control ID (`SOC2-CC6.1`,
`HIPAA-164.312(b)`, `PCI-3.5.1`). If no control maps, it is not a compliance
finding — drop it or move it to Coverage Notes.

### ❌ Inferring framework scope silently

**Problem:** Auditing a payments repo against SOC 2 only because the user did not
specify, missing all PCI-DSS card-data controls.

**Why it's wrong:** The framework set determines the entire control surface. A
silent wrong guess produces a confident, incomplete report.

**Fix:** When frameworks are not specified, infer from the target, **state the
inferred set explicitly**, and let the user redirect before the fan-out. For SOC 2
this extends to TSC categories: silently dropping Processing Integrity on a
reporting or analytics product omits the criteria covering the product's core
promise.

### ❌ Overclaiming that a control has no bypass

**Problem:** Reporting access logging or tenant isolation as complete on the
strength of an application-layer check.

**Why it's wrong:** "No possible bypass" gets tested — by the auditor and the pen
tester. They probe break-glass paths, backups and snapshots, and infra-level roles
that read around application controls. An overclaim that gets corrected becomes a
credibility finding, which is worse than the original gap.

**Fix:** State the scope actually verified — "no bypass within the application
path" — and route infra-level and break-glass paths to Coverage Notes as
separately-gated, unverified-here.

### ❌ Skipping Critical/High verification

**Problem:** Passing agent findings straight into the report.

**Why it's wrong:** Sub-agents over-report. An unverified Critical compliance
finding in a deliverable is a credibility and remediation-cost risk.

**Fix:** Re-read the cited evidence for every Critical and High finding in the
skill context before it ships. Demote or drop what does not survive.

## Notes

- This skill runs in a forked context — the multi-agent fan-out stays out of the
  main conversation; only the final report returns.
- Catalogs are versioned data. SOC 2 has no fixed control numbers (TSC are
  criteria, not a checklist); the catalog uses the common `CCx.x` mapping.
- In `code`/`design`/`iac`/`runtime` the skill audits *technical* controls. It is
  one input to a compliance program, not a substitute for a SOC 2 Type II audit or
  a HIPAA risk assessment.
- `readiness` mode produces a gap assessment and a phase plan — **not an audit
  opinion, and not a substitute for a formal readiness assessment or mock audit.**
  Cost figures in `references/readiness-program.md` are point-in-time reference
  data; quotes move yearly, so treat them as a sizing aid and get live numbers.
- Where a control is automated and preventive (a merge-blocking CI gate, a
  deny-by-default scrub), say so in the finding. Auditors weight preventive
  controls above detective ones and sample them less aggressively, which lowers
  audit cost directly — that is worth surfacing in a remediation recommendation.
