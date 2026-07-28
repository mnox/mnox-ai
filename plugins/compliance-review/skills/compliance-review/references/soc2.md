# SOC 2 Control Catalog (Trust Services Criteria)

SOC 2 has no fixed control numbers — the TSC are *criteria*, and each auditor maps
controls to them. This catalog uses the widely-adopted `CCx.x` Common Criteria
mapping plus the optional Availability (A), Confidentiality (C), and Processing
Integrity (PI) categories.

Columns: **ID** · **Criterion** · **Automated signal** (what an audit of code/IaC
can verify) · **Domain** (maps to a control-domain agent) · **Type**.

**Control type** decides where a gap is reported:

- `technical` — verifiable from code, IaC, or cloud config. Files as a **finding**.
- `program` — a governance, evidence, or process control. Files in **Out of Scope —
  Human Attestation Required** in `code`/`design`/`iac`/`runtime` modes, and as a
  **first-class finding in `readiness` mode**, where its absence is the whole point
  of the review.

Never file a `program` control as a code finding outside readiness mode. See
`references/scope-boundaries.md`.

## Category selection

**Security (Common Criteria) is mandatory.** All nine CC series are required for
any valid report — a program cannot pass by covering only the technical ones.

Optional categories, selected by what the system actually promises:

| Category | Select when |
|----------|-------------|
| Availability (A) | Uptime/recovery is a customer commitment |
| Confidentiality (C) | The system holds customer data under confidentiality obligations |
| Processing Integrity (PI) | **Output correctness is the product** — reporting, analytics, billing, data transformation, ML scoring |
| Privacy (P) | The system handles personal information under a privacy notice |

Do **not** default Processing Integrity to out-of-scope. For a data, reporting, or
analytics product, correctness *is* the deliverable and PI belongs in scope. State
the selected category set explicitly before the fan-out and let the user redirect.

## Type I vs Type II — what the mode implies

- **Type I** attests control *design* at a point in time. A criterion with zero
  controls mapped to it is a **design gap**, which fails at Type I — not merely at
  Type II.
- **Type II** attests controls *operated effectively* over a 3–12 month observation
  window. It is evidence-driven: a control that runs but is never recorded produces
  nothing to test.
- **A control with no named owner fails silently**, because no evidence accumulates
  for it and nobody notices until fieldwork.
- **Evidence cannot be backfilled.** A gap discovered mid-window cannot be
  retroactively papered over; the window restarts. Treat any missing-evidence
  finding as schedule risk, not just a control gap.

## Common Criteria — Control Environment & Governance (CC1–CC5)

Predominantly organizational, and the series engineering-led programs
systematically under-build while over-indexing on CC6/CC7/CC8.

| ID | Criterion | Automated signal | Domain | Type |
|----|-----------|------------------|--------|------|
| SOC2-CC1.1 | Commitment to integrity and ethical values | Code of conduct exists with acknowledgment records | 11 | program |
| SOC2-CC1.2 | Board or equivalent oversight independent of management | Documented oversight body or, for a small company, a documented equivalent oversight cadence | 11 | program |
| SOC2-CC1.3 | Org structure, reporting lines, authority defined | Documented org structure and authority matrix | 11 | program |
| SOC2-CC1.4 | Competence — hiring, training, development | Security awareness training delivered and acknowledgments recorded | 11 | program |
| SOC2-CC1.5 | Individuals held accountable for control responsibilities | Controls matrix assigns a named owner per control | 11 | program |
| SOC2-CC2.1 | Quality information supports control function | Evidence sources identified per control and actually produce output | 11 | program |
| SOC2-CC2.2 | Internal communication of security commitments | Documented internal security communication path | 11 | program |
| SOC2-CC2.3 | External communication with users and stakeholders | Published security contact / disclosure path; commitments communicated to customers | 11 | program |
| SOC2-CC3.2 | Risks to objectives are identified | Secrets not committed; sensitive data classified | 4,6 | technical |
| SOC2-CC3.2-RA | Documented risk assessment performed | Dated risk assessment covering the current period | 11 | program |
| SOC2-CC4.1 | Ongoing evaluation of whether controls are functioning | A monitoring routine that surfaces control failures **between** audits, not at fieldwork | 11 | program |
| SOC2-CC4.2 | Control deficiencies communicated and remediated | Tracked remediation record for identified deficiencies | 11 | program |
| SOC2-CC5.1 | Control activities selected to mitigate risk | Controls matrix maps each in-scope criterion to a control statement | 11 | program |
| SOC2-CC5.2 | Technology controls support objectives | Automated/preventive controls exist where feasible | 9,11 | program |
| SOC2-CC5.3 | Policies and procedures deployed | Core policy stack exec-approved, dated, acknowledged | 11 | program |

