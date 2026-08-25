# Browser Playbook

Mechanics for driving job boards and applicant-tracking systems (ATSes) with
whatever browser-control surface the host provides. Selectors drift and sites
redesign — treat the notes below as orientation, read the live page every
time, and prefer role/label-based targeting ("the button labeled *Submit
application*") over brittle CSS selectors.

## General rules of the road

- **Visible browser** whenever possible (`headless: false`): the user can
  watch, take over logins/CAPTCHAs, and trust what's happening.
- **Human pacing.** One action, then read the result. No rapid-fire
  submissions, no parallel tabs hammering one site. If a site rate-limits or
  challenges, back off and tell the user.
- **Logins are the user's.** Navigate to the login page, stop, ask the user to
  sign in, wait for their go-ahead. Same for any CAPTCHA / "verify you're
  human" step — never attempt it.
- **Read before writing.** On every form page, first enumerate the fields
  (labels, required markers, current values), map them to `profile.md` /
  `answers.md`, and only then fill. Unmapped required fields → ask the user.
- **Verify after writing.** Re-read each field after filling; file uploads in
  particular fail silently. Confirm the resume filename appears on the page.
- **Multi-step wizards:** screenshot/summarize each step before advancing;
  many ATSes discard state on back-navigation.
- **Never** click a final submit without the user's per-application approval
  (the skill's submit gate), and stop at any "review" page — that's the gate's
  natural home.
- If a site presents terms that prohibit automated access/applications, stop
  driving it and switch to dictation mode (user drives, you supply values).

## Discovery patterns

### LinkedIn Jobs

- Search URL shape: `linkedin.com/jobs/search/?keywords=...&location=...` with
  filters for date-posted, remote (`f_WT=2`), experience level. Logged-in
  search gives better results; expect a login pause.
- Collect from the results list: title, company, location, posted-age, and
  whether it's **Easy Apply** (in-LinkedIn form) vs external redirect.
- Open each posting to capture the full description — the list view truncates.
- Ghost-posting signals worth flagging at triage: reposted-many-times,
  >30 days old, "actively reviewing" absent, recruiter-anonymous postings.

### Indeed / general aggregators

- Aggregators often proxy an underlying ATS posting. Prefer following through
  to the **company's own careers page** and applying there — direct
  applications are typically parsed better and duplicate-detected less.
- Capture the canonical company-site URL in the tracker, not the aggregator's.

### Company careers pages

- Usually hosted by one of the ATSes below (`boards.greenhouse.io/<company>`,
  `jobs.lever.co/<company>`, `jobs.ashbyhq.com/<company>`, `<company>.wd5.
  myworkdayjobs.com`, …). Recognizing the host tells you which application
  flow you'll get before you click Apply.

## ATS playbooks

### LinkedIn Easy Apply

- Modal wizard, 1–7 steps, progress bar on top. Steps: contact info (pre-filled
  from the LinkedIn profile — verify against `profile.md`), resume upload
  (replace any default with the tailored PDF), screening questions, optional
  demographic questions, review.
- The **Review** step is the submit gate. Summarize everything shown, get
  approval, then "Submit application".
- Dropdown years-of-experience questions are common — values come from
  `answers.md`, computed conservatively.

### Greenhouse (`boards.greenhouse.io`)

- Single long form, no login. Standard fields + resume/cover-letter uploads
  (accepts paste-as-text on some boards), then custom questions.
- Resume upload sometimes triggers auto-parse that overwrites typed fields —
  upload **first**, then fix the parsed fields.
- EEO section ("voluntary self-identification") at the bottom — fill per the
  user's standing instruction; "Decline to self-identify" is always available.
- One submit button at the end; no review page, so the staged-form summary IS
  the gate — approve before clicking.

### Lever (`jobs.lever.co`)

- Similar single-page form. Distinctive: a required full-name field, resume
  upload with auto-parse, and free-text "Additional information" (default:
  leave empty or one hook line).
- Submit button labeled "Submit application"; same no-review-page caution as
  Greenhouse.

### Workday (`myworkdayjobs.com`)

- The heavy one: **requires account creation per company** (user does this —
  it's a credential), multi-step wizard (My Information → My Experience →
  Application Questions → Voluntary Disclosures → Self Identify → Review).
- Resume auto-parse on "My Experience" is notoriously bad — expect to repair
  titles/dates/descriptions field-by-field from `profile.md`.
- Work-history entries are structured (add-per-job) — enter dates exactly as
  in the profile; Workday validates overlaps.
- There IS a Review step — the natural submit gate.
- Sessions time out (~20 min idle); don't stage-and-abandon mid-wizard.

### Ashby (`jobs.ashbyhq.com`)

- Modern single-page form, occasionally multi-step. Fast, reliable uploads;
  custom questions often include short free-text prompts — draft from
  `answers.md`, keep answers tight.

### iCIMS (various `*.icims.com`)

- Older wizard, frame-heavy pages (automation surfaces may need to enter an
  iframe to reach the form), account creation frequently required (user's
  credential), aggressive session timeouts.
- If the surface can't reach into the frames, switch to dictation mode rather
  than fighting it.

### Unknown / bespoke ATS

- Enumerate fields, map, fill, verify — the general rules cover it. If the
  form fights automation (canvas widgets, exotic file pickers), fall back to
  dictation mode: the user drives, you read out each field's value from the
  prepared materials.

## Failure handling

| Symptom | Response |
|---|---|
| CAPTCHA / bot check | Stop; hand to user; continue after they clear it |
| Login wall | Stop; user signs in; continue |
| Upload rejected (type/size) | Re-render resume (PDF ≤2 MB usually safe); retry once; else ask user |
| Form error on submit-adjacent step | Read the inline errors, fix mapped fields, re-verify; never guess at required fields |
| Session expired mid-wizard | Tell the user what was lost; restart the wizard fresh rather than trusting stale state |
| Site blocks automation outright | Dictation mode + note it in the tracker so future runs skip straight there |
