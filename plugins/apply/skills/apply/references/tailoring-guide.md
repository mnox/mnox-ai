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

Two audiences read every resume: literal engines (exact-term matchers,
recruiter keyword search) and semantic readers (AI graders, LLM screeners,
humans). The method below serves both at once; engine-specific intel is in
`references/ats-engines.md`.

### 1. Build the requirement map and keyword map

From `fit.md`, list the posting's requirements in the order the employer
weighted them (usually: first-listed and repeated items matter most). For each,
find the strongest supporting bullet(s) in `resume-base.md`. The map drives
everything below.

Then extract a **tiered keyword map** from the posting into
`applications/<slug>/keywords.json` (schema in `scripts/keyword_coverage.py`):

- **hard_skills** (weight 50): tools, technologies, methodologies, named
  systems. The tier engines and recruiters weigh most.
- **title_seniority** (20): the exact job title and level words.
- **certifications** (15): named certs/licenses/clearances.
- **soft_skills** (10): only ones the posting states explicitly.
- **domain** (5): industry/domain vocabulary the posting leans on.

Rules of extraction: take the posting's **exact surface forms**; a term that
appears in the title or repeats in the body is tier-1 within its tier; list
known variants (`"Kubernetes"` with variant `"k8s"`, `"CI/CD"` with
`"continuous integration"`) so the coverage check credits any true form.
Mark which terms the profile can truthfully support — the rest are **fit
gaps**, recorded in `fit.md`, never keyword targets.

### 2. Place keywords where engines look

For every truthfully-supported tier-1 term:

- **Both placements:** in the skills section AND inside at least one
  experience bullet as evidence — listed-but-never-used reads as filler to
  semantic engines; used-but-not-listed misses recruiter skill filters.
- **Top third:** the posting's top requirements appear in the summary or
  first role's bullets — screeners and match engines both weight the top of
  page one.
- **Recency:** relevant terms live in the most recent roles where truthful;
  several engines discount skills last used years ago.
- **Frequency, naturally:** core skills appear 2–3 times across the resume
  in different true contexts (iCIMS-style engines count; LLM screeners
  penalize unnatural repetition — context keeps it legitimate).
- **Dual forms on first use:** acronym + spelled-out — "Search Engine
  Optimization (SEO)", "Amazon Web Services (AWS)" — so both literal search
  forms hit.
- **Exact title alignment:** use the posting's job title verbatim in the
  summary/headline when it truthfully names the candidate's level; adjust
  phrasing ("Senior Engineer specializing in…"), never the level itself.

### 3. Select and order bullets

- The **top third** of page one must answer the top 3 requirements — a
  screener spends ~10 seconds deciding whether to keep reading.
- Per role in work history, keep the 3–5 bullets most relevant to *this*
  posting; drop strong-but-irrelevant bullets without regret (they live on in
  `resume-base.md`).
- Prefer bullets with outcomes and numbers over responsibility statements.
  If the base bullet has a metric, keep the metric exact — never round up.
- Shape each key bullet as **quotable evidence**: verb + task + tool/skill +
  scale + result, one claim per bullet. Semantic engines (Ashby, HiredScore,
  LLM screeners) extract exactly this shape as proof of a requirement, and
  it's also what a human skim retains. "Cut p99 latency 40% by moving the
  ingest pipeline to Kafka across 200+ services" beats "responsible for
  performance improvements".
- Old or irrelevant roles compress to one line (title, company, dates).

### 4. Mirror terminology — honestly

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

### 5. Rewrite the summary/headline

One or two lines, rewritten per job: candidate's actual seniority + the 2–3
matched strengths from the requirement map + the domain, phrased toward this
role's language — including the posting's exact title where truthful (§2). No
objectives, no adjectives-without-evidence.

### 6. Score the draft — the coverage loop

Run the deterministic check (script beside this skill):

```
python3 scripts/keyword_coverage.py \
  --keywords applications/<slug>/keywords.json \
  --resume   applications/<slug>/resume.md
```

- **Target: ≥80 weighted coverage** (industry tooling converges on 75–80%),
  with the job title present and tier-1 hard skills each appearing more than
  once, at least one of them in the top third.
- For each MISSING term: if `resume-base.md` truthfully supports it, work it
  into a real bullet or the skills section and re-run. If it doesn't, it
  stays missing — record it as a fit gap (candidate for the cover letter's
  honest-gap line), and never add it anyway. **The score ceiling is set by
  the truth**; a truthful 65 ships before a padded 85.
- Include the final score and remaining gaps in the pre-submit summary so
  the user sees what the application's keyword posture actually is.

### 7. Render — parse fidelity is half the score

If parsing drops a section, its keywords were never evaluated (~40% of
resumes hit at least one parsing error). Non-negotiable format rules:

- **Single column**, no tables, no text boxes, no images/icons/skill bars.
- **Contact info in the document body** — parsers skip header/footer layers.
- **Standard section headers** (Summary, Experience, Education, Skills,
  Certifications) — custom headers break section detection.
- **Dates as `Mon YYYY – Mon YYYY`** ("Jan 2020 – Present"), consistent
  everywhere.
- 10–12pt standard font (Arial/Calibri/Georgia/Times), 0.75–1in margins.
- **Text-based PDF or .docx** — never an image/scanned PDF.
- One page default; two pages only if the profile says the candidate's field
  expects it (senior/staff+, academia, etc.).
- File name: `Firstname-Lastname-Resume.pdf` (companies see it).

**Round-trip check before anything ships:** extract the rendered file's text
(`pdftotext resume.pdf -` or equivalent) and confirm sections survive in
order, no scrambling, and the coverage script scores the same on the
extracted text as on the markdown. If extraction looks scrambled to you, it
looks scrambled to the ATS.

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
