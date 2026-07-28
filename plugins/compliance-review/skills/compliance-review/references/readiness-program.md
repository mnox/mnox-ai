# SOC 2 Readiness Program

Loaded in **`readiness` mode** only. The other modes audit a technical target for
control gaps; readiness mode assesses whether an organization can *pass an
examination* — which is a different question with different failure modes, most of
them evidentiary rather than technical.

The deliverable is a risk register with discovery steps, fix/prevent actions, and
cost-of-inaction — plus a dependency-ordered phase plan. Not a list of code bugs.

## Severity crosswalk

Readiness findings use the skill's standard severity ladder, mapped to audit
consequence:

| Severity | Readiness meaning |
|----------|-------------------|
| Critical | Blocks the examination outright, or produces a qualified opinion |
| High | Audit exception likely; or an evidence gap that can force a window restart |
| Medium | Finding/cleanup; slow-bleed governance debt |
| Low | Hardening; minor deviation |
| Info | Observation |

**Weight evidence gaps heavily.** A technical control that works but produces no
retained evidence is a High in readiness mode even though a code review would call
it clean — because it cannot be tested over a Type II window.

## Risk register — the fifteen recurring gaps

Each entry: why it matters · how to discover it · fix/prevent · cost of inaction.
Use these as the checklist backbone; the control IDs point into
`references/soc2.md`.

### Critical

**Dependency CVEs (critical/high)** — `SOC2-CC7.1`, `CC7.1-SLA`
Discovery: SCA scan (Snyk, Grype, osv-scanner) against lockfiles; verify lockfiles
exist at all; inventory transitive deps.
Fix: upgrade and pin; SCA in CI as a **blocking** gate; documented patch SLA;
quarterly third-party library review.
Cost: rejected releases and re-review cycles; dead calendar time against a launch
date.

**Secrets in code / plaintext secrets** — `SOC2-CC3.2`, `CC6.1`
Discovery: **full git-history** scan (gitleaks, trufflehog), not just HEAD; grep
configs, IaC, CI variables, seed files.
Fix: rotate everything found — **history scrubs are cosmetic, rotation is the
fix** — move to a secrets manager, add secret-scanning as a pre-merge CI gate.
Cost: if a leaked credential is ever exercised, incident response and disclosure
dwarf all audit spend combined.

**Missing mandatory audit deliverables** — `SOC2-PROG.1`, `PROG.2`
Discovery: ask who is drafting the system description and who signs the assertion.
On a small team with no exec ops function, the usual answer is that nobody has
thought about it.
Fix: draft the system description early; identify the signer; give the assertion
real review time.
Cost: **the examination cannot begin without the signed assertion.**

### High

**Over-broad privilege grants** — `SOC2-CC6.3-LP`
Discovery: diff granted/declared privileges against what the code actually
exercises; flag blanket grants.
Fix: narrow to exercised privileges; document each with rationale.
Cost: review friction; enterprise customers read privilege scope during security
review and over-asking loses deals silently.

**No change-management enforcement** — `SOC2-CC8.1`, `-SEG`, `-TRACE`
One of the two most common first-audit exceptions: approvals living in chat
instead of a tracked workflow.
Discovery: check branch protection (force-push, required reviews, admin bypass);
sample recent merges for review evidence; check required CI status enforcement.
Fix: branch protection, required reviews, required CI, PR template linking change
to issue. Cheap — the cost is discipline.
Cost: qualified report, or compensating evidence sampled at much higher volume,
billed as hours.

**Access reviews that never generate evidence** — `SOC2-CC6.3-AR`
The other most common first-audit exception. The reviews happen; they are never
saved.
Discovery: "show me last quarter's access review." A shrug is the finding.
Fix: quarterly calendar with a named owner; export/screenshot with timestamps into
an evidence repo; automate via compliance-platform integrations.
Cost: **an exception spanning the whole Type II window cannot be fixed
retroactively — the window restarts.**

**Engineers debugging against live customer data** — `SOC2-C1.1-DBG`, `C1.1-FIX`
Discovery: interview the debugging workflow; check staging/dev data provenance;
grep fixtures and seeders for real-looking data.
Fix: synthetic seeders sufficient to reproduce customer-shaped bugs; anonymization
pipeline where prod-derived data is unavoidable; prod reads behind logged
break-glass.
Cost: confidentiality exception plus contract-breach exposure — customer DPAs
generally prohibit it outright.

**No audit trail on data access** — `SOC2-CC7.2-ATTR`
Discovery: trace a sample data access end-to-end; identify every path with no
attribution — service accounts, shared credentials, direct database access.
Fix: centralized access logging with identity attribution; eliminate shared
accounts; convert standing prod access to logged break-glass.
Cost: exception, plus inability to answer "what did the attacker touch," which
converts a contained incident into a full-disclosure event.

