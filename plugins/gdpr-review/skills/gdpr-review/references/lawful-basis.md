# Lawful Basis & Consent — Art. 5(1)(a), 6, 7, 8, 9, 10

Columns: **ID** · **Requirement** · **Automated signal** (what a code/design/IaC
review can verify) · **Domain** (fan-out agent) · **Type**.

- `technical` — verifiable from code, config, or the document under review. Files as a **finding**.
- `program` — legal/organizational. Files in **Out of Scope — Legal/Attestation Required**
  (first-class finding in `readiness` mode only).

## Art. 6 — lawful basis

Exactly one of six bases per processing purpose, chosen and documented **before**
processing begins: consent, contract necessity, legal obligation, vital
interests, public task, legitimate interests.

| ID | Requirement | Automated signal | Domain | Type |
|----|-------------|------------------|--------|------|
| GDPR-6.1 | Every processing purpose has a documented lawful basis | Design docs / RoPA name a basis per purpose; code purposes (analytics, marketing, profiling) map to a stated basis | 1 | program |
| GDPR-6.1b | Contract necessity read narrowly | Purposes claimed contract-necessary are genuinely required to deliver the service — behavioral ads under "contract" is a precedent-contradicted red flag | 1 | technical |
| GDPR-6.1f | Legitimate interest backed by a documented 3-part LIA (purpose, necessity, balancing) | LIA artifact exists and predates the processing; LI not used for purposes regulators have rejected (ad profiling) | 1 | program |
| GDPR-6.4 | Purpose limitation — no reuse for incompatible purposes | Data collected for purpose A not silently fed to purpose B (e.g. support emails into marketing lists, prod data into model training) without a documented basis | 1 | technical |

## Art. 7 — consent validity

Freely given, specific, informed, unambiguous, by affirmative act.

| ID | Requirement | Automated signal | Domain | Type |
|----|-------------|------------------|--------|------|
| GDPR-7.1 | Controller can demonstrate consent | Consent record schema captures who, when, policy/text version, purposes, and collection context; timestamped, append-only preferred | 1 | technical |
| GDPR-7.2 | Consent request distinguishable, plain language, not bundled into T&Cs | Consent UI/copy separate from T&C acceptance; no single "agree to everything" gate | 1,7 | technical |
| GDPR-7.3 | Withdrawal as easy as giving; effective downstream | One-step withdrawal path exists; withdrawal propagates (stops event flow, unsubscribes downstream vendors) | 1,7 | technical |
| GDPR-7.4 | No consent walls — service not conditioned on unnecessary consent | Core functionality reachable with non-essential consent declined | 7 | technical |
| GDPR-7-GRAN | Granular per-purpose consent | Separate flags per purpose (analytics / marketing / functional), not one blanket boolean | 1 | technical |
| GDPR-7-ENF | Consent enforced at point of use | Every analytics/marketing/profiling call site reads the consent flag before firing; a stored-but-never-read flag is a finding | 1,7 | technical |
| GDPR-7-VER | Re-consent on material change | Mechanism exists to version consent text and re-prompt when purposes change | 1 | technical |

## Art. 8 — children

| ID | Requirement | Automated signal | Domain | Type |
|----|-------------|------------------|--------|------|
| GDPR-8.1 | Parental consent below the member-state age floor (13–16) for information-society services | Age gate exists where minors are plausible users; parental-consent flow for under-floor users; flag which member state's floor applies | 1 | technical |
| GDPR-8.2 | Reasonable efforts to verify parental consent | Verification mechanism beyond a self-asserted checkbox | 1 | technical |

## Art. 9 — special categories

Prohibited by default: racial/ethnic origin, political opinions,
religious/philosophical beliefs, trade-union membership, genetic data, biometric
data for unique identification, health, sex life/orientation. Requires an Art. 6
basis **and** an Art. 9(2) exception. Explicit consent is a higher bar than
regular consent. **Inferred sensitive data counts** (health inferred from
purchases, orientation from behavior).

| ID | Requirement | Automated signal | Domain | Type |
|----|-------------|------------------|--------|------|
| GDPR-9.1 | Special-category data identified and gated | Inventory flags Art. 9 fields; any found column (`health`, `diagnosis`, `religion`, `ethnicity`, `orientation`, `political`, `union`, `biometric`, `genetic`) raises severity floor to High | 1 | technical |
| GDPR-9.2 | Documented Art. 9(2) exception per special-category purpose | Exception named per purpose (explicit consent, employment law, vital interests, legal claims, health care, research) | 1 | program |
| GDPR-9-INF | Inferred special-category data treated as special-category | Profiling/ML features that proxy sensitive attributes flagged (e.g. pregnancy prediction, religiosity scores) | 1 | technical |
| GDPR-10 | Criminal-offence data processed only under official authority or member-state law | Columns like `criminal_record`, `conviction`, `offense` flagged; legal gate documented | 1 | program |
