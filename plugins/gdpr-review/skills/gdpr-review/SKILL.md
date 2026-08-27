---
name: gdpr-review
description: Use when auditing a codebase, design doc, IaC, or data-flow map for GDPR compliance - lawful basis, consent validity, data subject rights (access/erasure/portability), retention and deletion, cross-border transfers, processor/DPA posture, privacy by design, breach readiness - OR when assessing organizational GDPR readiness (RoPA, DPIA, DPO, accountability). Triggers - /gdpr-review, GDPR audit, GDPR review, are we GDPR compliant, privacy review, data protection review, right to be forgotten, data deletion audit, erasure audit, consent flow review, PII handling review, DSAR, DPIA, RoPA, EU user data, cross-border transfer check, Schrems, SCCs. Auto-detects input mode, builds a personal-data inventory first, fans out parallel domain agents, and produces structured findings with GDPR article IDs, severity, evidence, remediation, confidence, plus an out-of-scope section for legal-attestation items. Analysis aid, not legal advice.
context: fork
---

# GDPR Review

## Overview

Multi-agent GDPR auditor. Auto-detects the input mode (code/config repo, design
doc, IaC, data-flow map, or organizational readiness), builds a **personal-data
inventory** as the audit's spine, fans out parallel domain agents, and produces
structured findings keyed to GDPR article IDs with severity, evidence,
remediation, confidence — plus an explicit out-of-scope section for obligations
that only a human (usually legal or a DPO) can attest to.

This skill is an analysis aid, **not legal advice** and not a substitute for
counsel, a DPIA, or a supervisory-authority determination.

## Quick Reference

| Input | Detected mode | What the audit checks |
|-------|---------------|-----------------------|
| Repo path / git diff / branch | `code` | PII inventory, deletion paths, consent enforcement, logs, DSAR plumbing, vendor SDK flows |
| `.md` ADR or PRD (path or pasted) | `design` | Whether the *design* names lawful basis, retention, DSR support, transfer mechanism before build |
| `*.tf` / Helm / k8s manifests / cloud config | `iac` | Encryption, region pinning, backup lifecycle, log retention, IAM on PII stores |
| Data-flow diagram / vendor list / "where does our data go" | `dataflow` | Vendor-by-vendor: DPA needed, transfer mechanism, deletion propagation, documented vs actual flows |
| "are we ready" / "are we compliant" org-level | `readiness` | Whether the **organization** can face a supervisory authority — RoPA, DPIAs, DPO, breach register, notices, program evidence |

| Severity | Meaning |
|----------|---------|
| Critical | Active violation with enforcement exposure (special-category data unprotected, no lawful basis for live processing, transfers with no mechanism, no erasure path); in `readiness`, a gap a DPA inquiry would immediately surface |
| High | Gap likely to fail a DPA inquiry or turn a complaint into a finding; erasure/DSAR paths that miss data stores |
| Medium | Partial implementation; weak consent records; retention as policy but not code |
| Low | Hardening opportunity; minor deviation from EDPB guidance |
| Info | Observation; no action required |

**Enforcement-weighted priorities.** DPA fines cluster on: international
transfers, ad-tech lawful basis, dark-pattern consent, children's data, breach
handling, and processor-contract completeness. Weight these domains above
rarely-enforced areas when triaging.

## Workflow

### 1. Resolve scope

Determine the following before fanning out. Ask with **AskUserQuestion** only if
they cannot be inferred; otherwise state the inferences explicitly and let the
user redirect:

- **Target** — the path, diff, document, vendor list, or the organization itself.
- **Mode** — auto-detect per the Quick Reference table; state it.
- **Role** — controller, processor, or both. A processor's obligations are
  narrower (Art. 28, 30(2), 32, 33(2)); auditing a pure processor against
  controller duties produces false findings.