**PII/secrets in logs** — `SOC2-C1.1-LOG`
Discovery: sample log output across services; grep log statements for raw object
dumps, request bodies, headers.
Fix: structured logging with allowlisted fields (deny-by-default); scrubbing at a
single choke point; log-content tests in CI.
Cost: confidentiality finding whose exposure is historical and growing with
retention — fix cost compounds monthly.

**Untested incident response / disaster recovery** — `SOC2-CC7.4-IR`, `A1.3-DR`
An IR plan that exists but was never exercised fails.
Discovery: "when did you last restore from backup?" and "when was the last
tabletop?" Two questions, usually two silences.
Fix: one documented tabletop with dated participants and findings, plus one timed,
documented restore drill. The cheapest exceptions in the program to prevent.
Cost: an exception — and a real incident during the window turns the post-incident
review into audit evidence against you.

**Thin coverage on CC1–CC5** — `SOC2-CC1.*`–`CC5.*`
Engineering-led programs over-index on CC6/CC7/CC8 and under-build governance,
communication, and monitoring.
Discovery: map existing controls to CC1–CC9 and look for **series with zero
entries**.
Fix: code of conduct with acknowledgments; documented org structure and authority;
an oversight cadence appropriate to company size; internal and external security
communication paths; a monitoring routine that surfaces control failures rather
than discovering them at audit time.
Cost: a CC-series with no controls is a **design gap — it fails at Type I**, not
just Type II.

**No controls matrix** — `SOC2-PROG.3`
Discovery: ask for the matrix. A policy folder is not a matrix.
Fix: build it alongside the evidence machine; compliance platforms generate a
usable starting version once integrations are connected.
Cost: without the mapping, evidence gaps stay invisible until fieldwork — the
point at which they can no longer be fixed inside the current window.

### Medium

**Governance paper** — `SOC2-PROG.4`, `CC3.2-RA`, `CC9.2`
Every technical control needs a governing policy: exec-approved, dated, with
employee acknowledgment logs. Plus an annual risk assessment and a vendor
inventory holding subprocessors' SOC 2 / ISO reports.
Discovery: inventory what exists against the core policy stack (infosec, access,
change mgmt, IR, BC/DR, data classification & retention, vendor risk, acceptable
use, HR security).
Fix: templates cover most of the writing; the real work is making policies match
actual practice.
Cost: slow-bleed findings. **Worst case is a policy that contradicts practice,
which is worse than no policy.**

**Endpoint/laptop posture** — `SOC2-CC6.8-EP`
Discovery: a short survey of the in-scope machines.
Fix: lightweight MDM, or documented and attested configuration for a small team.
Cost: a minor finding, but an embarrassing one to fail at small n.

## Phase plan

Ordering logic: highest-exposure and release-blocking items first, then
evidence-machine prerequisites (**evidence cannot be backfilled into an
observation window**), then durability. No arbitrary calendar targets — the only
hard time constraints are listed below.

### Phase 1 — stop the bleeding
- Full git-history secret scan, rotate findings, secrets manager, CI secret-scan gate
- SCA scan, remediate critical/high CVEs, CI dependency gate, documented patch SLA
- Privilege audit: narrow to minimum exercised, document
- Branch protection, required reviews, required CI
- Kill standing prod access, eliminate shared credentials
- Endpoint survey, encryption/lock verification

**Exit criterion:** no known critical technical exposure; releases unblocked.

### Phase 2 — stand up the evidence machine (**must complete BEFORE the Type II window opens**)
- Compliance platform selected, integrations connected (cloud, VCS, IdP, MDM)
- Policy stack drafted, adjusted to actual practice, exec-approved, acknowledged
- Access review #1 executed and saved, establishing the quarterly cadence and evidence format
- Centralized logging with identity attribution, PII scrub choke point, log-content CI test
- Synthetic seeders for the top customer-bug archetypes; prod-data debugging path closed
- Controls matrix built: each in-scope criterion → control statement, owner, evidence source, test cadence
- CC1–CC5 gap pass: code of conduct, org structure and authority, oversight cadence, security communication paths, monitoring routine
- Vendor inventory, subprocessor SOC 2 reports collected

**Exit criterion:** every control has a named owner and an operating cadence. Only
now can the observation window start. This gate, plus the window itself, sets the
true floor on time-to-Type-II.

### Phase 3 — durability and audit engagement (runs during the window)
- IR tabletop exercised and documented; restore drill timed and documented
- Risk assessment performed and documented
- Auditor selected, formal scoping session, decision on Type I vs Type II window length
- Pen test scheduled
- System description drafted; assertion signer identified
- Security awareness training delivered, acknowledgments recorded
- Quarterly cadences calendared with owners: access reviews, dependency review

