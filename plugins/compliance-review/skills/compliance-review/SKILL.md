---
name: compliance-review
description: Use when auditing a target for regulatory compliance against SOC 2, HIPAA Security Rule, or PCI-DSS - reviewing code/config repos, ADRs/PRDs, IaC posture, or live cloud state for control gaps. Triggers - /compliance-review, compliance audit, SOC 2 review, HIPAA review, PCI-DSS review, is this compliant, check compliance, audit against controls, PHI or CHD handling review. Auto-detects input mode, fans out parallel control-domain agents, and produces structured findings with control IDs, severity, evidence, remediation, confidence, plus an out-of-scope section for human-attestation controls.
context: fork
---

# Compliance Review

## Overview

Multi-agent compliance auditor that reviews a target against SOC 2, HIPAA Security
Rule, and/or PCI-DSS control catalogs. Auto-detects the input mode (code/config
repo, ADR/PRD, IaC posture, or live cloud state), fans out parallel control-domain
agents, and produces structured findings with control IDs, severity, evidence,
remediation, confidence, and an explicit out-of-scope section for controls that can
only be satisfied by human attestation.

## Quick Reference

| Input | Detected mode | What the audit checks |
|-------|---------------|-----------------------|
| Repo path / git diff / branch | `code` | Encryption, access control, logging, secrets, dep CVEs, input handling |
| `.md` ADR or PRD (path or pasted) | `design` | Whether the *design* names required controls before build |
| `*.tf` / Helm charts / k8s manifests | `iac` | Encryption settings, network policy, retention, IAM posture |
| "live" / cloud / "check prod" | `runtime` | Actual cloud config via MCP — **see Runtime caveat below** |

| Severity | Meaning |
|----------|---------|
| Critical | Active control failure with regulatory exposure (unencrypted PHI/CHD, no audit trail) |
| High | Control gap likely to fail an audit; exploitable weakness |
| Medium | Partial control; weak configuration; missing defense-in-depth |
| Low | Hardening opportunity; minor deviation from best practice |
| Info | Observation; no action required |

## Workflow

### 1. Resolve scope

Determine three things before fanning out. Ask the user with the host's
structured clarification mechanism when available, and only if they cannot be
inferred:

- **Target** — the path, diff, branch, document, or "live" indicator.
- **Frameworks** — one or more of `soc2`, `hipaa`, `pci-dss`. If the user did not
  say, infer from the target (PHI handling → hipaa; payment/card code → pci-dss;
  SaaS infra generally → soc2) and state the inferred set.
- **Mode** — auto-detect per the Quick Reference table; state the detected mode.

### 2. Load control catalogs

Read only the catalogs for the active frameworks:

- `references/soc2.md` — Trust Services Criteria
- `references/hipaa.md` — HIPAA Security Rule §164.3xx safeguards
- `references/pci-dss.md` — PCI-DSS v4.0 requirements

Always read `references/scope-boundaries.md` — it defines which controls are
**out of scope** for an automated audit and must be reported as human-attestation
items rather than as findings.

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

Skip a domain only if it is structurally impossible for the detected mode (e.g.
domain 8 availability for a `design` review of a doc that does not cover it — but
note its absence as an Info finding).

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
  Mode:        code | design | iac | runtime
  Evidence:    <file:line | config block | doc passage> — quoted, concrete
  Why:         <how this fails or weakens the control>
  Remediation: <specific, actionable fix>
  Confidence:  <1-100> — <one-line justification>
```

## Report template

```markdown
# Compliance Review — <target>

**Frameworks:** <soc2 / hipaa / pci-dss>   **Mode:** <code/design/iac/runtime>
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

## Runtime mode caveat

`runtime` mode requires live cloud/observability access (AWS, GCP, Datadog) via
MCP tooling. If the required MCP tools are unavailable, do **not** guess at live
config — report runtime controls as "unverifiable from this context; requires
live infrastructure access" in the Coverage Notes section and audit the other
modes normally.

## Common Mistakes

### ❌ Reporting human-attestation controls as findings

**Problem:** Flagging "no documented incident-response policy" or "no signed BAA"
as a Critical code finding.

**Why it's wrong:** An automated audit cannot see policies, contracts, training
records, or physical security. Reporting their absence as a finding produces false
failures and, worse, false *comfort* that the skill covered them.

**Fix:** Route every such control to the **Out of Scope — Human Attestation
Required** section with its control ID and the owner who must attest.

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
inferred set explicitly**, and let the user redirect before the fan-out.

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
- The skill audits *technical* controls. It is one input to a compliance program,
  not a substitute for a SOC 2 Type II audit or a HIPAA risk assessment.
