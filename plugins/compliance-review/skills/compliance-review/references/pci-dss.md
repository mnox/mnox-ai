# PCI-DSS v4.0 Control Catalog

Scope: the **Payment Card Industry Data Security Standard v4.0** — protects
cardholder data (CHD: PAN, cardholder name, expiry, service code) and sensitive
authentication data (SAD: full track, CVV, PIN). The audit covers the technical
requirements; assessor/QSA process, scoping documentation, and policy maintenance
are Out of Scope.

The trigger for any PCI finding is the presence of **CHD or SAD** in the target —
storage, processing, or transmission. If the system only touches a tokenized
reference or a hosted payment iframe and never sees a PAN, most of Req 3 does not
apply; say so rather than manufacturing findings.

Columns: **ID** · **Requirement** · **Automated signal** · **Domain**.

## Requirement 3 — Protect stored account data

| ID | Requirement | Automated signal | Domain |
|----|-------------|------------------|--------|
| PCI-3.2.1 | SAD is not retained after authorization | No full track / CVV / PIN persisted to DB, logs, or cache | 4 |
| PCI-3.3.1 | PAN is masked when displayed (max first 6 / last 4) | UI and API responses mask PAN | 4 |
| PCI-3.4.1 | PAN is unreadable in logs and audit trails | PAN never written to logs in clear | 3,4 |
| PCI-3.5.1 | PAN is rendered unreadable wherever stored | PAN encrypted / tokenized / hashed at rest | 1,4 |
| PCI-3.6.1 | Strong cryptography and key management for stored PAN | KMS-managed keys, documented key lifecycle, no app-embedded keys | 1 |
| PCI-3.7.x | Key lifecycle — rotation, retirement, split knowledge | Key rotation configured; keys not hardcoded | 1,6 |

## Requirement 4 — Protect CHD in transit over open networks

| ID | Requirement | Automated signal | Domain |
|----|-------------|------------------|--------|
| PCI-4.2.1 | Strong cryptography for PAN transmission | TLS ≥1.2 (prefer 1.3); no weak ciphers; cert validation enabled | 1,5 |
| PCI-4.2.1.1 | Inventory of trusted keys/certificates | Pinned/managed certs; no `InsecureSkipVerify`-style bypass | 5 |

## Requirement 6 — Develop and maintain secure systems and software

| ID | Requirement | Automated signal | Domain |
|----|-------------|------------------|--------|
| PCI-6.2.4 | Secure coding — injection, access-control, crypto flaws addressed | No SQLi/XSS/SSRF patterns; parameterized queries | 9 |
| PCI-6.3.1 | Security vulnerabilities are identified and ranked | SCA / CVE scanning present | 7 |
| PCI-6.3.2 | Inventory of bespoke and third-party software | Lockfiles, pinned dependencies, SBOM-able | 7 |
| PCI-6.3.3 | Components are patched (critical patches ≤1 month) | No known-vulnerable dependency versions | 7 |
| PCI-6.4.1 | Public-facing web apps protected (review or WAF) | Code review gating; WAF/network rules in IaC | 9,10 |

## Requirement 7 — Restrict access to system components and CHD

| ID | Requirement | Automated signal | Domain |
|----|-------------|------------------|--------|
| PCI-7.2.1 | Access is assigned by role with least privilege | RBAC enforced; no broad default grants | 2 |
| PCI-7.2.2 | Access is based on job function and least privilege | Scoped permissions; CHD access narrowly gated | 2 |

## Requirement 8 — Identify users and authenticate access

| ID | Requirement | Automated signal | Domain |
|----|-------------|------------------|--------|
| PCI-8.2.1 | Unique ID for every user before access | No shared accounts; per-actor identity | 2 |
| PCI-8.3.1 | Strong authentication for all access | No weak/default credentials; password policy enforced | 2,6 |
| PCI-8.4.1 | MFA for access into the CDE | MFA required for admin / CDE access | 2 |
| PCI-8.6.x | Application/system accounts and credentials managed | Service-account secrets vaulted, rotated, not hardcoded | 6 |

## Requirement 10 — Log and monitor all access

| ID | Requirement | Automated signal | Domain |
|----|-------------|------------------|--------|
| PCI-10.2.1 | Audit logs capture all access to CHD and admin actions | Security-relevant events logged with actor/time | 3 |
| PCI-10.3.1 | Audit logs are protected from modification | Append-only / tamper-evident log sink | 3 |
| PCI-10.5.1 | Audit log history is retained (≥12 months, 3 readily available) | Log retention configured | 3,8 |

## Requirement 11 — Test security of systems and networks regularly

| ID | Requirement | Automated signal | Domain |
|----|-------------|------------------|--------|
| PCI-11.3.1 | Internal vulnerability scans are performed | Scanning wired into CI / scheduled | 7 |
| PCI-11.6.1 | Change/tamper detection on payment pages | Integrity monitoring on payment-page assets | 9 |

## Notes for the auditing agent

- Requirements **1** (network controls), **2** (secure configuration), **5**
  (anti-malware), **9** (physical access), and **12** (policy/program management)
  are predominantly infrastructure-team or organizational. Audit Req 1/2-style
  network and config controls only in `iac` or `runtime` mode (Domains 5, 10);
  route Req 9 and Req 12 to Out of Scope.
- The single highest-severity PCI finding class is **SAD retention** (`PCI-3.2.1`)
  and **PAN in logs** (`PCI-3.4.1`) — these are outright prohibited, not weak
  configurations. Treat any confirmed instance as Critical.
