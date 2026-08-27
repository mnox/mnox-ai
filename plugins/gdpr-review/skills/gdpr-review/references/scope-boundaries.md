# Scope Boundaries — Legal / Attestation Obligations

An automated audit of code, IaC, or documents can verify *technical* posture. It
**cannot** verify contracts, the legal adequacy of notice text, whether a
balancing test was genuinely performed, or organizational facts. Reporting the
absence of those as findings produces false failures and false comfort. Route
them to the report's **Out of Scope — Legal / Attestation Required** section
with the **article ID**, the **attestation owner**, and the **question the human
must answer**.

> **`readiness` mode inverts this file.** There these obligations are the
> subject of the review and their absence is a first-class finding (see
> `accountability-program.md`). Out of Scope there is reserved for what the
> reviewer genuinely could not reach.

## Out of scope in code / design / iac / dataflow modes

| Obligation | Article | Owner | Attestation question |
|------------|---------|-------|----------------------|
| Lawful-basis selection is legally sound per purpose | 6 | Legal / DPO | Is the documented basis defensible for each purpose, chosen before processing? |
| LIA balancing tests performed and adequate | 6(1)(f) | Legal / DPO | Does a dated three-part LIA exist per LI purpose, and does it survive scrutiny? |
| Art. 9(2) exceptions legally established | 9 | Legal | Which exception covers each special-category purpose, and does member-state law add conditions? |
| Privacy notice legal adequacy | 12–14 | Legal | Does the notice satisfy all mandatory items in plain language, in the right languages? |
| Signed DPAs with all Art. 28(3) clauses, per vendor | 28 | Legal / Procurement | Is a signed, complete DPA on file for every processor the audit found in code? |
| SCCs executed with correct modules; TIAs documented | 46 | Legal | For each non-adequate destination: which instrument, which module, where is the TIA? |
| DPF/adequacy reliance currently valid for each vendor | 45 | Legal | Is the vendor certified today, for this data type — checked against the live register? |
| RoPA existence and currency | 30 | DPO / Compliance | Produce the RoPA; when was it last reconciled with reality? |
| DPIAs for high-risk processing | 35 | DPO | Which DPIAs exist, and do they cover the systems this audit inventoried? |
| DPO designation, independence, DPA filing | 37–39 | Leadership | Who is the DPO, whom do they report to, and is the contact filed and published? |
| Breach register and IR plan quality | 33(5) | Security / DPO | Show the register — including non-notified incidents — and the last IR exercise. |
| Member-state derogations (consent age floor, employment data) | 8, 88 | Legal | Which member states apply, and what do their derogations change? |
| Employee/HR data processing rules | 88 | Legal / HR | Is workforce data covered by the applicable member-state framework? |
| Representative appointed where Art. 3(2) applies without EU establishment | 27 | Legal | Is an EU representative designated and named in the notice? |

**Two rules when reporting these:**

1. **Distinguish "absent" from "present but unevidenced."** A basis that was
   chosen but never documented and one never chosen look identical from code and
   have different fixes.
2. **Always pair the attestation item with what the audit *did* verify.** "DPA
   existence is attestation — but vendor X receives email addresses
   (`file:line`) and is absent from the published subprocessor list" keeps the
   out-of-scope section from reading as a shrug.

## Never out of scope (common misroutes)

These look legal but are code-checkable — file them as findings, not
attestation:

- Consent **enforcement** at point of use (the flag is never read) — GDPR-7-ENF
- Deletion-path **coverage** vs the inventory — GDPR-17-CASC
- Vendor flows in code missing from the documented list — GDPR-28-INV
- Region pinning when EU residency is claimed — GDPR-44-IAC
- PII in logs, unsalted-hash "anonymization", pre-consent SDK init
