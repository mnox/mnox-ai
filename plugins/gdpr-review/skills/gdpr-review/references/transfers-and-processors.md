# Processors & International Transfers — Art. 28, 44–49

Columns: **ID** · **Requirement** · **Automated signal** · **Domain** · **Type**.
Type semantics as in `lawful-basis.md`.

**Enforcement-weighted: the largest GDPR fines cluster here.** Weight transfer
findings aggressively.

## Vendor inventory (run against the code, not the docs)

Build the vendor list from the target itself: SDK imports and API clients
(payments, analytics, error tracking, CRM, messaging, email, push, LLM APIs) and
outbound HTTP calls carrying inventory fields. Regulators test with network
monitors, not policy documents — **the code-derived list diffed against the
documented processor list is the single highest-yield check in this domain.**
LLM/AI API calls with PII in prompts are processor data flows like any other.

## Art. 28 — processors

| ID | Requirement | Automated signal | Domain | Type |
|----|-------------|------------------|--------|------|
| GDPR-28-INV | Every PII-receiving vendor is on the documented processor/subprocessor list | **Coverage diff**: code-derived vendor inventory vs documented list — undocumented flows are technical findings | 5 | technical |
| GDPR-28.3 | Written DPA with all mandatory clauses (documented instructions, confidentiality, Art. 32 security, sub-processor authorization + flow-down, DSR assistance, breach/DPIA assistance, deletion-or-return at end, audit rights) | DPA existence/content is attestation; the audit verifies which vendors *need* one | 5 | program |
| GDPR-28.2 | Sub-processor changes notified; list maintained | Published subprocessor list exists and matches observed flows | 5 | program |
| GDPR-28-DEL | Vendors support deletion propagation | Deletion API integration per vendor (see GDPR-17-PROC); vendors with no deletion path flagged | 2,5 | technical |
| GDPR-28-SDK | SDKs do not transmit before consent | Mobile/web SDKs initialized at launch vs consent-gated init (`setConsent`, delayed init) — init-at-launch of analytics SDKs = finding | 5,7 | technical |

## Chapter V — transfers (Art. 44–49)

A transfer is lawful only via: **adequacy decision** (Art. 45), **appropriate
safeguards** (Art. 46 — 2021 SCCs by module, BCRs), or narrow **Art. 49
derogations** (occasional only). Post-Schrems II, SCC transfers additionally
require a documented **Transfer Impact Assessment** plus supplementary measures
where needed. Remote *access* from a third country is a transfer.

> **Verify adequacy and DPF status live** — never from this file or memory. The
> EU–US DPF and individual vendor certifications (dataprivacyframework.gov) are
> litigation-exposed and time-sensitive; recommend SCC fallback clauses for
> DPF-reliant transfers.

| ID | Requirement | Automated signal | Domain | Type |
|----|-------------|------------------|--------|------|
| GDPR-44-MAP | A transfer map exists covering onward/sub-processor transfers and third-country remote access | Map exists; diff against code-derived vendor inventory and IaC regions | 5 | technical |
| GDPR-45 | Adequacy relied on only where a decision actually covers the destination and data type (e.g. DPF HR vs non-HR) | Destination country per vendor identified; adequacy claim flagged for live verification | 5 | technical |
| GDPR-46-SCC | Non-adequate destinations use SCCs with the correct module + documented TIA | SCC/TIA artifacts are attestation; the audit lists which vendors trigger the requirement | 5 | program |
| GDPR-44-IAC | Claimed EU residency is real in IaC | Region config on every PII datastore (`eu-*` vs `us-*`), cross-region replication rules, CDN/edge log locations, KMS keys region-pinned, bucket policies restricting region | 5 | technical |
| GDPR-44-UK | UK transfers use IDTA / UK addendum | UK-destination flows flagged for the UK-specific instrument | 5 | program |
| GDPR-49 | Derogations not used for systematic transfers | Regular vendor flows justified under "occasional" derogations = finding | 5 | technical |
