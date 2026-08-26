# ATS & Resume-Evaluator Engine Intelligence

How the screening engines behind big-company hiring actually evaluate resumes,
and what that means for tailoring. Sourced from vendor documentation and
current (2025–2026) industry analysis; engines evolve, so treat specifics as
strong priors and update when observed behavior differs.

**The truth lock applies unchanged.** Everything here optimizes how truthful
content is *selected, phrased, placed, and formatted* so engines can see it.
Nothing here justifies inventing a skill or gaming with hidden text — modern
engines flag stuffing, recruiters diff against LinkedIn, and interviews expose
the rest.

## The real pipeline (myths corrected)

Every major system runs some version of: **parse → match → rank → human
review**, with two automation layers candidates actually face:

1. **Knockout/minimum-qualification questions** — the only common *hard*
   auto-reject. Wrong answer on work auth, required license, or a
   minimum-quals question ends the application regardless of resume quality.
   That's why the skill surfaces disqualifying answers at triage: the answer
   never changes, but the user can skip the job.
2. **Ranking/grading** — resumes are scored *relative to the posting* and the
   pool; recruiters review the top slice. There is usually no secret pass/fail
   keyword threshold, but a resume that parses badly or misses the posting's
   core terms sits in the slice nobody opens.

Corollaries that drive tailoring:

- **Parse fidelity comes first.** If parsing drops or scrambles a section,
  its keywords were never evaluated. Industry testing suggests ~40% of
  resumes contain at least one element that causes a parsing error.
