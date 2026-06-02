# SOC 2 Control Catalog (Trust Services Criteria)

SOC 2 has no fixed control numbers — the TSC are *criteria*, and each auditor maps
controls to them. This catalog uses the widely-adopted `CCx.x` Common Criteria
mapping plus the optional Availability (A) and Confidentiality (C) categories.
Processing Integrity (PI) and Privacy (P) are rarely in scope for an engineering
audit; treat them as Out of Scope unless the user asks.

Columns: **ID** · **Criterion** · **Automated signal** (what an audit of code/IaC
can verify) · **Domain** (maps to a control-domain agent).

## Common Criteria — Logical & Physical Access (CC6)

| ID | Criterion | Automated signal | Domain |
|----|-----------|------------------|--------|
| SOC2-CC6.1 | Logical access controls restrict access to assets | AuthZ enforced on protected routes/resources; no broken object-level auth; tenant isolation | 2 |
| SOC2-CC6.2 | Registration/authorization of users before access | User provisioning gated; no default/shared accounts; role assignment on creation | 2 |
| SOC2-CC6.3 | Access modified/removed on role change or termination | Deprovisioning path exists; no orphaned credentials; role changes revoke access | 2 |
| SOC2-CC6.6 | Boundary protection against external threats | TLS enforced; no public exposure of internal services; network policy/firewall rules | 5,10 |
| SOC2-CC6.7 | Data transmission is protected | TLS ≥1.2 for all data in transit; no plaintext protocols; cert validation not disabled | 1,5 |
| SOC2-CC6.8 | Controls prevent/detect unauthorized software | Dependency provenance; lockfiles; no unpinned/unverified packages | 7,9 |

## Common Criteria — System Operations (CC7)

| ID | Criterion | Automated signal | Domain |
|----|-----------|------------------|--------|
| SOC2-CC7.1 | Detect configuration changes / vulnerabilities | Vulnerability scanning in CI; dependency CVE gating | 7 |
| SOC2-CC7.2 | Monitor system components for anomalies | Logging of security-relevant events; alerting wired | 3 |
| SOC2-CC7.3 | Evaluate security events | Errors/auth failures emitted to a monitored sink | 3 |
| SOC2-CC7.4 | Respond to identified security incidents | Incident hooks (alerts page someone) — *largely attestation* | 3 |

## Common Criteria — Change Management (CC8)

| ID | Criterion | Automated signal | Domain |
|----|-----------|------------------|--------|
| SOC2-CC8.1 | Changes are authorized, designed, tested, approved | Branch protection; required PR review; CI gates before deploy | 9 |

## Common Criteria — Risk & Encryption support (CC3, CC6.1)

| ID | Criterion | Automated signal | Domain |
|----|-----------|------------------|--------|
| SOC2-CC6.1-ENC | Encryption supports access restriction | Data at rest encrypted (DB, object storage, volumes); KMS-managed keys | 1,10 |
| SOC2-CC3.2 | Risks to objectives are identified | Secrets not committed; sensitive data classified | 4,6 |

## Availability (A) — optional category

| ID | Criterion | Automated signal | Domain |
|----|-----------|------------------|--------|
| SOC2-A1.2 | Environmental protections, backups, recovery infrastructure | Automated backups configured; retention set; restore path exists | 8 |
| SOC2-A1.3 | Recovery plan is tested | DR config present — *test execution is attestation* | 8 |

## Confidentiality (C) — optional category

| ID | Criterion | Automated signal | Domain |
|----|-----------|------------------|--------|
| SOC2-C1.1 | Confidential information is identified and protected | Sensitive fields classified, encrypted, access-scoped | 1,4 |
| SOC2-C1.2 | Confidential information is disposed of | Retention/deletion logic for confidential data | 4 |

## Notes for the auditing agent

- CC1 (control environment), CC2 (communication), CC4 (monitoring), CC5 (control
  activities), and CC9 (risk mitigation / vendor management) are **predominantly
  organizational** — route to Out of Scope, do not file as code findings.
- A SOC 2 finding is a *gap between the criterion and the implementation*. "No
  audit logging on the login mutation" → `SOC2-CC7.2`. Generic code smells without
  a criterion mapping are not SOC 2 findings.
