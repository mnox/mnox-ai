# Module Template

Every module in a generated curriculum follows the same five-part spine.
This file is the authoritative description of each part, with examples and
anti-examples. Load this file before writing any module.

## File naming

`modules/NN-kebab-slug.md` where `NN` is a zero-padded two-digit index.
First module is always `00-orientation`. Final module is conventionally
named `-synthesis`, `-the-flywheel`, `-capstone`, or similar — a module
whose job is to integrate everything prior.

## Frontmatter

Modules do not carry YAML frontmatter. The heading order (`# Module NN — Title`)
is the file's header.

## Section order (required)

```markdown
# Module NN — Title

## ELI5

## Core Concepts

## Deep Dive

## Supporting Material

## Understanding Check
```

Every module has all five sections. Optional sections (e.g., a bridge
block) may appear above `## ELI5` when inserted by the prepare-next-module
workflow; they are delimited by `<!-- bridge:auto -->` markers.

## Section specs

### `## ELI5`

- 3–6 sentences. Plain language. No jargon.
- Leads with an analogy or physical intuition. Ends by naming the concept
  in one line.
- Rule of thumb: if someone who has never studied the field cannot follow
  it, rewrite it.

### `## Core Concepts`

- Dense but readable. 400–800 words.
- Introduce the formal vocabulary here — the names the rest of the field
  uses. Bold the term on first use.
- Use subheadings (`###`) liberally. Each subheading is one concept or
  one mental model.
- Include the one or two key formulas, typeset in a fenced code block when
  ASCII-displayable.
- Every Core Concepts section ends with an explicit tie to the learner's
  long-term goal. This is load-bearing scaffolding, not decoration.

### `## Deep Dive`

- The longest section, typically 500–1500 words.
- This is where non-obvious tradeoffs, gotchas, worked examples, and
  anti-patterns live.
- Include at least one **worked example** — either a code snippet, a
  numerical walkthrough, or a concrete scenario.
- Include at least one **anti-pattern** — something the learner might
  try that seems right but is wrong, with the reason.
- If there's a project, system, performance, or craft context the
  learner cares about (from the stated long-term goal), include a
  subsection tying this concept into that context. Usually the most
  valuable part of the module.

### `## Supporting Material`

- 4–8 curated links. No more.
- Each entry is `- [Title](url) — one-line editorial note.`
- Mix source types: a textbook or canonical reference, a paper or
  long-form essay, a video or demo, a blog post from a practitioner, a
  primary doc / spec / manual.
- Do not pad. A 3-item list from experts beats a 15-item dump.
- Do not fabricate URLs. If a link cannot be verified, describe the
  resource by name and let the learner find it ("the Feynman Lectures,
  Vol. I, Chapter 9" or "the official PostgreSQL documentation on MVCC").
- For fast-moving fields, prefer sources dated within the last 2–3 years
  or mark older sources as "foundational, dated."

### `## Understanding Check`

- 5–8 questions. Numbered.
- Mix three types (aim for all three in every module):
  - **Recall / definition**: "In your own words, define X."
  - **Application**: "Given scenario Y, what would you do?"
  - **Synthesis or trap**: cross-module integration, or a deliberately
    plausible-but-wrong premise the learner must diagnose.
- Mark at least one question with `**Trap question.**`, `**Application.**`,
  or `**Synthesis.**` inline so the learner knows the type.
- End with: "Paste your answers when ready." or equivalent low-friction
  handoff.

## Length

Aim for 200–500 lines per module. Shorter for orientation-style modules.
Longer is permitted for deep-dive modules (especially emphasized areas);
if a module exceeds ~600 lines, consider splitting it.

## Code and diagrams

- Fenced code blocks with language hints (` ```python`, ` ```text`).
- ASCII diagrams are fine and often the right call. Do not embed binary
  images — they don't render in the markdown viewing path the user will use.
- For math, use fenced code blocks with plain notation
  (e.g. `f(x) = a·x + b` or `H = -Σ p_i · log(p_i)`). Do not use LaTeX
  — it will not render.

## Goal tie-in — examples across domains

The goal determines the tie. Each example below is a different domain,
to show the same pattern works regardless of subject matter.

- Goal: "play jazz standards by ear at a jam session." Every module's
  Deep Dive ends with "How this shows up on the bandstand" — concrete
  fingerings, tune references, listening exercises.
- Goal: "ship a side project that does X." The tie is to architecture
  choices in that project: "In your project, this is where the
  <storage | sync | auth | UI> layer lives, and here's why this concept
  governs that boundary."
- Goal: "pass the L4 interview at <company>." The tie is to interview
  scenarios: "Interviewers usually probe this as <X>. The stronger
  answer hits <Y> and <Z>."
- Goal: "write a publishable novel in 12 months." The tie is to craft
  decisions in the manuscript: "When this technique appears in your
  current chapter, the choice is between <effect A> and <effect B>."
- Goal: "run a sub-3-hour marathon." The tie is to a training-week
  decision: "This is the variable you adjust on <tempo | long | recovery>
  days, and here's the failure mode if you over-correct."

Pattern: every Deep Dive closes by translating the concept into an
action the learner takes inside their goal context. Never optional.

## Anti-patterns to avoid

1. **The textbook dump**: writing a generic chapter without the goal
   tie-in. Makes the curriculum feel like a library instead of a path.
2. **The link dump**: 15 URLs with no editorial note. The learner cannot
   prioritize; the module feels lazy.
3. **The rhetorical Understanding Check**: 5 questions, all recall.
   Misses the application test which is what matters for real competence.
4. **The Skipped ELI5**: jumping straight to Core Concepts because "the
   topic is too advanced for ELI5." Every concept has an ELI5. Writing
   it forces the author to know what they actually mean.
5. **The Copy-Paste Deep Dive**: pulling paragraphs verbatim from a
   famous blog. Adds no value beyond the Supporting Material link.
6. **Missing zero-pad**: `modules/1-foo.md` instead of `modules/01-foo.md`.
   Breaks sort order at the tenth module.
