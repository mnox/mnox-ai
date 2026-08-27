# GDPR Skill — Research Brief

Synthesized from four parallel web-research passes (prior art, legal substance, engineering checks, skill-authoring practice) on 2026-08-27. This is the input document for building the skill.

## Verdict on prior art

The space is populated but not solved. Nothing in the user's claude.ai skill/plugin catalog covers GDPR. Publicly:

| Source | What it is | Use |
|---|---|---|
| [Sushegaad/Claude-Skills-Governance-Risk-and-Compliance](https://github.com/Sushegaad/Claude-Skills-Governance-Risk-and-Compliance) | 33 GRC skills incl. dedicated GDPR (EU+UK). MIT, 858★, v1.8.0, 165+ eval cases, current through 2026 | Best existing GDPR *advisor* skill; the bar to beat |
| [mukul975/privacy-data-protection-skills](https://github.com/mukul975/privacy-data-protection-skills) | 282+ privacy skills, 50+ GDPR-specific. Apache 2.0, marketplace-installable | Quarry for citations, enforcement precedents, templates |
| [alirezarezvani/claude-skills gdpr-dsgvo-expert](https://github.com/alirezarezvani/claude-skills/blob/main/ra-qm-team/skills/gdpr-dsgvo-expert/SKILL.md) | GDPR+BDSG with codebase-scanning, DPIA-generator, DSR-tracker scripts | Closest to a code-audit skill; German slant |
| [anthropics/knowledge-work-plugins compliance-check](https://github.com/anthropics/knowledge-work-plugins/blob/main/legal/skills/compliance-check/SKILL.md) | Official legal skill with heavy GDPR content, reviews initiatives not code | Best official precedent for report format |
| [wshobson/agents gdpr-data-handling](https://skills.sh/wshobson/agents/gdpr-data-handling) | "Build it compliant" implementation guide | Developer-guidance angle |
| Local `plugins/compliance-review` | This repo's SOC 2/HIPAA/PCI multi-agent audit skill | **The direct structural template** |

**Differentiated play:** no one has built a GDPR skill shaped like `compliance-review` — mode-detecting, multi-agent, structured findings with article IDs, evidence, severity, confidence, and an honest human-attestation boundary. Build that (as a sibling plugin or a fourth framework inside compliance-review), quarrying the repos above for content rather than re-treading advisory ground.

## Legal substance to encode

Hard numbers as deterministic checks: 72h breach notice to DPA (Art. 33) + internal register of ALL breaches (33(5)); 1-month DSAR response, +2-month extension noticed within the first month (Art. 12); RoPA exemption <250 employees (Art. 30) — Omnibus IV would raise to <750, flag as *proposed*; parental consent under 16 (member-state floor 13); fine tiers €20M/4% vs €10M/2%.

Per-domain criteria (full detail in agent report):
- **Art. 5 principles** — each demonstrable under 5(2) accountability; retention implemented in code, not just policy.
- **Art. 6/7/9** — exactly one documented basis per purpose, chosen before processing; LI needs a documented 3-part balancing test; contract necessity read narrowly (Meta ruling: behavioral ads fail); consent = affirmative act, granular, withdrawal one-click, records versioned; special categories need Art. 6 AND an Art. 9(2) exception; inferred sensitive data counts.
- **Arts. 12–22 DSR** — access/rectification/erasure/restriction/portability (structured machine-readable)/objection (absolute for direct marketing)/ADM (SCHUFA: credit scoring is an Art. 22 decision; meaningful-logic explanation required).
- **Art. 25/28/30/35/37** — privacy-by-design gate in SDLC; written DPA with all 28(3) clauses per vendor; RoPA matching real flows; DPIA screening with DPA blacklists; DPO independence.
- **Chapter V transfers** — adequacy (incl. EU-US DPF: upheld Sept 2025 General Court, CJEU appeal C-703/25 P pending — valid-but-watch, recommend SCC fallback), 2021 SCCs + documented TIA post-Schrems II, UK IDTA.
- **2025–26 developments** — EDPB Opinion 28/2024 (AI models not automatically anonymous; LI workable for training with full test), Guidelines 01/2025 pseudonymisation, draft 02/2026 anonymisation & 03/2026 web scraping; Digital Omnibus (COM(2025) 837) would fold cookie consent into GDPR and recognize LI for AI training — *proposed, verify at review time*; AI Act applies cumulatively (DPIA + FRIA for high-risk, enforceable Aug 2, 2026).
- **Enforcement weighting** — TikTok €530M (China transfers), LinkedIn €310M (ad-tech basis), Uber €290M (transfers), Meta €251M (Art. 25/breach). Weight transfers, ad-tech lawful basis, dark-pattern consent, children's data, breach registers, DPA completeness highest.

## Engineering checks (code/IaC mode)

Sequence: **build the PII inventory first** (grep schemas/models for PII-indicative columns, flag Art. 9 columns high-severity, check unexpected stores: search indexes, caches, event schemas, warehouses, queues). Every later check diffs against that inventory — the **coverage-diff pattern** is the highest-value technique: PII columns vs. deletion-path coverage, code-derived vendor list vs. documented processor list, PII stores vs. encrypted stores.

By category (mechanical vs. judgment flagged in full report):
1. **Logs** — PII interpolation in log calls, whole-object dumps, redaction layer presence (pino redact, Rails filter_parameters), Sentry `sendDefaultPii`, PII in query strings, log retention bounds.
2. **Retention/deletion** — soft-delete (`deleted_at`, paranoid) without stage-2 purge job = finding; cascade completeness across FKs, blobs, indexes, vector DBs; backups need bounded retention + deletion replay or crypto-shredding.
3. **Consent** — record schema (who/when/version/purposes), granular per-purpose, checked at point of use, withdrawal propagates; frontend scripts (GA, Meta Pixel) not loaded unconditionally pre-consent; GPC handling; TCF v2.3 if adtech.
4. **Anonymization** — unsalted `sha256(email)` claimed as anonymized = finding (pseudonymized at best; still personal data); key separation from data; quasi-identifier survival in "anonymized" exports; prod snapshots into staging unscrubbed.
5. **Art. 32** — `storage_encrypted` in IaC, TLS floors, Argon2/bcrypt, secret scanning, admin-access audit logging, least-privilege IAM on PII buckets.
6. **Minimization** — full-model serialization vs. DTOs, unjustified required fields, raw email in analytics `track()` properties, raw IP storage.
7. **DSAR plumbing** — export covering the full inventory, erasure fan-out to processor APIs (OpenDSR/mParticle pattern), request queue with 30-day tracking.
8. **Vendors/transfers** — SDK/API-client inventory from imports; mobile SDKs initializing pre-consent; LLM API prompts as processor flows; IaC region-pinning when EU residency claimed.

Reference tooling: [Fides/fideslang](https://github.com/ethyca/fides) (privacy-as-code taxonomy, DSR graph traversal), [Presidio](https://github.com/microsoft/presidio) (PII scanning), [OpenDSR spec](https://github.com/opengdpr/OpenDSR/blob/master/specification.md), LINDDUN threat modeling, [OWASP Top 10 Privacy Risks v2](https://owasp.org/www-project-top-10-privacy-risks/).

## Recommended skill structure

Sibling plugin mirroring compliance-review:

```
plugins/gdpr-review/
├── .claude-plugin/plugin.json
└── skills/gdpr-review/
    ├── SKILL.md                        # ~300–450 lines
    └── references/
        ├── lawful-basis.md             # Art. 6/7/9
        ├── data-subject-rights.md      # Art. 12–23
        ├── security-and-breach.md      # Art. 25/32/33/34
        ├── transfers-and-processors.md # Art. 28/44–49
        ├── accountability-program.md   # Art. 5(2)/30/35/37 (mostly program-type)
        ├── tracking-and-consent-ux.md  # cookies/ePrivacy, dark patterns
        └── scope-boundaries.md         # attestation-only items
```

Reference-file row format (the compliance-review "automated signal" move): **ID (Art. X(y)) · Requirement · Automated signal · Domain · Type (technical|program)**.

SKILL.md phases: (1) resolve scope — mode auto-detect (code/design/iac/dataflow/readiness) plus GDPR-specific parameters stated before fan-out: controller vs processor role, EU establishment vs Art. 3(2) targeting, special-category data present, ePrivacy in/out; (2) load only in-scope catalogs + scope-boundaries; (3) fan out one agent per domain in a single message; (4) verify Critical/High against quoted evidence before shipping; (5) fixed report template — findings keyed by article ID with severity, `file:line` evidence, remediation, confidence, then **Out of Scope — Legal/Attestation Required**, coverage notes; (6) Common Mistakes (❌/why/fix): "delete endpoint exists" ≠ erasure; consent-stored ≠ consent-valid; pseudonymized ≠ anonymized; LI without balancing-test artifact; citing adequacy/fines from memory instead of live lookup; (7) disclaimers — analysis aid, not legal advice; time-sensitive items (DPF status, Omnibus) verified via web search at review time.

Frontmatter: third-person "pushy" description under 1,024 chars with explicit trigger list (/gdpr-review, GDPR audit, right to be forgotten, DSAR, DPIA, consent flow review, EU user data…); `context: fork`. Note `context: fork` is a Claude Code extension — strip it if publishing to the portable Agent Skills spec.

Authoring rules: SKILL.md < 500 lines; references one level deep with TOCs when > 100 lines; no time-sensitive facts in the body (they go in references, labeled point-in-time); build 3+ eval scenarios first (repo with leaky delete path, design doc missing lawful basis, readiness ask).