**Exit criterion:** Type I achievable at any point once Phase 2 controls are
designed. Type II follows the full observation window plus fieldwork.

## Hard time constraints

- **Type II observation window: 3–12 months minimum by definition.** The report
  attests controls operated over a period. The window cannot be compressed, and
  mid-window evidence gaps cannot be backfilled — the window restarts.
- **Access reviews: quarterly** is the standard cadence auditors test against.
- **Dependency review: quarterly** is the commonly recommended cadence; one
  cadence can satisfy both the vulnerability-management control and any
  distribution-channel review requirement.
- **Published end-to-end ranges:** Type I typically 1–3 months including
  preparation. Type II 6–15 months because of the mandatory observation period.
  Reported industry data puts 56% of organizations at 3–6 months in the
  preparation phase alone, with compliance automation cutting preparation time by
  roughly 40%.

## Cost model

**Auditor fees** (national directory data, 171 CPA firms, soc2auditors.org, June
2026): specialist-tier CPA firms — which fit a small single-product scope —
typically quote roughly **$10–20K for Type I** and **$15–30K for Type II**.

*Example local shortlist (Utah/SLC, illustrative — regenerate for the actual
geography):* Tanner LLC (Salt Lake City), with a dedicated SOC 2 examination
practice and local-reference advantage; Barnes Dennig, serving SLC clients for SOC
1/2/3 and readiness assessments, remote-first.

**Filter warning:** many local "CPA" shops are tax/bookkeeping and explicitly do
not perform attest services. Attestation requires an AICPA-licensed firm doing SOC
work specifically. And a bargain audit from a firm enterprise buyers do not
recognize can get bounced in customer security review — **optimize for
recognizable legitimacy, not lowest bid.**

**Compliance automation platform:** Hicomply from ~$7K/yr with an 8–12 week
readiness claim (auditor fees separate); Vanta, Drata, and Secureframe are the
incumbents. Pricing is negotiable at this scale and moves yearly — get live quotes.

**Other line items:**
- Pen test — expected for Type II by most auditors and customers; get current quotes.
- Mock audit / formal readiness assessment — bundled with most platforms, or
  standalone via a CPA firm or consultant. Recommended for a first-time team: it
  surfaces "we do this but never saved proof" failures before they can kill the
  window.
- IR tabletop — can be run internally and documented at no cash cost, or
  facilitated externally.
- **Engineering time is the dominant real cost.** Whether Phase 2 items are
  configuration work or construction work depends entirely on how the system was
  built.

**Cost of delay:** evidence gaps discovered mid-window cannot be backfilled — the
window restarts and the full 3–12 months elapses again before a Type II report is
possible. The asymmetry to state plainly: prevention for most register items is
configuration-scale work, while post-hoc fixes are bounded below by that mandatory
window restart.

## Free public resources

- **strongdm/comply** (Apache-2.0, ~1.6k stars) — open-source policy and procedure
  templates suitable for satisfying a SOC 2 audit, plus a markdown document
  pipeline and ticketing integration for Jira, GitHub, GitLab. 24 pre-authored
  policies edited directly in markdown and version-tracked in git. Last release
  v1.6.0 (2021): treat the tooling as dated and the policy text as a starting
  draft, not a finished stack.
- **getprobo/probo** — actively maintained open-source SOC 2 / GDPR / ISO 27001
  platform, self-hostable. Worth evaluating against paid platform pricing.
- **soc2.fyi** (Rhosys, open source) — plain-language guide to the attestation and
  its costs.
- **Petronella SOC 2 toolkit** (GitHub) — trust service criteria checklists,
  control matrices, and risk assessment templates. Useful as a cross-check against
  the controls matrix.
- **Cloud provider SOC reports** — AWS SOC 3 is publicly available as a whitepaper;
  SOC 2 under NDA. Satisfies part of the vendor inventory.

**Caveat on all of the above: templates get you a draft, not a program.** Auditors
test the gap between what policies say and what the team actually does, so every
template needs editing down to actual practice before it helps.

## Reporting notes for readiness mode

- Report `program`-type controls as **findings**, not Out-of-Scope items — their
  absence is the subject of the review. Out of Scope in readiness mode is reserved
  for things the reviewer genuinely could not reach (e.g. no access to the policy
  repository).
- Every register entry gets all four parts: **why it matters · discovery ·
  fix/prevent · cost of inaction.** The cost line is what makes the report
  actionable to a decision-maker; omit it and the report reads as a chore list.
- Distinguish "control absent" from "control present but unevidenced." They have
  different fixes and very different schedule consequences.
- Do not invent calendar dates. State dependencies and the hard constraints above;
  let the team place them on a calendar.
