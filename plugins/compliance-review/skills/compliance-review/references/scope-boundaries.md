# Scope Boundaries — Human-Attestation Controls

An automated audit of code, IaC, or cloud config can verify *technical* controls.
It **cannot** verify policies, contracts, training, processes, or physical
security. Reporting the absence of those as a finding produces false failures and
false comfort. This file lists controls that must be routed to the report's
**Out of Scope — Human Attestation Required** section instead of being filed as
findings.

For each, the report should name the **control ID**, the **attestation owner**,
and the **question the human must answer**.

> **`readiness` mode inverts this file.** In readiness mode these controls are the
> subject of the review, so their absence is a **first-class finding**, not an
> out-of-scope note. Out of Scope there is reserved for what the reviewer genuinely
> could not reach. See `references/readiness-program.md`.

## SOC 2 — out of scope

| Control area | Owner | Attestation question |
|--------------|-------|----------------------|
| CC1 — Control environment, org structure, ethics | Leadership / HR | Are roles, responsibilities, and a code of conduct defined, with acknowledgments recorded? |
| CC1.2 — Board or equivalent oversight | Leadership | Is there an oversight body, or a documented equivalent oversight cadence for a company this size? |
| CC1.4 — Security awareness training | HR / Security | Is training delivered, and are acknowledgments recorded? |
| CC2 — Communication of objectives & responsibilities | Leadership | Are security commitments communicated internally and to users, with a published external security contact? |
| CC3.2 — Risk assessment | Compliance / Security | Is there a dated risk assessment covering the current period? |
| CC4 — Monitoring activities (the *program*) | Compliance | Are control evaluations performed on a cadence that surfaces failures **between** audits rather than at fieldwork? |
| CC5 — Control activities (policy-level) | Compliance | Are policies documented, exec-approved, dated, acknowledged — and do they match actual practice? |
| CC6.3 — Access review execution & evidence | IT / Security | **"Show me last quarter's access review."** Is it performed quarterly by a named owner, and retained with timestamps? |
| CC6.8 — Endpoint/workstation posture | IT | Are in-scope laptops encrypted, screen-locked, and MDM-enrolled or documented and attested? |
| CC7.1 — Patch SLA and dependency review cadence | Engineering | Are remediation thresholds defined, met, and is the periodic dependency review evidenced? |
| CC7.4 — Incident response *process* | Security / SRE | Is there a runbook with on-call ownership, and **when was the last tabletop** — dated, with named participants and findings? |
| CC9 — Risk mitigation & vendor management | Procurement / Security | Is there a vendor inventory; are subprocessor SOC 2 / ISO reports collected and current? |
| Availability — DR *test execution* (A1.3) | SRE | **"When did you last restore from backup?"** Has a timed restore drill been performed and documented within the period? |
| PROG.1 — Management assertion letter | Leadership (signer) | Who signs it, and is it signed **before** the examination begins? |
| PROG.2 — System description | Leadership / Compliance | Who is drafting it, and does it match the system as actually built? |
| PROG.3 — Controls matrix | Compliance | Does each in-scope criterion map to a control statement, a **named owner**, an evidence source, and a test cadence? |

**Two rules when reporting these:**

1. **Distinguish "absent" from "present but unevidenced."** A control that runs and
   is never recorded looks clean in code and fails a Type II examination. Say which
   one you found.
2. **Flag evidence gaps as schedule risk.** Missing evidence cannot be backfilled
   into an observation window — the window restarts. That consequence belongs in
   the report, not just the control status.

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
