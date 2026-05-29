---
name: debut
description: "Audit a personal open-source repo for public-readiness before going public or pushing to its public git history — secrets/PII in history, licensing, README & community-health files, code quality, tests/CI, deps & releases. Produces a scored report (SHIP IT / NEEDS POLISH / NOT READY) with exact fix commands. Use when: '/debut', 'is this repo ready to go public', 'oss readiness audit', 'public-ready check', 'audit my repo before open-sourcing', 'is this presentable', 'pre-publish audit'. Adaptive: full-repo readiness sweep or lighter pre-push diff mode. Draft-only, flag-only — never commits, never auto-fixes, never rewrites history."
context: fork
---

# debut

Multi-agent **open-source readiness auditor**. Tells a perfectionist maintainer
whether a personal repo is clean, presentable, and SAFE enough to go public or to
push to its public git history. Fans out 6 domain agents, scores the repo /100,
and returns a verdict — **SHIP IT / NEEDS POLISH / NOT READY** — with exact,
copy-pasteable fix commands. It never commits, never pushes, never auto-fixes, and
never rewrites history. It flags; the maintainer decides.

## Context-hygiene contract (NON-NEGOTIABLE)

- **The main thread is a coordination layer ONLY.** Never grep, glob, or
  read-for-discovery in the orchestrator. **ALL scanning is delegated to the 6
  domain sub-agents.** The one allowed exception is the Phase 3 validation gate
  (targeted re-reads of CRITICAL/HIGH evidence only — verification, not
  exploration).
- **Stay below ~35% context** in the orchestrator. The main thread holds only:
  the input, the signals JSON path, per-agent ≤400-word summaries, sub-scores, and
  the final synthesis. Sub-agents write full detail to temp files; the main thread
  reads summaries, not dumps.
- **Phase 0 runs `scripts/collect_signals.py` ONCE** (cheap deterministic SAFE
  pre-scan) and passes each agent only its domain slice + the repo path. Agents run
  their own heavier domain tool scans (gitleaks/trufflehog/eslint/tsc/npm audit/…).

## Overview

`debut` answers one question: *"is this repo worthy of the public eye, and is it
safe to expose?"* It grades 6 domains — secrets/history, community-health,
licensing, code-quality, tests-ci, deps-release — each weighted by stakes (secrets
dominate at 30/100 because a leak is catastrophic and often irreversible). The
output is a scored markdown report with severity-grouped findings, a domain-score
breakdown, validation notes, and an honest record of what was skipped or ran
degraded. An optional self-contained HTML report is offered on request.

## Quick Reference

**Modes** (auto-detected; state which in one line):

