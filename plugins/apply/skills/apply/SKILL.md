---
name: apply
description: "Browser-driven job search and application copilot — locate matching job postings, score fit, tailor the resume / cover letter / screening answers to each individual posting, then drive the application form in a real browser with a human confirmation gate before every submit. Use when: '/apply', 'help me apply to jobs', 'find jobs and apply', 'tailor my resume for this posting', 'apply to this job for me', 'run my job hunt', 'fill out this application'. Truth-locked: emphasis and wording adapt per job, facts never do. Never submits without explicit approval, never handles passwords, never bypasses CAPTCHAs or anti-bot controls."
---

# apply

Browser-driven **job application copilot**. Finds postings that match the
candidate, scores fit, tailors the application materials to each individual
job — resume emphasis, cover letter, screening answers — and then drives the
application form in a live browser session, pausing at a hard confirmation
gate before anything is submitted. Every application is logged to a local
tracker so the hunt has state across sessions.

The skill optimizes for **quality of each application, not volume**. Ten
tailored applications beat a hundred generic ones, and mass-blasting forms is
both ineffective and a fast way to get an account flagged.

## Non-negotiables (read first, apply always)

1. **Truth lock.** Tailoring means re-ordering, re-emphasizing, and re-wording
   what is true. NEVER invent, inflate, or shift: employers, titles, dates,
   degrees, certifications, metrics, visa/work-authorization status, or skills
   the candidate hasn't claimed in their profile. If a posting wants something
   the profile doesn't support, say so in the fit report — don't paper over it.
   When a tailored bullet is a judgment call (e.g. "led" vs "drove"), stay on
   the conservative side of what the profile states.
2. **Submit gate.** Never click a final Submit / Send application / Review &
   submit button without explicit, per-application approval from the user in
   this session. Filling and staging a form is fine; submitting is theirs to
   approve. A blanket "just apply to everything" still gets a per-job summary
   + confirm, batched is fine ("approve jobs 1, 3, 4").
3. **Credentials stay human.** Never ask for, type, store, or log passwords,
   2FA codes, or session cookies. When a site needs login, pause, tell the
   user which site and why, let them log in in the visible browser window (or
   via their own saved session), then continue.
4. **No anti-bot evasion.** Never attempt to solve or route around CAPTCHAs,
   bot checks, or rate limits. Hand CAPTCHAs to the user, and pace actions
   like a human reading a form. If a site's terms clearly prohibit automated
   applications, tell the user and let them drive that site manually while you
   prep the materials.
5. **PII discipline.** The candidate profile is sensitive. Keep it in the
   local workspace, send it only to the job site being applied to, and never
   include it in commits, logs, or third-party calls.

## Requirements

A browser-control surface, whichever the host provides — in preference order:

- A **browser-automation MCP server** (Playwright MCP, Chrome DevTools MCP,
  browser-use, etc.) — check the available tools before assuming.
- **Playwright driven from a script** (Node or `python3`) when the environment
  has a browser installed — prefer `headless: false` so the user can watch and
  take over for logins/CAPTCHAs.
- The host's **computer-use / screen-control** capability as a fallback.

If none exists, say so and degrade gracefully: run Phases 1–3 (discovery via
web search, fit scoring, tailored materials) and hand the user copy-paste-ready
output plus a checklist instead of driving the form.

## Workspace

All state lives in a local, git-ignored workspace the user chooses on first
run (suggest `~/job-hunt/`, never inside a repo that gets pushed):

```
<workspace>/
  profile.md               # candidate profile — single source of truth (template below)
  resume-base.md           # master resume: the full, untailored fact set
  answers-bank.md          # reusable screening answers (auth, salary, notice, etc.)
  tracker.jsonl            # one JSON object per application (schema below)
  applications/<slug>/     # per-job folder: posting.md, fit.md, resume.md/pdf, cover-letter.md, notes.md
```

`<slug>` = `<company>-<role>` kebab-cased, e.g. `acme-staff-engineer`.
Resolve bundled templates/references relative to this SKILL.md directory.

**Tracker schema** (append-only JSONL; one line per application):

```json
{"slug": "acme-staff-engineer", "company": "Acme", "role": "Staff Engineer",
 "url": "https://...", "source": "linkedin", "fit": 82, "status": "submitted",
 "date_found": "2026-08-25", "date_applied": "2026-08-25",
 "resume_variant": "applications/acme-staff-engineer/resume.pdf",
 "salary_posted": "$180-220k", "notes": "referral from J; follow up 9/1"}
```

`status` ∈ `found → triaged → tailored → staged → submitted → interviewing → offer → rejected → withdrawn`.

## Workflow

### Phase 0 — Profile intake (first run, or when stale)

1. If `profile.md` exists and the user hasn't said it changed, load it and
   move on. Otherwise copy `templates/candidate-profile.md` into the workspace
   and fill it interactively from what the user provides (an existing resume
   file, LinkedIn export, or conversation).
2. Build `resume-base.md` — the master resume containing **every** true bullet,
   even ones that won't all appear in any single tailored variant. Tailoring
   later selects from this set; it never adds to it.
3. Build `answers-bank.md` from the template's screening section: work
   authorization, relocation, remote preference, salary expectations, notice
   period, and the user's stance on the standard "why us / why you" questions.
4. Capture the **search spec**: target titles, seniority, locations/remote,
   salary floor, must-haves, dealbreakers, companies to avoid or target.