- **Territorial hook** — EU establishment (Art. 3(1)) vs targeting EU data
  subjects from outside (Art. 3(2)) vs possibly out of scope entirely. If GDPR
  plausibly does not apply, say so and confirm before auditing.
- **Special-category data** — is Art. 9 data (health, biometrics, orientation,
  religion, ethnicity, union membership, political opinions, genetic) present or
  inferable? This raises severity floors across every domain.
- **ePrivacy adjacency** — are cookies/trackers/electronic comms in scope? If the
  target has a web or mobile frontend, default **in** and run domain 7.

### 2. Build the personal-data inventory

**Before any domain agent runs**, build the inventory every other check diffs
against. In `code`/`iac` mode, scan schemas, migrations, ORM models, event
schemas, and IaC for PII-bearing fields and stores (patterns in
`references/minimization-and-retention.md`). In `design`/`dataflow` mode, extract
the inventory from the document. In `readiness` mode, ask for the RoPA and treat
its absence as a first-class finding.

The inventory table (system → store → field → category → special-category flag)
is passed to **every** domain agent. The highest-value findings are
**coverage diffs** against it:

- PII fields found **vs** fields covered by the deletion path
- PII fields found **vs** fields covered by the DSAR export
- PII stores found **vs** stores encrypted / region-pinned / TTL'd
- Vendors found in code **vs** the documented processor list

### 3. Load control catalogs

Read only the reference files for the domains in scope; always read
`references/scope-boundaries.md` — it defines which obligations are
out of scope for an automated audit and must be reported as attestation items,
not findings.

- `references/lawful-basis.md` — Art. 6/7/8/9
- `references/data-subject-rights.md` — Art. 12–23
- `references/minimization-and-retention.md` — Art. 5(1)(c)/(e), 17 mechanics, PII inventory patterns
- `references/security-and-breach.md` — Art. 25/32/33/34
- `references/transfers-and-processors.md` — Art. 28/44–49
- `references/tracking-and-consent-ux.md` — ePrivacy adjacency, dark patterns
- `references/accountability-program.md` — Art. 5(2)/30/35/37–39 (`readiness` mode)

In `readiness` mode, `accountability-program.md` **inverts**
`scope-boundaries.md`: program obligations become first-class findings there
rather than out-of-scope notes.

### 4. Fan out domain agents

Spawn parallel agents (one Agent call per domain, all in one message). Each agent
receives: the target, the detected mode and role, the personal-data inventory,
and its domain's control rows. Domains:

| # | Domain | Primary articles |
|---|--------|------------------|
| 1 | Lawful basis & consent validity | 6, 7, 8, 9 |
| 2 | Data subject rights implementation | 12–23 |
| 3 | Minimization & retention/erasure mechanics | 5(1)(c), 5(1)(e), 17 |
| 4 | Security of processing & privacy by design | 25, 32 |
| 5 | Transfers & processors | 28, 44–49 |
| 6 | Logging, PII leakage & breach readiness | 32(1), 33, 34 |
| 7 | Tracking & consent UX | ePrivacy Art. 5(3), 7, 21(2)-(3) |
| 8 | Accountability program | 5(2), 30, 35, 37–39 — **`readiness` mode only** |

Domain 8 runs **only in `readiness` mode**. In every other mode its controls are
`program`-type and route to Out of Scope — see the first Common Mistake.

Skip a domain only if structurally impossible for the detected mode (e.g. domain
7 for a backend-only service with no frontend — but note its absence as an Info
finding if the service emits data to analytics anyway).

Each agent must return findings in the **Finding schema** below and must not
invent violations — every finding cites a concrete article ID and evidence.

### 5. Validate before reporting

**Every Critical and High finding must be verified in the main (skill) context**
before it lands in the report. Re-read the cited evidence (`file:line`, config
block, doc passage) and confirm the gap genuinely exists. Demote or drop anything
that does not survive verification. Sub-agents over-report.

### 6. Assemble the report