| Mode | When | What runs |
|------|------|-----------|
| **READINESS (full)** | DEFAULT | All 6 domains over the whole repo + full git history |
| **PRE-PUSH (diff)** | unpushed commits exist (`git log @{u}..` non-empty) AND intent is pre-push, OR a diff scope is passed | secrets-history (on the diff + new commits' messages/content), code-quality (changed files only), licensing/deps DELTA. Skips full community-health unless relevant files changed |

Explicit override: user can say **"full"**, **"diff"**, or scope it (e.g. **"just secrets"**).

**Domains & weights** (sum = 100 — see `references/scoring-rubric.md`):

| # | Domain | Weight | Agent file |
|---|--------|:------:|-----------|
| 1 | secrets-history | 30 | `agents/secrets-history.md` |
| 2 | community-health | 20 | `agents/community-health.md` |
| 3 | licensing | 15 | `agents/licensing.md` |
| 4 | code-quality | 15 | `agents/code-quality.md` |
| 5 | tests-ci | 10 | `agents/tests-ci.md` |
| 6 | deps-release | 10 | `agents/deps-release.md` |

**Verdict bands:** 🟢 **SHIP IT** (≥85, no criticals) · 🟡 **NEEDS POLISH** (60–84)
· 🔴 **NOT READY** (<60). **Hard-blocks:** verified secret/PII in tree or history →
🔴 NOT READY; no LICENSE → caps at 🟡 NEEDS POLISH (never SHIP IT).

**Severity ladder:** 🔴 CRITICAL · 🟠 HIGH · 🟡 MEDIUM · 🔵 LOW · ⚪ NIT.

**Flags:** `--html` (also render the HTML report) · `full` / `diff` / scope words.

## Workflow

### Phase 0 — Preflight, signal collection, mode detection (main thread, ~10s)

1. **Resolve the target repo path** (default cwd) and derive a kebab-case `<slug>`
   from the repo dir name. `mkdir -p /tmp/debut-<slug>`.
2. **Prior-context sweep** (optional, if you have memory/history tooling available):
   - If a memory-graph or session-tracker MCP is available, search the repo name /
     topic for prior decisions or known issues; carry as priors and verify before
     relying (precedent ≠ correctness). Skip if unavailable.
3. **Run the SAFE pre-scan ONCE:**
   `python3 scripts/collect_signals.py --repo <path> --out /tmp/debut-signals-<slug>.json`
   (PEP 723, stdlib-only, read-only). This yields the file-presence matrix,
   tracked-cruft list, tool-availability probe, unpushed-commit count, tsconfig
   `strict` parse, package.json summary, SemVer-tag presence, and bounded
   commit-message smell hits.
4. **Detect mode** from the signals: unpushed commits + pre-push intent (or a
   passed diff scope) → **PRE-PUSH (diff)**; else → **READINESS (full)**. Honor
   explicit overrides. **State the chosen mode in one line.**

### Phase 1 — Fan-out (spawn all 6 domain agents in a SINGLE message)

Spawn **all 6 domain agents in ONE message** (one Agent call each, same message),
`subagent_type: general-purpose`, default model **sonnet**. In diff mode, still
spawn the relevant subset in one message (secrets-history, code-quality,
licensing+deps delta) and tell each it is diff-scoped.

Pass each agent ONLY: the repo path, the signals JSON path
(`/tmp/debut-signals-<slug>.json`), its temp output path
(`/tmp/debut-<slug>/<domain>.md`), the mode, any priors, and (diff mode) the diff
scope. Each agent runs its own domain tool scans, writes full detail to its temp
file, and **returns a ≤400-word structured summary including its sub-score and the
arithmetic**. The main thread keeps summaries + sub-scores only.

### Phase 2 — Aggregate & score (main thread)

Collect the 6 sub-scores. Sum to `overall /100` per `references/scoring-rubric.md`.
Deduplicate findings raised by more than one agent against the same evidence (keep
the highest severity). Build the domain-score breakdown table (show the math). Do
NOT finalize the verdict yet — validation can change the score.

### Phase 3 — Validation gate (the one allowed main-thread read exception)

Re-verify **every 🔴 CRITICAL and 🟠 HIGH finding** in the main context. For secret
hits especially: confirm it is a real/live credential, not a test fixture or
placeholder, to kill false positives. Targeted reads only — verification, not
exploration. **Demote or drop** anything that doesn't survive; only validated
findings count toward the score. Recompute sub-scores and `overall`. Apply
hard-block overrides (verified secret/PII → NOT READY; no LICENSE → cap at NEEDS
POLISH). Settle the verdict.

### Phase 4 — Report, offer HTML, offer memory

1. **ALWAYS write** the markdown report to
   `/tmp/debut-<slug>-<YYYY-MM-DD>.md` using `templates/report.md`. Lead with:
   verdict + score/100 + mode + severity-count table + domain-score breakdown; then
   findings grouped by severity; then validation notes + what was skipped/degraded
   (e.g. "trufflehog not installed → degraded secret scan"). **No local file paths
   in anything destined for external sharing.**
2. **Print** a ≤200-word inline summary: verdict, score, top findings, report path.
3. **OFFER (don't auto-render)** the self-contained HTML report via
   `templates/audit.html` (gauge for the score) when the user wants it or passed
   `--html`.
4. **OFFER (never auto-run)** `/mem` to persist notable findings after a
   substantive run.

## Common Mistakes

### ❌ Researching in the main thread
**Problem:** reaching for Grep/Glob/Read to "just check" a file in the orchestrator.
**Why wrong:** it pollutes the coordination layer and blows the context budget.
**✅ Fix:** delegate every scan to a domain agent. Read only in Phase 3 to verify a CRITICAL/HIGH.

### ❌ Spawning agents one at a time
**Problem:** sequential Agent calls across multiple messages.
**Why wrong:** serializes a parallel fan-out, wastes wall-clock, breaks the contract.
**✅ Fix:** spawn all 6 (or the diff subset) in a SINGLE message.

### ❌ Shipping unvalidated criticals
**Problem:** passing an agent's CRITICAL secret hit straight into the report.
**Why wrong:** agents over-report; a placeholder/fixture flagged as a live secret is a false NOT-READY.
**✅ Fix:** re-verify every CRITICAL/HIGH in Phase 3. Demote/drop what doesn't survive.

### ❌ Running or suggesting auto-fixes / history rewrites
**Problem:** running `git filter-repo`, committing a `.gitignore`, or "fixing" lint.
**Why wrong:** debut is flag-only; history rewrites are destructive and un-leak nothing.
**✅ Fix:** mark history fixes `destructive: true`, give the command, prepend "rotate the credential FIRST", never run it.

### ❌ Fabricating findings for a stack you didn't run
**Problem:** reporting eslint findings on a Python repo.
**Why wrong:** invents failures and erodes trust.
**✅ Fix:** detect the language; run the real equivalent or mark N/A with a note.

## Failure modes to avoid

- **Hidden degraded mode.** If gitleaks/trufflehog/gh/tsc are absent, the report MUST say so — a degraded secret scan that reads "clean" is dangerous.
- **Scoring dropped findings.** Only Phase-3-validated findings subtract from sub-scores.
- **Ignoring hard-blocks.** A 95/100 repo with a verified live secret is still 🔴 NOT READY. No LICENSE caps at 🟡 NEEDS POLISH.
- **Leaking local paths externally.** Strip `/Users/...`, internal hostnames, and personal emails from anything meant to be shared.
- **Diff mode scoring like full mode.** Renormalize against the domains that actually ran and label the score as partial.