**Audit rule for this series: look for zero-entry series.** Map existing controls
to CC1–CC9 and flag any series with no controls at all. Governance-heavy series
are where the blanks show up, and a CC-series with no controls is a **design gap**.

CC4 in particular favors monitoring that catches failures quickly — reliance on
manual periodic review is a common reason teams that pass Type I struggle on
their first Type II.

## Common Criteria — Logical & Physical Access (CC6)

| ID | Criterion | Automated signal | Domain | Type |
|----|-----------|------------------|--------|------|
| SOC2-CC6.1 | Logical access controls restrict access to assets | AuthZ enforced on protected routes/resources; no broken object-level auth; tenant isolation | 2 | technical |
| SOC2-CC6.2 | Registration/authorization of users before access | User provisioning gated; no default/shared accounts; role assignment on creation | 2 | technical |
| SOC2-CC6.3 | Access modified/removed on role change or termination | Deprovisioning path exists; no orphaned credentials; role changes revoke access | 2 | technical |
| SOC2-CC6.3-LP | Least privilege — granted access matches exercised access | Diff declared/granted permissions against what the code actually uses; flag blanket grants | 2,10 | technical |
| SOC2-CC6.3-AR | **Access reviews performed on a cadence and evidenced** | Quarterly review with a named owner; exported/timestamped evidence retained | 11 | program |
| SOC2-CC6.6 | Boundary protection against external threats | TLS enforced; no public exposure of internal services; network policy/firewall rules | 5,10 | technical |
| SOC2-CC6.7 | Data transmission is protected | TLS ≥1.2 for all data in transit; no plaintext protocols; cert validation not disabled | 1,5 | technical |
| SOC2-CC6.8 | Controls prevent/detect unauthorized software | Dependency provenance; lockfiles; no unpinned/unverified packages | 7,9 | technical |
| SOC2-CC6.8-EP | Endpoint posture for in-scope workstations | Disk encryption, screen lock, MDM enrollment or documented+attested standards | 11 | program |

Endpoint posture stays in scope even for a very small team — a handful of laptops
is still a handful of laptops, and it is an embarrassing control to fail at n=4.

## Common Criteria — System Operations (CC7)

| ID | Criterion | Automated signal | Domain | Type |
|----|-----------|------------------|--------|------|
| SOC2-CC7.1 | Detect configuration changes / vulnerabilities | SCA scanning in CI as a **blocking** gate; dependency CVE gating; lockfiles present; transitive deps inventoried | 7 | technical |
| SOC2-CC7.1-SLA | Documented patch SLA and review cadence | Remediation thresholds defined **and met**; quarterly dependency review evidenced | 7,11 | program |
| SOC2-CC7.2 | Monitor system components for anomalies | Logging of security-relevant events; alerting wired | 3 | technical |
| SOC2-CC7.2-ATTR | **Data access is attributable to an identity** | Centralized access logging with identity attribution; no shared/service-account blind spots; standing prod access converted to logged break-glass | 3,2 | technical |
| SOC2-CC7.3 | Evaluate security events | Errors/auth failures emitted to a monitored sink | 3 | technical |
| SOC2-CC7.4 | Respond to identified security incidents | Incident hooks (alerts page someone) — *process is attestation* | 3 | technical |
| SOC2-CC7.4-IR | **Incident response plan exercised** | Dated tabletop record with named participants and findings | 11 | program |

