# Accountability Program — Art. 5(2), 24, 30, 35, 36, 37–39

**`readiness` mode only** as first-class findings; in every other mode these
route to Out of Scope per `scope-boundaries.md`.

Columns: **ID** · **Requirement** · **Automated signal / discovery question** ·
**Domain** · **Type**. Everything here is `program` unless marked; in readiness
mode, `program` items file as findings with `Status` (absent / present but
unevidenced / present and evidenced) and `Cost`.

## Art. 30 — records of processing (RoPA)

| ID | Requirement | Discovery | Domain | Type |
|----|-------------|-----------|--------|------|
| GDPR-30.1 | Controller RoPA: purposes, data-subject and data categories, recipient categories, transfers + safeguards, retention envelopes, security-measures description | "Show me the RoPA." Written/electronic, current, produced on demand | 8 | program |
| GDPR-30.2 | Processor RoPA (lighter, parallel) where acting as processor | Same, scoped to processor activities | 8 | program |
| GDPR-30-MATCH | RoPA matches actual systems | **Coverage diff**: RoPA rows vs the personal-data inventory and code-derived vendor list — the gap is the finding | 8 | technical |
| GDPR-30.5 | Exemption applied correctly | Current law: <250 employees AND processing occasional, non-risky, no special categories. A pending proposal raises the threshold — **verify status live** before relying on the exemption | 8 | program |
| GDPR-30-INV | Inventory-as-code | Machine-readable classification (Fides/fideslang, dbt meta) keeps the RoPA honest; absence is a Medium in readiness mode | 8 | technical |

## Art. 35/36 — DPIA

| ID | Requirement | Discovery | Domain | Type |
|----|-------------|-----------|--------|------|
| GDPR-35.1 | DPIA screening for new high-risk processing | A screening step exists in the project/feature process | 8 | program |
| GDPR-35.3 | DPIAs exist for mandatory triggers: systematic extensive profiling with significant effects; large-scale Art. 9/10 data; large-scale systematic public monitoring — plus the relevant DPA's Art. 35(4) blacklist | DPIA documents exist for the org's AI/ML systems, tracking, biometrics, monitoring; revisited on change | 8 | program |
| GDPR-35.7 | DPIA content complete | Systematic description + purposes, necessity/proportionality, risk assessment, mitigations; DPO advice sought | 8 | program |
| GDPR-36 | Prior consultation when residual risk stays high | Evidence of DPA consultation where a DPIA ended high-risk | 8 | program |
| GDPR-35-AI | AI systems inventoried and cross-referenced | AI system inventory reconciled with the RoPA; for high-risk AI, DPIA paired/combined with an AI-Act fundamental-rights impact assessment — obligations phase in, **verify current enforceability dates live** | 8 | program |

## Art. 37–39 — DPO

| ID | Requirement | Discovery | Domain | Type |
|----|-------------|-----------|--------|------|
| GDPR-37.1 | DPO designated where mandatory (public authority; core activities = regular systematic large-scale monitoring; core activities = large-scale Art. 9/10 data) | Trigger analysis documented; DPO appointed on expertise | 8 | program |
| GDPR-37.7 | DPO contact published and communicated to the DPA | Contact on the website and in the notice; DPA filing done | 8 | program |
| GDPR-38 | DPO independence and resourcing | No instructions on task performance, no conflict of interest (not CTO/head of marketing deciding purposes), reports to highest management, involved early | 8 | program |

## Art. 5(2)/24 — demonstrable accountability

| ID | Requirement | Discovery | Domain | Type |
|----|-------------|-----------|--------|------|
| GDPR-5.2-EVID | Compliance is demonstrable, not just done | Policies dated and approved; LIAs, consent records, DPIAs, breach register, training logs retained and retrievable | 8 | program |
| GDPR-24-REV | Measures reviewed and updated | A review cadence exists that surfaces gaps between incidents, not after them | 8 | program |
| GDPR-12-SLA | DSR handling evidenced | Request log with received/fulfilled dates demonstrating the 1-month SLA | 2,8 | program |

## Readiness-mode ordering

Triage in this order — it mirrors what a supervisory authority asks for first
after a complaint: (1) RoPA and inventory match, (2) lawful-basis register incl.
LIAs, (3) DSR log and SLA evidence, (4) breach register and IR plan, (5)
DPIAs for the obvious triggers, (6) DPO posture, (7) transfer map + TIAs. A gap
in (1)–(3) escalates every other finding, because it means the org cannot answer
the first letter.