Use the **Report template** below. Deduplicate findings multiple agents raised
against the same evidence; keep the highest severity. Sort by severity.

## Finding schema

```
- ID:          GDPR-<article>(<paragraph/point>) (e.g. GDPR-6.1, GDPR-17.1, GDPR-32.1a, EPRIV-5.3)
  Title:       <one line>
  Severity:    Critical | High | Medium | Low | Info
  Mode:        code | design | iac | dataflow | readiness
  Evidence:    <file:line | config block | doc passage | inventory diff> — quoted, concrete
  Why:         <how this violates or weakens the obligation>
  Remediation: <specific, actionable fix>
  Confidence:  <1-100> — <one-line justification>
```

In `readiness` mode, add:

```
  Status:      absent | present but unevidenced | present and evidenced
  Cost:        <consequence — DPA inquiry exposure, complaint escalation, fine tier (Art. 83: up to €20M/4% for basis/rights/transfers; €10M/2% for controller-duty articles)>
```

## Report template

```markdown
# GDPR Review — <target>

**Mode:** <code/design/iac/dataflow/readiness>   **Role:** <controller/processor/both>
**Territorial hook:** <Art. 3(1) / 3(2) / confirmed with user>
**Special-category data:** <present / not found / inferable via …>
**Date:** <date>   **Scope:** <what was and was not examined>

## Summary
<2-3 sentences: posture, count by severity, the single biggest exposure>

| Severity | Count |
|----------|-------|
| Critical | n |
| High | n |
| Medium | n |
| Low | n |

## Personal-Data Inventory
<the inventory table, with special-category rows flagged — this is the audit's
spine and belongs in the deliverable>

## Findings
<findings, sorted by severity, in the Finding schema>

## Out of Scope — Legal / Attestation Required
<obligations from scope-boundaries.md an automated audit cannot verify — signed
DPAs, notice adequacy, LIA balancing tests, DPO independence, member-state
derogations. List each with its article ID and who must attest.>

## Coverage Notes
<domains skipped and why; stores the audit could not reach; time-sensitive items
(adequacy status, pending legislation) that were verified live or flagged stale>
```

## Time-sensitive law — verify live, never from memory

Some GDPR facts move. **Do not assert these from the catalogs or from training
data** — run a web search at review time when a finding depends on them, and say
in the finding that the status was checked:

- **EU–US Data Privacy Framework status** and the certification status of any
  specific US vendor (dataprivacyframework.gov).
- **Adequacy decisions** for any third country.
- **Pending legislation** — the Omnibus IV RoPA-threshold change and the Digital
  Omnibus (cookie consent into GDPR, legitimate interest for AI training) were
  *proposals* as of the catalog date; check whether they are now law.
- **Fine amounts and enforcement precedents** cited to justify severity.

## Common Mistakes

### ❌ Reporting legal-attestation obligations as code findings

**Problem:** Flagging "no signed DPA with vendor X" or "privacy notice is not
legally adequate" as a Critical code finding.

**Why it's wrong:** An automated audit cannot see contracts, the legal adequacy
of notice text, or whether a balancing test was genuinely performed. Reporting
these as findings produces false failures and false *comfort* that the skill
covered them.

**Fix:** Route to **Out of Scope — Legal / Attestation Required** with the
article ID and owner. What the audit *can* verify: whether the vendor exists in
code but not on the documented processor list — that diff is a real finding.

**Exception:** `readiness` mode inverts this — there, program obligations are
the subject of the review.

### ❌ "A delete endpoint exists" scored as Art. 17 satisfied

**Problem:** Finding `DELETE /account` and marking erasure implemented.

**Why it's wrong:** Erasure must be verifiable and irreversible across **every**
copy: child tables, search indexes, caches, analytics events, warehouses, blob
storage, vector DBs, logs, backups, and third-party processors. A soft delete
with no stage-2 purge, or a local delete while events keep flowing to vendors,
is functional deletion, not erasure.

