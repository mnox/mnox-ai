# Severity Rubric, Confidence & Finding Format

Shared by every lens. All findings use this severity scale, confidence labeling, and output format.

## Severity scale

- 🔴 **CRITICAL** — Data corruption is possible, a security exploit is directly enabled, or the decision is irreversible / fatal-at-scale and brutally expensive to fix later. Merge blocker.
- 🟠 **HIGH** — Integrity, performance, or evolvability defect that must be fixed before merge.
- 🟡 **MEDIUM** — Design drift or compounding tech debt. Should fix; acceptable to defer with a ticket.
- 🔵 **LOW** — Convention, documentation, or observability gap. Author's discretion.
- ⚪ **NITPICK** — Cosmetic. Noted, not scored.

## Confidence

Prefix HIGH/CRITICAL findings with a confidence label: `[confidence: HIGH | MEDIUM | LOW]`.

- Use **MEDIUM/LOW** when the finding depends on an assumption you cannot confirm from the artifact alone (e.g. "this column is *probably* queried on a hot path", "this table is *expected* to grow large").
- **Never escalate severity to compensate for low confidence.** Lower confidence lowers the severity floor. A CRITICAL claim you cannot fully chain is a HIGH-at-most until verified.
- CRITICAL and HIGH findings must have their full failure/attack chain verified before they ship in a report.

## Finding format

```
**[🟠 HIGH] `users.org_id` — missing index on tenant-scope FK**  [confidence: HIGH]
`org_id` is a foreign key and the primary tenant-scope filter column, with no index.
Impact: every tenant-scoped query against this table is a full table scan at scale; also widens the IDOR blast radius.
Fix: `CREATE INDEX CONCURRENTLY idx_users_org_id ON users (org_id);`
Blocker: yes.
```

Every finding includes, in order:
1. **Severity + location** — exact table.column, file:line, module, or migration step.
2. **Confidence** — for HIGH/CRITICAL.
3. **Problem** — one factual sentence, no editorializing.
4. **Impact** — what breaks, corrupts, or becomes exploitable if unfixed.
5. **Fix** — concrete DDL / migration / type change. Not "consider…".
6. **Blocker?** — explicit yes/no. CRITICAL and HIGH are blockers by default; call out exceptions.

## Tone

Facts and impacts only. Never mock or attribute blame to whoever wrote the existing schema — not even a casual aside. Imperative recommendations ("Add…", "Replace…", "Split…"), never hedged suggestions.
