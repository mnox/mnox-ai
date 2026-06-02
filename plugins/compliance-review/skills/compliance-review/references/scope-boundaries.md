# Scope Boundaries — Human-Attestation Controls

An automated audit of code, IaC, or cloud config can verify *technical* controls.
It **cannot** verify policies, contracts, training, processes, or physical
security. Reporting the absence of those as a finding produces false failures and
false comfort. This file lists controls that must be routed to the report's
**Out of Scope — Human Attestation Required** section instead of being filed as
findings.

For each, the report should name the **control ID**, the **attestation owner**,
and the **question the human must answer**.

## SOC 2 — out of scope

| Control area | Owner | Attestation question |
|--------------|-------|----------------------|
| CC1 — Control environment, org structure, ethics | Leadership / HR | Are roles, responsibilities, and a code of conduct defined? |
| CC2 — Communication of objectives & responsibilities | Leadership | Are security commitments communicated internally and to users? |
| CC4 — Monitoring activities (the *program*) | Compliance | Are control evaluations performed on a cadence? |
| CC5 — Control activities (policy-level) | Compliance | Are policies documented and enforced organizationally? |
| CC7.4 — Incident response *process* | Security / SRE | Is there a tested incident-response runbook with on-call ownership? |
| CC9 — Risk mitigation & vendor management | Procurement / Security | Are vendors risk-assessed; are vendor contracts reviewed? |
| Availability — DR *test execution* (A1.3) | SRE | Has the recovery plan actually been tested within the period? |

## HIPAA — out of scope

| Control area | Owner | Attestation question |
|--------------|-------|----------------------|
| §164.308(a)(1) — Risk analysis & risk management | Security / Compliance | Is a documented ePHI risk assessment current? |
| §164.308(a)(1)(ii)(C) — Sanction policy | HR | Is there a workforce sanction policy for violations? |
| §164.308(a)(5) — Security awareness & training | HR / Security | Is workforce security training delivered and tracked? |
| §164.308(a)(7) — Contingency plan *testing* | SRE | Has the contingency plan been tested? |
| §164.308(a)(8) — Periodic evaluation | Compliance | Is the security posture periodically re-evaluated? |
| §164.310 — Physical safeguards (facility, workstation, device) | Facilities / IT | Are facility access, workstation use, and media disposal controlled? |
| §164.314 — Business Associate Agreements | Legal | Is a signed BAA in place for every processor touching ePHI? |

## PCI-DSS — out of scope

| Control area | Owner | Attestation question |
|--------------|-------|----------------------|
| Req 9 — Physical access to the CDE | Facilities | Is physical access to cardholder-data systems restricted and logged? |
| Req 12 — Information security policy & program | Compliance | Is an infosec policy maintained, with risk assessment and personnel screening? |
| Req 11.3 — Penetration testing *engagement* | Security | Has an external/internal pen test been performed this period? |
| Scoping & network segmentation validation | QSA / SRE | Has CDE scope and segmentation been validated by a QSA? |
| SAQ / ROC / AOC documentation | Compliance | Are the PCI attestation documents complete and current? |

## How to report these

Do not omit them silently — that hides risk. For each relevant control, emit a row
in the Out of Scope section:

```
- ID: <control>  Owner: <team>  Status: Requires human attestation
  Question: <the attestation question>
```

If the target *integrates a third party* that would trigger one of these (a new
data processor → BAA / vendor review), call it out explicitly so the human knows
an attestation item was newly created by this change.
