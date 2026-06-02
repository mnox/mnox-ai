# HIPAA Security Rule Control Catalog

Scope: the **HIPAA Security Rule** (45 CFR Part 164, Subpart C) — the safeguards
for electronic protected health information (ePHI). The Privacy Rule and Breach
Notification Rule are process/legal and are Out of Scope for an automated audit.

Safeguards are marked **(R)** required or **(A)** addressable. Addressable does not
mean optional — it means the entity must implement it or document why an
equivalent is reasonable.

Columns: **ID** · **Safeguard** · **Automated signal** · **Domain**.

## §164.312 — Technical Safeguards (the primary auditable surface)

| ID | Safeguard | Automated signal | Domain |
|----|-----------|------------------|--------|
| HIPAA-164.312(a)(1) | Access control (R) | ePHI access is restricted to authorized users/roles; object-level authZ enforced | 2 |
| HIPAA-164.312(a)(2)(i) | Unique user identification (R) | Every actor has a distinct identity; no shared/service accounts touching ePHI without attribution | 2 |
| HIPAA-164.312(a)(2)(ii) | Emergency access procedure (R) | Break-glass access path exists and is logged | 2 |
| HIPAA-164.312(a)(2)(iii) | Automatic logoff (A) | Sessions expire after inactivity; token TTLs bounded | 2 |
| HIPAA-164.312(a)(2)(iv) | Encryption & decryption of ePHI at rest (A) | ePHI encrypted in DB, object storage, volumes, backups | 1 |
| HIPAA-164.312(b) | Audit controls (R) | Access to and modification of ePHI is logged; logs capture who/what/when | 3 |
| HIPAA-164.312(c)(1) | Integrity — protect ePHI from improper alteration/destruction (R) | Integrity checks, immutable/append-only logs, checksums on stored ePHI | 3 |
| HIPAA-164.312(c)(2) | Mechanism to authenticate ePHI integrity (A) | Tamper detection on ePHI records | 3 |
| HIPAA-164.312(d) | Person/entity authentication (R) | Strong authN before ePHI access; MFA for privileged access; no auth bypass | 2 |
| HIPAA-164.312(e)(1) | Transmission security (R) | ePHI encrypted in transit; TLS ≥1.2; no plaintext transport | 1,5 |
| HIPAA-164.312(e)(2)(i) | Integrity controls in transmission (A) | Transmitted ePHI cannot be modified undetected | 5 |
| HIPAA-164.312(e)(2)(ii) | Encryption in transmission (A) | End-to-end encryption of ePHI over networks | 1,5 |

## §164.308 — Administrative Safeguards (mostly attestation; a few auditable)

| ID | Safeguard | Automated signal | Domain |
|----|-----------|------------------|--------|
| HIPAA-164.308(a)(1)(ii)(D) | Information system activity review (R) | Log review is *possible* — logs exist, are queryable, retained | 3 |
| HIPAA-164.308(a)(3)(ii)(C) | Termination procedures (A) | Deprovisioning path revokes ePHI access | 2 |
| HIPAA-164.308(a)(4)(ii)(B) | Access authorization (A) | Role-based access grants are explicit, least-privilege | 2 |
| HIPAA-164.308(a)(5)(ii)(C) | Log-in monitoring (A) | Failed/successful auth attempts are logged | 3 |
| HIPAA-164.308(a)(5)(ii)(D) | Password management (A) | No hardcoded/weak credentials; secrets vaulted | 6 |
| HIPAA-164.308(a)(7)(ii)(A) | Data backup plan (R) | Automated ePHI backups configured | 8 |
| HIPAA-164.308(a)(7)(ii)(B) | Disaster recovery plan (R) | DR/restore configuration exists | 8 |

The remainder of §164.308 (risk analysis, sanction policy, security training,
workforce clearance, contingency *testing*, evaluation) is **attestation** — route
to Out of Scope.

## §164.310 — Physical Safeguards

Entirely **attestation** for an automated audit (facility access, workstation
security, device/media disposal). Route all of §164.310 to Out of Scope. One
partial exception: media disposal logic in code (secure deletion of ePHI from
storage) maps to `HIPAA-164.310(d)(2)(i)` and can be checked — Domain 4.

## §164.314 — Organizational Requirements

Business Associate Agreements (BAAs) and contracts — **attestation only**. Route
to Out of Scope. Flag if the target integrates a third-party processor that would
*require* a BAA, so the human reviewer can confirm one exists.

## Notes for the auditing agent

- The trigger for *any* HIPAA finding is **ePHI**. First identify whether the
  target actually handles ePHI (health data tied to an individual). If it does
  not, say so — do not manufacture HIPAA findings for a non-ePHI system.
- "Addressable" controls still produce findings: an absent addressable safeguard
  with no documented equivalent is a real gap. Mark severity by ePHI exposure.
