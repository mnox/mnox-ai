# Data Subject Rights — Art. 12–23

Columns: **ID** · **Requirement** · **Automated signal** · **Domain** · **Type**.
Type semantics as in `lawful-basis.md`.

## Hard numbers (deterministic checks)

- Response **without undue delay, max 1 calendar month**; extendable **+2 months**
  for complexity, but the extension notice with reasons must go out within the
  first month (Art. 12(3)).
- Free of charge; fee/refusal only for manifestly unfounded or excessive
  requests, burden of proof on the controller (Art. 12(5)).
- Refusals must state reasons, the right to complain to a DPA, and judicial
  remedy, within 1 month (Art. 12(4)).

## Art. 12 — modalities

| ID | Requirement | Automated signal | Domain | Type |
|----|-------------|------------------|--------|------|
| GDPR-12.2 | DSR intake channel exists and is discoverable | A request path exists (settings page, endpoint, documented email); requests are logged with received-date for deadline tracking | 2 | technical |
| GDPR-12.3 | Deadline tracking for the 1-month window | Queue/state machine or tracker records request → fulfillment dates | 2 | technical |
| GDPR-12.6 | Identity verification proportionate, not obstructive | Verification before fulfillment, but not demands for excessive ID for low-risk requests | 2 | technical |

## Art. 13/14 — information at collection

| ID | Requirement | Automated signal | Domain | Type |
|----|-------------|------------------|--------|------|
| GDPR-13.1 | Notice at point of collection with mandatory items (identity, DPO contact, purposes + basis, recipients, transfers, retention, rights, withdrawal, complaint right, ADM logic) | Collection surfaces link a notice; notice covers the purposes actually observed in code | 2 | program |
| GDPR-14.3 | Indirectly-obtained data: notice within 1 month or at first contact | Data enrichment / purchased-list flows include a notice step | 2 | program |
| GDPR-13-DRIFT | Notice matches actual processing | Diff observed data flows (vendors, purposes) against the published notice — undisclosed flows are technical findings | 2,5 | technical |

## Art. 15 — access; Art. 20 — portability

| ID | Requirement | Automated signal | Domain | Type |
|----|-------------|------------------|--------|------|
| GDPR-15.1 | Access: copy of data plus metadata (purposes, categories, recipients, retention, source, ADM logic) | Export job/endpoint exists; output includes metadata, not just rows | 2 | technical |
| GDPR-15-COV | Export covers the full personal-data inventory | **Coverage diff**: tables/stores read by the export vs the inventory — every gap is a finding | 2 | technical |
| GDPR-15.3 | Secure delivery | Export delivered authenticated; no unauthenticated download links; links expire | 2 | technical |
| GDPR-20.1 | Portability: structured, commonly used, machine-readable | JSON/CSV output; applies to consent/contract-based, user-provided data | 2 | technical |

## Art. 16 — rectification; Art. 18 — restriction; Art. 19 — notification

| ID | Requirement | Automated signal | Domain | Type |
|----|-------------|------------------|--------|------|
| GDPR-16 | Users can correct their data | Edit paths exist for profile data; corrections propagate to downstream copies (search index, cache, warehouse) | 2 | technical |
| GDPR-18 | Processing can be restricted without deleting | A flag/quarantine mechanism exists that suppresses processing while retaining data | 2 | technical |
| GDPR-19 | Recipients notified of rectification/erasure/restriction | Downstream/vendor propagation on correction and deletion | 2,5 | technical |

## Art. 17 — erasure

Mechanics (soft-delete stages, backups, cascade completeness) live in
`minimization-and-retention.md`; this domain checks the *right* is serviceable.

| ID | Requirement | Automated signal | Domain | Type |
|----|-------------|------------------|--------|------|
| GDPR-17.1 | An erasure path exists for the six grounds | User-facing or operational deletion path exists at all | 2,3 | technical |
| GDPR-17-PROC | Erasure fans out to processors | Deletion calls to third-party APIs (payment, analytics, CRM deletion endpoints, OpenDSR-style) — local-only deletion while events keep flowing to vendors is a finding | 2,5 | technical |
| GDPR-17.3 | Refusal grounds documented (legal obligation, legal claims, free expression) | Retention exemptions (e.g. invoices under tax law) are scoped to the exempt fields, not used to retain everything | 2 | technical |

## Art. 21 — objection; Art. 22 — automated decision-making

| ID | Requirement | Automated signal | Domain | Type |
|----|-------------|------------------|--------|------|
| GDPR-21.2 | Objection to direct marketing is absolute and immediate | Unsubscribe/objection stops marketing processing unconditionally, incl. profiling for marketing | 2 | technical |
| GDPR-21.1 | Objection to LI-based processing honored unless compelling grounds | Objection path exists for LI purposes; suppression list maintained | 2 | technical |
| GDPR-22.1 | No solely-automated decision with legal/similarly-significant effect without a 22(2) gate | Inventory automated decisions (credit, pricing, hiring, moderation bans); each has human review, contract necessity, or explicit consent — note precedent: credit scoring itself can be an Art. 22 decision | 2 | technical |
| GDPR-22.3 | Safeguards: human intervention, express view, contest | Appeal/human-review path exists for significant automated decisions; meaningful-logic explanation available | 2 | technical |
| GDPR-22.4 | No special-category data in ADM absent 9(2)(a)/(g) + safeguards | ADM feature sets checked against Art. 9 fields and proxies | 1,2 | technical |
