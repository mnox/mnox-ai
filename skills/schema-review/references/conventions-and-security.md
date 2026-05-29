# Lens: Naming/Consistency, Privacy & Security

Cross-cutting hygiene: naming conventions, PII/PHI, tenant isolation (IDOR), audit columns, mass-assignment, documentation.

## Review dimensions (context for scoring)

- **Naming / consistency** — one convention throughout; reserved words avoided; abbreviations team-canonical.
- **Privacy / security** — PII/PHI identified + protected; tenant-isolation columns present; no unguarded mass-assignable fields; audit trail present.
- **Documentation** — column comments for non-obvious fields; enum values documented; no "what is this?" columns.

## Naming / consistency checklist

- All identifiers `snake_case` — no camelCase/PascalCase → 🔵 LOW
- Tables: pick singular **or** plural and enforce everywhere (plural is dominant) → 🔵 LOW on inconsistency
- No Hungarian prefixes (`tbl_`, `col_`, `sp_`) → 🔵 LOW
- FK columns named `<referenced_singular>_id` (e.g. `user_id` → `users.id`) → 🔵 LOW
- Boolean columns `is_*` / `has_*` (e.g. `is_active`) → 🔵 LOW
- Datetime columns `*_at` (`created_at`, `deleted_at`); date-only `*_date` → 🔵 LOW
- Enum-like columns `<noun>_status`/`_type`/`_state`, never bare `status` → 🔵 LOW
- Index/constraint names consistent (`idx_<table>_<cols>`, `fk_`, `uq_`, `chk_`) → 🔵 LOW
- No SQL reserved words as identifiers (`user`, `order`, `value`, `type`, `offset`, `limit`, `group`) → 🟡 MEDIUM (quoting bugs)
- Novel undocumented abbreviations introduced silently → 🔵 LOW

## Privacy / security checklist

- **Tenant-isolation column** (`org_id`/`organization_id`) present, `NOT NULL`, indexed on every tenant-scoped table — missing → 🔴 CRITICAL (IDOR / cross-tenant leak surface). *(Verify the full chain before reporting CRITICAL.)*
- **PII / PHI columns** (email, phone, name, SSN, DOB, address, IP) identified with a documented decision: encrypted-at-rest, tokenized, or justified plaintext — undocumented → 🟠 HIGH
- **Sensitive flag columns** (`is_admin`, `role`, `permissions_mask`, `subscription_tier`) not in user-controlled input surface; DTO/allowlist separation documented — otherwise → 🔴 CRITICAL (mass assignment / privilege escalation)
- **Audit columns** present on mutable tables: `created_at NOT NULL`, `updated_at NOT NULL` (+ `created_by_id`/`updated_by_id` for sensitive data) — absent → 🟠 HIGH
- **Soft-delete** (`deleted_at`/`is_deleted`): if used, every query surface must filter it; document whether hard-delete is used for PII erasure (GDPR/CCPA) — unfiltered → 🟠 HIGH
- **Encryption annotation** on credential/token/payment/PHI columns names the strategy — missing → 🟠 HIGH
- **No secrets in defaults** — no `DEFAULT 'password'`, default API keys, secret-looking seeds → 🔴 CRITICAL
- **Encrypted column not in a plaintext index** — index on an encrypted PII column that defeats the encryption → 🟠 HIGH
- **Retention/erasure path exists** — schema supports bulk delete/anonymize of a user's PII; FK cascades configured so soft-delete doesn't orphan PII → 🟡 MEDIUM
- **Mass-assignment surface** — server-managed columns (role, status transitions, financial totals) flagged as not-user-settable; recommend DTO/allowlist → 🟠 HIGH

## Severity quick map

- 🔴 CRITICAL: missing tenant-isolation column on a multi-tenant table; sensitive flag in mass-assignable surface; secret in a column default
- 🟠 HIGH: undocumented PII/PHI handling; missing audit columns on mutable tables; unfiltered soft-delete; missing encryption annotation; plaintext index on encrypted PII; unguarded mass-assignment surface
- 🟡 MEDIUM: reserved-word identifier; missing retention/erasure path
- 🔵 LOW: naming-convention deviations; missing column comments; abbreviation inconsistency

## Documentation checklist

- Non-obvious columns lack a comment → 🔵 LOW
- Enum/finite-set values undocumented → 🔵 LOW
- Migration intent uncommented where non-obvious → 🔵 LOW

## Sources

- [sqlstyle.guide (Simon Holywell)](https://www.sqlstyle.guide/)
- [OWASP — Mass Assignment Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Mass_Assignment_Cheat_Sheet.html)
- [Google eng-practices — standard of code review](https://google.github.io/eng-practices/review/reviewer/standard.html)
- [Atlassian — security severity levels](https://www.atlassian.com/trust/security/security-severity-levels)
- [Bytebase — table naming: singular vs plural](https://www.bytebase.com/blog/sql-table-naming-dilemma-singular-vs-plural/)
- [OWASP API Security — BOLA/IDOR & sensitive data](https://www.wiz.io/academy/api-security/owasp-api-security)