An unattributable access path is not only a control gap: it removes the ability to
answer "what did the attacker touch," which converts a contained incident into a
full-disclosure event.

Patch-SLA thresholds are a policy choice you define — and then must actually meet,
because the published SLA becomes the control the auditor tests.

## Common Criteria — Change Management (CC8)

| ID | Criterion | Automated signal | Domain | Type |
|----|-----------|------------------|--------|------|
| SOC2-CC8.1 | Changes are authorized, designed, tested, approved | Branch protection; required PR review; required CI status checks before merge/deploy | 9 | technical |
| SOC2-CC8.1-SEG | Author is not the sole approver | Review settings forbid self-approval; admin bypass and force-push restricted | 9 | technical |
| SOC2-CC8.1-TRACE | Change traceable request → review → test → deploy | PR template links change to a tracked issue; deploy record exists | 9 | technical |

The classic first-audit exception here is **approvals living in chat instead of a
tracked workflow**. Auditors require a request, peer review, test, and deploy
record. Enforcement is cheap; the cost is discipline. Where it is missing, the
auditor demands compensating evidence sampled at much higher volume — which is
billable hours.

## Common Criteria — Risk Mitigation & Vendor Management (CC9)

| ID | Criterion | Automated signal | Domain | Type |
|----|-----------|------------------|--------|------|
| SOC2-CC9.1 | Risk mitigation activities for business disruption | Documented mitigations tied to assessed risks | 8,11 | program |
| SOC2-CC9.2 | Vendor and business-partner risk managed | Vendor inventory maintained; subprocessor SOC 2 / ISO reports collected and current | 11 | program |

A new third-party integration in the reviewed target **creates** a CC9 attestation
item. Call that out explicitly so the human knows the change added one.

## Encryption support

| ID | Criterion | Automated signal | Domain | Type |
|----|-----------|------------------|--------|------|
| SOC2-CC6.1-ENC | Encryption supports access restriction | Data at rest encrypted (DB, object storage, volumes); KMS-managed keys | 1,10 | technical |

## Availability (A) — optional category

| ID | Criterion | Automated signal | Domain | Type |
|----|-----------|------------------|--------|------|
| SOC2-A1.2 | Environmental protections, backups, recovery infrastructure | Automated backups configured; retention set; restore path exists | 8 | technical |
| SOC2-A1.3 | Recovery plan is tested | DR config present — *test execution is attestation* | 8 | technical |
| SOC2-A1.3-DR | **Restore actually performed and timed** | Dated restore drill record with measured duration | 11 | program |

Backups are not restores. Auditors request *tested* restores and dated tabletop
records — an untested plan fails the criterion. Together with CC7.4-IR these are
the cheapest exceptions in the whole program to prevent.

## Confidentiality (C) — optional category

| ID | Criterion | Automated signal | Domain | Type |
|----|-----------|------------------|--------|------|
| SOC2-C1.1 | Confidential information is identified and protected | Sensitive fields classified, encrypted, access-scoped | 1,4 | technical |
| SOC2-C1.1-LOG | **Confidential data does not leak into logs** | Structured logging with allowlisted fields (deny-by-default); no raw object dumps, request bodies, or headers; log-content test in CI | 3,4 | technical |
| SOC2-C1.1-FIX | **Non-production data contains no real identities** | Fixtures/seeders/test data generated or reserved-domain (RFC 2606 `example.com`); no prod-derived records | 4,6 | technical |
| SOC2-C1.1-DBG | Engineers have no standing need to read production data | Prod reads gated behind logged break-glass; dev/staging data provenance is synthetic or anonymized | 2,4 | technical |
| SOC2-C1.2 | Confidential information is disposed of | Retention/deletion logic for confidential data | 4 | technical |

**C1.1-LOG:** logging is a classic uncontrolled egress path — data is replicated
into a system with weaker access controls than the source. Log retention means the
exposure is historical and growing, so remediation cost compounds monthly.

**C1.1-FIX:** applies to employee identities as well as customer data. Real
routable addresses in fixtures can fire actual mail or leak into logs, and their
presence signals absent fixture-provenance discipline — which invites broader
"what else leaked in?" sampling. One rule (generated or reserved-domain identities
everywhere, enforced by the same CI gate as C1.1-LOG) removes the distinction.

