# Security, Privacy by Design & Breach — Art. 25, 32, 33, 34

Columns: **ID** · **Requirement** · **Automated signal** · **Domain** · **Type**.
Type semantics as in `lawful-basis.md`.

## Hard numbers (deterministic checks)

- **Notify the supervisory authority ≤ 72 hours** from *awareness* of a breach,
  unless unlikely to result in risk; late notification requires stated reasons;
  phased notification allowed (Art. 33(1)).
- **Notify data subjects without undue delay** when the breach is *high* risk
  (Art. 34(1)); exceptions: data rendered unintelligible (encryption), subsequent
  risk-removing measures, or public communication where individual notice is
  disproportionate.
- **Internal register of ALL breaches** — including non-notified ones — with
  facts, effects, remediation (Art. 33(5)). A favorite audit item.
- Processors notify the controller **without undue delay** (Art. 33(2)) — the
  clause belongs in every DPA.

## Art. 25 — privacy by design and by default

| ID | Requirement | Automated signal | Domain | Type |
|----|-------------|------------------|--------|------|
| GDPR-25.1 | Data protection embedded in the SDLC | Privacy review gate in the design/PR process; DPIA screening step for new features (see `accountability-program.md`) | 4 | program |
| GDPR-25.2-DEF | Defaults are the most protective | New-account defaults: minimal fields, private-by-default visibility, no pre-enabled sharing/marketing; pre-ticked boxes = finding | 4 | technical |
| GDPR-25-PSE | Pseudonymization/minimization used where feasible | Internal analytics on pseudonymous IDs; PII confined to the systems that need it | 3,4 | technical |

## Art. 32 — security of processing

| ID | Requirement | Automated signal | Domain | Type |
|----|-------------|------------------|--------|------|
| GDPR-32-REST | Encryption at rest on PII stores | IaC: `storage_encrypted` on DBs, encryption blocks on buckets/volumes, TDE; **coverage diff** vs inventory — field-level encryption for Art. 9 data | 4 | technical |
| GDPR-32-TRAN | Encryption in transit | TLS 1.2+ floors on LBs/CDNs, no `http://` internal URLs to PII services, `sslmode=require`+ on DB connections, HSTS | 4 | technical |
| GDPR-32-PWD | Password storage | bcrypt/scrypt/Argon2 only; MD5/SHA1 password paths = Critical | 4 | technical |
| GDPR-32-SEC | Secrets hygiene | Hardcoded credentials in code/config/CI/IaC/history (gitleaks-style patterns); scrubbed-but-not-rotated is unremediated | 4 | technical |
| GDPR-32-ACC | Access control on personal data | Admin PII endpoints behind authz; least-privilege IAM on PII stores; wildcard grants / public bucket ACLs = finding | 4 | technical |
| GDPR-32-AUD | Admin access to personal data is logged | Audit log of who viewed/exported whose record | 4,6 | technical |
| GDPR-32-KEY | Key management | KMS/vault vs keys in env files; rotation configured | 4 | technical |
| GDPR-32.1d | Regular testing and evaluation of measures | Security testing in CI (SCA, SAST), dated pen-test artifacts | 4 | program |
| GDPR-32-RES | Resilience and restore | Backup config exists; restore actually exercised (attestation for the drill itself) | 4 | technical |

## Art. 33/34 — breach readiness (code/IaC-checkable slice)

| ID | Requirement | Automated signal | Domain | Type |
|----|-------------|------------------|--------|------|
| GDPR-33-DET | Breaches are detectable | Alerting on PII stores (anomalous access, exfil-scale reads, auth failures); no detection = "cannot start the 72h clock" finding | 6 | technical |
| GDPR-33-IR | Incident-response plan with the 72-hour clock | Runbook exists defining awareness, severity/risk assessment, DPA-notification decision, and content template (nature, categories, approximate numbers, DPO contact, consequences, measures) | 6 | program |
| GDPR-33.5 | Breach register | A log of all incidents incl. non-notified, with facts/effects/remediation | 6 | program |
| GDPR-34-COMMS | Subject-notification path | Plain-language template and a mechanism to reach affected users | 6 | program |
| GDPR-33.2 | Processor→controller notification clause | Present in DPAs (attestation); for *this* org as processor: an escalation path from on-call to customer notification | 5,6 | program |

## PII leakage into logs (Art. 32 + 5(1)(c)/(e) applied to telemetry)

| ID | Requirement | Automated signal | Domain | Type |
|----|-------------|------------------|--------|------|
| GDPR-32-LOG1 | No PII interpolated into log statements | Log calls (`logger.`, `console.log`, `print(`, structured loggers) interpolating `email`, `req.body`, `params`, `headers`, tokens; whole-object dumps (`JSON.stringify(user)`, `%+v`, `repr(user)`) | 6 | technical |
| GDPR-32-LOG2 | A redaction layer exists | Serializer denylists/allowlists (pino `redact`, Rails `filter_parameters`, logback masking, custom scrubbers); none in a PII-handling app = finding | 6 | technical |
| GDPR-32-LOG3 | No PII in URLs/query strings | GET endpoints taking `email=`/`token=` — these leak into access logs, proxies, browser history | 6 | technical |
| GDPR-32-LOG4 | Error trackers scrubbed | Sentry-style `sendDefaultPii: true` without `beforeSend` scrubbing; local-variable capture on PII paths | 6 | technical |
| GDPR-32-LOG5 | Log pipeline masks or drops before storage; retention bounded | fluentd/logstash/vector filter config; retention: operational 30–90 days norm, security/audit 12–18 months; indefinite = finding | 6 | technical |
| GDPR-32-LOG6 | PII-bearing logs are in DSAR/erasure scope or expire fast enough to be exempt-by-expiry | Logs either covered by the deletion path or short-retention with the tradeoff documented | 2,6 | technical |
