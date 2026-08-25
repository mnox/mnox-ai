# Tailoring Guide

How to adapt a resume, cover letter, and screening answers to one specific
posting without ever crossing the truth lock. Tailoring is **selection,
ordering, and phrasing** — never new facts.

## The one rule, restated

Every claim in a tailored artifact must be traceable to `resume-base.md` or
`profile.md`. If you can't point at the source line, the claim doesn't ship.
Gaps get handled honestly (reframe, address in the letter, or accept the
weaker fit) — never by invention, inflation, or ambiguity engineered to
mislead ("familiar with" for something the profile doesn't mention at all).

## Resume tailoring

### 1. Build the requirement map

From `fit.md`, list the posting's requirements in the order the employer
weighted them (usually: first-listed and repeated items matter most). For each,
find the strongest supporting bullet(s) in `resume-base.md`. The map drives
everything below.

### 2. Select and order bullets

- The **top third** of page one must answer the top 3 requirements — a
  screener spends ~10 seconds deciding whether to keep reading.
- Per role in work history, keep the 3–5 bullets most relevant to *this*
  posting; drop strong-but-irrelevant bullets without regret (they live on in
  `resume-base.md`).
- Prefer bullets with outcomes and numbers over responsibility statements.
  If the base bullet has a metric, keep the metric exact — never round up.
- Old or irrelevant roles compress to one line (title, company, dates).

### 3. Mirror terminology — honestly

Use the employer's words for things the candidate genuinely did:

- Synonym swaps are fine: their "Kubernetes" for your "k8s", their
  "cross-functional stakeholders" for your "partner teams", their "CI/CD"
  for your "build pipelines".
- Scope swaps are not: "led" ≠ "participated in", "architected" ≠
  "implemented", "managed" (people) ≠ "coordinated" (tasks). When unsure
  which side of the line a rephrase falls on, ask the user — it's their
  interview to survive.
- Never add a skills-section entry that isn't in the profile, and never
  hide keyword soup in white text or metadata. ATS keyword matching is
  served by using real terms in real bullets.

### 4. Rewrite the summary/headline

One or two lines, rewritten per job: candidate's actual seniority + the 2–3
matched strengths from the requirement map + the domain, phrased toward this
role's language. No objectives, no adjectives-without-evidence.

### 5. Render

- One page default; two pages only if the profile says the candidate's field
  expects it (senior/staff+, academia, etc.).
- Simple single-column layout — ATS parsers mangle tables, text boxes, and
  multi-column layouts. Standard section headers (Experience, Education,
  Skills). File name: `Firstname-Lastname-Resume.pdf` (companies see it).

### Truth-lock checklist (run before anything ships)

- [ ] Every employer, title, and date range identical to `resume-base.md`
- [ ] Every metric identical (not rounded up, not re-based)
- [ ] No skill appears that the profile doesn't claim
- [ ] Every verb's scope matches what actually happened
- [ ] Education/certs exactly as held (no "expected" upgrades, no dropped qualifiers)
- [ ] Nothing hidden from the human reader that the ATS sees

## Cover letter tailoring

Skeleton in `templates/cover-letter.md`. Quality bar:

- **≤300 words, 3 paragraphs.** Recruiters skim; density wins.
- **Paragraph 1 — the hook:** name the role, then the single strongest
  fit-point from `fit.md`, with its evidence. Not "I am excited to apply".
- **Paragraph 2 — proof + company specificity:** one or two concrete
  accomplishments mapped to their stated needs, plus one *real* company fact
  from discovery (product, mission, recent launch, team blog post) that shows
  the letter isn't a mail-merge. A wrong or generic company fact is worse
  than none.
- **Paragraph 3 — the gap and the close:** if `fit.md` shows a visible gap
  they'll notice, one honest sentence reframing it (adjacent experience,
  fast ramp evidence) — then a plain close. Skip the gap sentence if there
  isn't one; never manufacture humility.
- Reuse of a base letter is fine; reuse of paragraph 2 across companies is
  how letters read generic. That paragraph is always fresh.

## Screening questions

Standard answers live in `answers-bank.md`; per-job answers in the job's
`answers.md`. Patterns:

- **Binary filters (work auth, relocation, license):** answer with the truth
  from the profile, verbatim, every time. If the true answer likely
  disqualifies, tell the user *before* staging — they may skip the job, but
  the answer never changes.
- **Salary expectations:** use the user's standing instruction from
  `answers-bank.md` (a range, "negotiable", or a number). If the posting's
  range is below the user's floor, flag it at triage, not at the form.
- **"Why this company?"** — compress cover-letter paragraph 2 to 2–3
  sentences with the company-specific fact.
- **"Describe a time…"** behavioral prompts — pick the matching story from
  the profile's stories section (STAR-shaped: situation, task, action,
  result), tailored to the competency asked.
- **Years-of-experience dropdowns:** compute from the profile's dates; round
  down, never up.
- **Free-text "anything else?"** — default empty or one line pointing at the
  strongest hook; it's not a second cover letter.

## Anti-patterns (all observed in the wild, all rejected)

- Keyword-stuffing a skills section to beat an ATS — screeners see it, and
  interviews expose it.
- Tailoring so aggressively the resume contradicts the candidate's LinkedIn —
  recruiters diff them.
- Same "personalized" sentence with the company name swapped — the
  mail-merge tell.
- Answering screening filters "optimistically" — an offer rescinded on a
  background check is the worst outcome the skill can cause. Truth, always.