**Fix:** Diff the deletion path's coverage against the personal-data inventory.
Every uncovered store is its own finding. Backups need bounded retention plus
deletion replay on restore, or crypto-shredding.

### ❌ Consent stored ≠ consent valid

**Problem:** A `marketing_opt_in` boolean exists, so Art. 7 passes.

**Why it's wrong:** Valid consent needs who/when/what-version/which-purposes
records, granularity per purpose, affirmative action (no pre-ticked defaults),
withdrawal as easy as giving, and **enforcement at point of use** — a flag that
is stored but never checked before firing analytics is decorative.

**Fix:** Trace the flag from storage to every read site. Consent recorded but
not enforced, not versioned, or not granular are three distinct findings.

### ❌ Pseudonymized treated as anonymized

**Problem:** `sha256(email)` in the analytics pipeline described as "anonymized,
so GDPR doesn't apply."

**Why it's wrong:** Hashing a predictable identifier is reversible by dictionary
attack; pseudonymized data is still personal data and every obligation still
applies. True anonymization requires irreversibility including against the
controller's own auxiliary data, and quasi-identifier combinations (zip + DOB +
gender) re-identify.

**Fix:** Classify hashed/tokenized identifiers as pseudonymized (in scope).
Check key/vault separation from the data it protects. Flag "anonymized" exports
that retain user-level rows with quasi-identifiers.

### ❌ Legitimate interest asserted without a balancing-test artifact

**Problem:** "We process under legitimate interest" accepted at face value.

**Why it's wrong:** Art. 6(1)(f) requires a documented three-part assessment
(purpose, necessity, balancing) performed *before* processing. Regulators have
rejected LI for behavioral advertising; contract necessity is read narrowly.

**Fix:** For each LI-based purpose, ask for the LIA artifact. Its existence and
timing route to attestation; the *plausibility* of LI for the observed purpose
(e.g. ad profiling) is a real finding when precedent contradicts it.

### ❌ Silently assuming controller role or GDPR applicability

**Problem:** Auditing a B2B data processor against controller duties, or a
US-only product against GDPR at all, because the user didn't specify.

**Why it's wrong:** Role and territorial scope determine the entire obligation
surface. A silent wrong guess produces a confident, wrong report.

**Fix:** Infer role and territorial hook from the target, **state both
explicitly**, and let the user redirect before the fan-out.

### ❌ Citing adequacy status or fines from memory

**Problem:** "Transfers to the US are fine under the DPF" or "this risks a €20M
fine like <case>" asserted from training data.

**Why it's wrong:** Adequacy decisions get invalidated (Schrems I, II; a DPF
appeal is a standing risk), vendors lapse from certification, and pending
omnibus legislation changes obligations. Stale law in a deliverable is worse
than no citation.

**Fix:** Verify live per the **Time-sensitive law** section, and record in the
finding that the check was done and when.

### ❌ Skipping Critical/High verification

**Problem:** Passing agent findings straight into the report.

**Why it's wrong:** Sub-agents over-report, and an unverified Critical GDPR
finding in a deliverable is a credibility and remediation-cost risk.

**Fix:** Re-read the cited evidence for every Critical and High finding in the
skill context before it ships. Demote or drop what does not survive.

## Notes

- This skill runs in a forked context — the fan-out stays out of the main
  conversation; only the final report returns.
- Output is one input to a privacy program — not legal advice, not a DPIA, and
  not a substitute for counsel or a supervisory-authority determination. Say so
  in the report when the audience may not know.
- Member-state derogations vary (consent age floor 13–16, employment data
  rules); flag where a finding depends on which member state's law applies.
- Where a control is automated and preventive (a CI gate blocking unclassified
  PII columns, a merge-blocking secret scan, consent-gated SDK init), say so in
  the finding — preventive controls are worth surfacing in remediation
  recommendations because they close the gap class, not the instance.