- **Recruiter keyword search is a second keyword engine.** Independent of any
  AI score, recruiters run literal term searches over the candidate database
  (Greenhouse's candidate search, LinkedIn Recruiter, Taleo/iCIMS filters).
  Exact terms on the resume decide whether you surface at all.
- **A newer AI/LLM layer** increasingly summarizes and ranks what survives
  parsing (HiredScore grades, Ashby match evidence, LLM screeners). It rewards
  clear, specific, evidence-backed writing and semantic relevance — and it
  penalizes keyword soup.

## Engine-by-engine

### Workday + HiredScore (very common at F500)

- HiredScore grades every applicant **A–D against the specific requisition**,
  with role-specific weighting; grades surface directly in the recruiter's
  Workday queue, and A/B candidates get opened first. It also does **skills
  inference** (e.g. inferring C++ from embedded-systems work) and **talent
  rediscovery** (re-surfacing past applicants for new reqs — your profile
  outlives this application).
- Workday's application form re-enters work history as **structured fields**;
  its auto-parse is weak, and graders read the structured data, not your PDF.
- Tailor for it: nail the posting's stated requirements in explicit, recent
  bullets (role-specific weighting means posting-alignment beats generic
  impressiveness); repair every parsed field during the wizard — titles,
  dates, and descriptions in the structured form ARE the input to the grade;
  keep skills named plainly so inference has hooks; expect the profile to be
  re-matched against future reqs, so nothing resume-local should contradict
  the reusable Workday profile.

### Oracle Taleo (older F500, government-adjacent)

- **Req Rank** scores each applicant against the job description — the
  closest thing to the mythical "keyword score" that actually exists.
  Heavy exact-term matching plus **knockout questions that hard-auto-reject**.
  Strictest parser of the majors: single column, standard headers, no
  graphics, or fields silently drop.
- Tailor for it: maximize exact-form keyword coverage (both acronym and
  spelled-out forms), ultra-conservative formatting, and treat every
  screening question as a knockout until proven otherwise.

### iCIMS (large enterprises)

- Keyword-frequency oriented matching plus recruiter-side keyword filters;
  older parser with known quirks; frequently requires an account.
- Tailor for it: each core skill appears more than once in real context
  (frequency counts here); conservative formatting; exact terms from the
  posting.

### SAP SuccessFactors (global enterprises)

- Keyword matching with a parser known for mangling complex layouts.
- Tailor for it: same as Taleo — parse-safe layout, exact terms.

### Greenhouse (tech mid-size/scale-ups)

- Historically **no native AI ranking score** — the engine is the recruiter:
  structured scorecards, attribute filters (skills, years, location), and a
  literal **keyword search across all candidates**. Resume auto-parse fills
  the candidate profile and can overwrite typed fields.
- Tailor for it: optimize for a fast human skim (top third carries the match)
  plus searchable exact terms; verify the parsed profile after upload and fix
  what the auto-parse broke.

### Lever (tech)

- Relationship/pipeline-oriented; no keyword scoring engine. Referrals,
  prior applications, and cover-letter quality visibly flag a profile.
- Tailor for it: the human materials do the work — a specific cover letter
  has outsized value here; keyword mechanics matter mainly for recruiter
  search.

### Ashby (startups/scale-ups)

- AI match that looks for **evidence sentences it can quote to the recruiter
  with reasoning** — semantic, not frequency-based.
- Tailor for it: write quotable evidence bullets (verb + task + tool + scale
  + result, one claim per bullet). A bullet that reads as self-contained
  proof of a posting requirement is exactly what it extracts.

### LinkedIn (Jobs / Easy Apply / Recruiter)

- Ranking blends the **profile and the uploaded resume**: skills match pulled
  from both, **exact keyword matching weighted heavily**, endorsements boost
  skill-search rank, and the top 3 pinned skills should be the ones recruiters
  actually search for the target role. "Top applicant" style signals come
  from keyword-match scores.
- Tailor for it: the LinkedIn profile is part of the application — headline
  and skills section aligned to the target role's search terms; resume and
  profile must not contradict (recruiters diff them); Easy Apply years-of-
  experience dropdowns are knockout-adjacent, answer from the profile.

### Eightfold / Phenom / deep-learning talent intelligence (large enterprises)

- Deep-learning match trained on career trajectories: **infers adjacent and
  unstated skills**, scores fit from progression patterns and potential, not
  keyword counts. Effectively cannot be keyword-gamed.
- Tailor for it: give the model clean structure to infer from — accurate
  titles, clear progression, explicitly named technologies and domains,
  scale indicators. Honest, well-structured content IS the optimization.

### LLM screeners (the growing layer everywhere)

- GPT-class models summarizing/ranking candidates semantically: synonyms
  match ("reduced downtime" ≈ "improved reliability"), context matters,
  keyword stuffing reads as spam and hurts. They reward bullets that name
  the tool, the task, the scale, and the result in plain language.
- Tailor for it: clarity and evidence density. The same writing that wins
  Ashby and a human skim wins here — this is why the skill's bullet formula
  is the backbone, with exact-term coverage layered on top for the literal
  engines.

## What this means, condensed (the tailoring engine encodes these)

1. **Parse-safe format always** — single column, no tables/text boxes/
   headers/footers, contact info in the body, standard section headers,
   `Mon YYYY – Mon YYYY` dates, 10–12pt standard fonts, text-based PDF or
   .docx. Verify with a text-extraction round trip before submitting.
2. **Exact terms for the literal engines** (Taleo/iCIMS/recruiter search):
   mirror the posting's exact phrasing for true skills; include both acronym
   and spelled-out forms on first use — "Search Engine Optimization (SEO)".
3. **Evidence bullets for the semantic engines** (HiredScore/Ashby/LLMs):
   verb + task + tool + scale + result; one claim per bullet; skills proven
   in context, not just listed.
4. **Both placements**: every tier-1 skill appears in the skills section AND
   inside at least one experience bullet; the top third of page one carries
   the posting's top requirements; recent roles carry the relevant terms
   (recency weighting is common).
5. **Title alignment**: use the posting's exact job title in the summary/
   headline when it truthfully describes the candidate's level ("Senior
   Software Engineer" for a senior software engineer) — never a title
   inflation.
6. **Coverage target**: ~80% weighted coverage of the posting's extracted
   keywords (industry tooling converges on 75–80%) — reached only with
   truthful content; below that, the remainder is a fit gap to disclose,
   not a wording problem to paper over.
7. **Structured-form ATSes grade the form, not the file** (Workday, some
   iCIMS): repairing parsed fields during Phase 4 is scoring work, not
   cleanup.
8. **Knockouts are answered truthfully, flagged early** — at triage, not at
   the form.