### Phase 1 — Discover

Locate candidate postings via the browser (and/or web search when faster):

1. Work the sources the user names; default sweep = LinkedIn Jobs, company
   careers pages for named targets, plus one aggregator (Indeed / Otta /
   Wellfound / relevant niche board). Site-specific mechanics live in
   `references/browser-playbook.md`.
2. For each promising posting capture: company, role, location/remote, salary
   if posted, URL, and the full job-description text into
   `applications/<slug>/posting.md`. Append a `found` row to the tracker.
3. Dedupe against the tracker before adding (same company+role, or same URL).
4. Stop at a reviewable batch (default ~10–15) rather than crawling forever;
   present the list and let the user cut or add before triage.

### Phase 2 — Triage & fit score

For each `found` posting, write `applications/<slug>/fit.md`:

1. Extract from the posting: hard requirements, nice-to-haves, the 5–8
   keywords the role actually screens on, culture/values signals, and any
   red flags (comp below floor, dealbreakers, ghost-posting signals).
2. Score fit 0–100 against `profile.md`: requirements coverage (50), keyword/
   domain overlap (25), seniority/comp alignment (15), candidate's stated
   preferences (10). Note the 2–3 strongest hooks and the honest gaps.
3. Update tracker to `triaged` with the score. Present a ranked table; the
   user picks which to take to tailoring (default: everything ≥70 they
   don't veto).

### Phase 3 — Tailor (the core of this skill)

Per selected job, produce the materials in `applications/<slug>/`. Full
technique and quality bars are in `references/tailoring-guide.md`; the shape:

1. **Resume variant** (`resume.md`, then render to PDF):
   - Select and re-order bullets from `resume-base.md` so the top third of
     the resume answers this posting's top requirements.
   - Mirror the posting's terminology **where truthful** (their "Kubernetes"
     over your "k8s"; their "stakeholders" over your "partners") — this is
     for the human reader, not keyword-stuffing.
   - Rewrite the summary line for this role; keep facts identical.
   - Render to PDF with what the host has (pandoc/typst/LaTeX via Bash, a
     docx/pdf skill, or hand the user the .md if nothing can render). One
     page unless the profile says senior-multi-page.
2. **Cover letter** (`cover-letter.md`, from `templates/cover-letter.md`):
   ≤300 words, specific to this company (name a real product/mission/team
   fact found during discovery), lead with the strongest hook from `fit.md`,
   close with the one gap you can honestly reframe — or skip the letter
   entirely where the form doesn't accept one.
3. **Screening answers** (`answers.md`): draft answers for the questions
   visible in the posting/form, pulling stock answers from `answers-bank.md`
   and tailoring the free-text ones. Flag any question whose true answer
   might disqualify (auth, comp) — the user decides how to answer; never
   shade the truth to pass a filter.
4. Diff-check against the truth lock: every claim traceable to
   `resume-base.md` / `profile.md`. Update tracker to `tailored`.

### Phase 4 — Apply (browser drive)

Per job, with the user available (this phase is interactive by design):

1. Open the application URL. Identify the ATS (Greenhouse, Lever, Workday,
   Ashby, iCIMS, LinkedIn Easy Apply, …) and follow its playbook in
   `references/browser-playbook.md`.
2. If login/CAPTCHA appears → pause per non-negotiables #3/#4.
3. Fill the form top-to-bottom from `profile.md` + `answers.md`: contact
   info, work history (dates/titles exactly as in the profile), education,
   EEO/voluntary sections per the user's standing instruction (default:
   "prefer not to say" unless the user set answers), upload the tailored
   resume PDF and paste/attach the cover letter where accepted.
4. Screenshot or summarize the filled form — every field and answer — and
   update tracker to `staged`.
5. **Submit gate:** present the summary, get explicit approval, then and only
   then click submit. Confirm the success page, capture the confirmation
   number/email note if shown, update tracker to `submitted` with the date.
6. On a multi-job run, pace like a human: complete one application fully
   before starting the next; a few per session, not dozens.

### Phase 5 — Track & follow up

- After each session, show the tracker as a table: pipeline counts by status,
  anything `staged` but unsubmitted, and applications >7 days old in
  `submitted` (suggest a follow-up note, draft it on request).
- Record outcomes as the user reports them (`interviewing`, `rejected`,
  `offer`); a rejection pattern on a keyword or seniority band is a signal to
  revisit the search spec or resume base — say so.

## Degraded modes

| Missing | Do |
|---|---|
| No browser control | Phases 1–3 via web search + tailored materials + a per-job manual checklist with the exact answers to paste |
| No PDF renderer | Deliver `resume.md` + tell the user how to export (Google Docs / word processor); never submit a raw .md to an ATS |
| User absent mid-Phase-4 | Stage the form, tracker → `staged`, stop before the gate; resume next session |
| Site blocks automation | Say so; user drives that site manually while you dictate field-by-field values |

## Bundled files

- `templates/candidate-profile.md` — profile + answers-bank intake template
- `templates/cover-letter.md` — cover-letter skeleton with quality bar
- `references/tailoring-guide.md` — full tailoring technique: bullet selection, keyword mirroring, truth-lock checklist, screening-question patterns
- `references/browser-playbook.md` — per-ATS/per-board mechanics: LinkedIn Easy Apply, Greenhouse, Lever, Workday, Ashby, iCIMS, plus discovery search patterns