**C1.1-DBG:** the strongest posture is removing the *reason* to touch production
data, not restricting it — synthetic seeders rich enough to reproduce
customer-shaped bugs. Where customer data in dev is unavoidable, an anonymization
pipeline plus logged break-glass is the fallback. Contract exposure compounds the
control gap here, since customer DPAs generally prohibit it outright.

## Processing Integrity (PI) — optional category

In scope whenever output correctness is the product.

| ID | Criterion | Automated signal | Domain | Type |
|----|-----------|------------------|--------|------|
| SOC2-PI1.1 | Information about processing objectives is available | Documented data lineage / definitions of computed outputs | 4 | program |
| SOC2-PI1.2 | Inputs are complete, accurate, authorized | Input validation, schema enforcement, source authentication | 4 | technical |
| SOC2-PI1.3 | Processing is complete, accurate, timely, authorized | Transformation tests, reconciliation checks, row-count/checksum assertions, job-failure alerting | 4,3 | technical |
| SOC2-PI1.4 | Outputs delivered completely, accurately, to the right party | Output validation; delivery scoped to the authorized tenant/recipient | 4,2 | technical |
| SOC2-PI1.5 | Stored inputs/outputs remain complete and accurate | Integrity checks on stored results; retention consistent with restatement needs | 4 | technical |

## Program deliverables

Mandatory artifacts that neither the auditor nor a compliance platform produces
for you. Absent from most engineering-led programs entirely.

| ID | Deliverable | Signal | Domain | Type |
|----|-------------|--------|--------|------|
| SOC2-PROG.1 | **Management assertion letter** | Signed by leadership **before** the examination begins; signer identified | 11 | program |
| SOC2-PROG.2 | **System description** | Management-written: system boundary, infrastructure, software, people, procedures, data, subservice orgs, complementary user entity controls | 11 | program |
| SOC2-PROG.3 | **Controls matrix** | Each in-scope criterion → control statement, named owner, evidence source, test cadence | 11 | program |
| SOC2-PROG.4 | Policy stack | Infosec, access, change mgmt, IR, BC/DR, data classification & retention, vendor risk, acceptable use, HR security — exec-approved, dated, acknowledged | 11 | program |

- **PROG.1** is a mandatory AICPA prerequisite: leadership attests that the system
  description is fairly presented, that controls are suitably designed, and (Type
  II) that they operated effectively over the period. **The examination cannot
  begin without it.** It binds leadership personally, so it needs real review time,
  not a signature scramble the week fieldwork starts.
- **PROG.2** is a management-written section of the report, not an auditor
  deliverable. A rushed or inaccurate description creates a mismatch between
  described and actual controls — precisely the gap auditors test.
- **PROG.3** is the working artifact of the entire program. Without it, "every
  control has an owner" is an intention rather than a document, and evidence gaps
  stay invisible until fieldwork — the point at which they can no longer be fixed
  inside the current window. **A policy folder is not a matrix.**
- **PROG.4**: templates cover most of the writing; the real work is making the
  policies match actual practice. Auditors test the gap between paper and reality,
  and **a policy that contradicts practice is worse than no policy.**

## Notes for the auditing agent

- A SOC 2 finding is a *gap between the criterion and the implementation*. "No
  audit logging on the login mutation" → `SOC2-CC7.2`. Generic code smells without
  a criterion mapping are not SOC 2 findings.
- `program`-type controls are **not** code findings outside readiness mode — route
  them to Out of Scope with an owner and an attestation question.
- Discovery for `program` controls is a *question*, not a scan. The sharp ones:
  "show me last quarter's access review," "when did you last restore from backup,"
  "when was the last tabletop," "who is drafting the system description and who
  signs the assertion." A shrug is the finding.
- Where a control is automated and preventive (a merge-blocking CI gate, a
  deny-by-default scrub), say so. Auditors weight preventive controls above
  detective ones, verify them once for design, and sample them less aggressively —
  which lowers audit cost directly.
