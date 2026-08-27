# Minimization, Retention & Erasure Mechanics — Art. 5(1)(c), 5(1)(e), 17, 25(2)

Columns: **ID** · **Requirement** · **Automated signal** · **Domain** · **Type**.
Type semantics as in `lawful-basis.md`.

## Personal-data inventory patterns (run first — the audit's spine)

Grep schemas, migrations, ORM models, protobuf/GraphQL/event schemas for
PII-indicative fields:

- **Direct identifiers:** `email`, `phone`, `name`, `first_name`, `last_name`,
  `address`, `zip|postal`, `ssn|national_id|passport`, `dob|birth`
- **Online/device identifiers (still personal data):** `ip_address`, `device_id`,
  `idfa|gaid`, `fingerprint`, `user_agent`, `lat|lng|location|geo`
- **Art. 9 flags (severity floor High):** `health`, `medical`, `diagnosis`,
  `religion`, `ethnicity|race`, `sexual|orientation`, `political`, `union`,
  `biometric`, `genetic`; children signals: `age`, `parent_consent`
- **Unclassifiable PII sinks:** free-text `notes`, `comments`, `bio`,
  `description` adjacent to user records — flag for policy, not for content

Check **unexpected stores** — the classic deletion blind spots: search-index
mappings (Elasticsearch/OpenSearch), cache key patterns (Redis), analytics/event
schemas, warehouse/dbt models, queue message schemas, vector-DB payloads, blob
storage (avatars, uploads).

Machine-readable classification (Fides/fideslang YAML, dbt meta tags, column
comments) present = verify coverage against the grep results; absent = file
GDPR-30-INV (see `accountability-program.md`) noting no inventory-as-code.

## Art. 5(1)(c) — minimization

| ID | Requirement | Automated signal | Domain | Type |
|----|-------------|------------------|--------|------|
| GDPR-5.1c-API | APIs expose only needed fields | Full-model serialization (`user.to_json`, entity spread, `SELECT *` into responses) instead of DTOs/allowlists; GraphQL PII fields without field-level authz | 3 | technical |
| GDPR-5.1c-COLL | Collected fields map to a purpose | Required signup/form fields with no evident purpose (DOB/gender/phone for a newsletter) | 3 | technical |
| GDPR-5.1c-ANA | Analytics events pseudonymous and minimal | `track(`/`logEvent`/`identify` calls carrying raw email/name/full payloads; identify keyed on internal pseudonymous IDs | 3,7 | technical |
| GDPR-5.1c-IP | IP addresses minimized | Raw IP stored in analytics/DB without truncation/anonymize-IP settings | 3 | technical |
| GDPR-5.1c-INT | Internal calls pass IDs, not whole user objects | Service-to-service payloads forwarding full user records where an ID suffices | 3 | technical |

## Art. 5(1)(e) — storage limitation

| ID | Requirement | Automated signal | Domain | Type |
|----|-------------|------------------|--------|------|
| GDPR-5.1e-SCHED | Retention schedule exists per data category | Retention documented per category in design/RoPA | 3 | program |
| GDPR-5.1e-CODE | Retention enforced in code, not just policy | TTL indexes, S3 lifecycle rules, table expiration, `retention.ms` on PII topics, scheduled purge jobs — **no enforcement job anywhere = finding ("retention exists only as policy")** | 3 | technical |
| GDPR-5.1e-LOG | Log retention bounded | Log pipeline retention config; indefinite retention of PII-bearing logs = finding | 3,6 | technical |

## Art. 17 — erasure mechanics

Doctrine: erasure must be **verifiable and irreversible**. Hidden-from-the-app
("functional deletion") is not erasure. Soft delete is acceptable only as stage
1 of a two-stage delete.

| ID | Requirement | Automated signal | Domain | Type |
|----|-------------|------------------|--------|------|
| GDPR-17-SOFT | Soft delete has a stage-2 purge | `deleted_at`/`is_deleted`/paranoid models on PII tables **without** a scheduled purge/anonymize job = finding | 3 | technical |
| GDPR-17-CASC | Cascade covers every copy | **Coverage diff**: deletion path vs inventory — child tables, denormalized copies, search indexes, caches, events, warehouse, blobs, queues, vector DBs (soft-deleted embeddings remain reconstructible) | 3 | technical |
| GDPR-17-BAK | Backups handled | One of: bounded backup retention (data ages out, documented), deletion replay on restore, or crypto-shredding (per-user keys destroyed on erasure). None = finding; indefinite backup retention = finding | 3 | technical |
| GDPR-17-TEST | Deletion verified | Tests or verification jobs confirm post-deletion absence across stores | 3 | technical |

## Art. 25(2), 89 — pseudonymization vs anonymization

Doctrine: **pseudonymized data is still personal data**. Anonymization requires
irreversibility including against the controller's own auxiliary data.

| ID | Requirement | Automated signal | Domain | Type |
|----|-------------|------------------|--------|------|
| GDPR-25.2-HASH | Hashed identifiers classified correctly | Unsalted `md5/sha256(email)` treated as "anonymized" = finding; minimum is keyed hashing (HMAC with secret) and it is still pseudonymization | 3 | technical |
| GDPR-25.2-KEY | Pseudonymization keys separated | Token vaults/lookup tables/keys in a separate store with separate access control; same DB/table as the data = finding | 3,4 | technical |
| GDPR-25.2-QID | "Anonymized" exports resist re-identification | Row-level exports retaining user_id, precise timestamps+location, or zip+DOB+gender quasi-identifier combos = finding; look for k-anonymity/aggregation logic | 3 | technical |
| GDPR-25.2-MASK | Masking is server-side | Client-side-only masking with full value in the API response = finding | 3 | technical |
| GDPR-25.2-STG | Non-prod environments scrubbed | Prod snapshots into staging/dev without anonymization; look for scrubbing tooling in seed/refresh scripts | 3 | technical |
