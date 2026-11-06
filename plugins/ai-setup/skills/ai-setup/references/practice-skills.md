# Practice Skills — the stack's best practices, as skills

Every core stack facet ends the setup with a practice skill: adopted
(`discovery.md`) or authored by a practice-author subagent following this file.
A practice skill is what makes "React frontend engineer" produce an agent that
writes current, idiomatic React in *this* repo rather than a plausible average
of every React version it has seen.

**Contents**
- [What a practice skill is for](#what-a-practice-skill-is-for)
- [Granularity and naming](#granularity-and-naming)
- [Research protocol](#research-protocol)
- [What goes in](#what-goes-in)
- [Shape](#shape)
- [Quality gate](#quality-gate)
- [Staleness](#staleness)

## What a practice skill is for

A capable model already knows the stack's basics. What it gets wrong, without
help, falls into five buckets — and a practice skill contains only these:

| Bucket | Example of the failure it prevents |
|---|---|
| **Changed** — the idiom moved between versions | Writing the pattern that was standard two majors ago and is now deprecated, removed, or unnecessary |
| **Decisions** — two valid options, a non-obvious rule for choosing | Reaching for the heavier tool by habit when the lighter one is the documented default |
| **Footguns** — legal code with a non-obvious failure | Code that compiles, passes a shallow test, and breaks under concurrency, hydration, or scale |
| **Verification** — how to prove the change works in this stack | Declaring done after typecheck when the failure only shows at runtime |
| **Local** — this repo's choices among the stack's options | Using the ecosystem default where the team standardized on something else |

Anything outside these buckets is a tutorial. It costs context and changes
nothing.

## Granularity and naming

One skill per **decision domain that triggers together**.

- Split when the triggers differ: writing components, writing tests, and
  auditing accessibility are three moments, so three skills.
- Merge when they always co-occur: a framework and its inseparable router or
  compiler belong together.
- Never one mega-skill for the whole stack, and never one skill per library.
- Three to six authored practice skills per role. If the count goes higher, the
  facets were sliced too thin.

Name by domain, kebab-case, matching the directory: `react-practices`,
`nextjs-practices`, `ts-practices`, `frontend-testing`, `web-a11y`. Check
`inventory.json` so the name does not shadow an installed skill.

Placement: repo scope (committed) when the skill encodes the repo's choices or
the team should share it; user scope when it is generic to the stack and the
engineer wants it everywhere.

## Research protocol

Run by the practice-author subagent. Model knowledge is the starting hypothesis,
never the source.

1. **Pin versions.** Take the facet's major version from `stack.json`. Unknown
   → ask the orchestrator; do not assume latest. Note adjacent pins that change
   the advice (language version, bundler, runtime).
2. **Read primary sources for that major**, in this order:
   1. The official documentation for the pinned version, especially pages titled
      like "thinking in", "rules of", "common mistakes", "best practices",
      "performance", "security".
   2. **Upgrade guides and release notes** for every major from roughly two
      versions back up to the pinned one. This is the richest source: each
      deprecation, removal, and changed default is a "Changed" row.
   3. The maintainers' own lint rule set. Every rule is a practice someone
      already made mechanical — and a lint recommendation for the plan.
   4. Maintainer-authored posts, RFCs, and conference material tied to that
      version.
   5. A vendor-published agent skill or `llms.txt` for the stack, as a
      cross-check.
3. **Exclude** undated posts, listicles, content for another major, and
   anything that cannot be traced to the maintainers or to observed behavior.
4. **Read the repo** (repo scope): lint and compiler configuration, a few
   representative files per layer, and the surveyor's conventions. Where the
   repo deliberately differs from the documented default, the repo wins and the
   skill says so in "Local".
5. **Filter every candidate rule** through one question: *would a strong model
   writing code for this stack get this wrong by default, on this version?* If
   no, cut it.
6. **Record sources** in the skill's `references/sources.md`: URL, the version
   it covers, the date checked, and which rules it supports. A rule with no
   source is cut.
7. **Send enforceable rules to the linter.** Any rule an available lint rule can
   enforce is returned as a lint recommendation, and the skill keeps only a
   one-line pointer.

If live research is not possible, stop and report it. The orchestrator decides
with the engineer whether to defer the skill or ship it labeled unverified.

## What goes in

Each rule is one line of instruction, one line of why, and — only where the
difference is not obvious from the words — a minimal contrast pair.

```
**Derive during render; do not mirror props into state.**
Why: mirrored state goes stale the moment the prop changes and needs an effect to resync.
Avoid:  const [full, setFull] = useState(first + last)  + an effect that updates it
Prefer: const full = first + last
```

Writing rules:

- State the default and its escape hatch: "Do X. Reach for Y only when Z."
- Name the version: "Since v19, …" tells a reader when the rule expires.
- Describe the situation, not just the API: a rule fires on a recognizable
  moment in the work ("when you are about to add an effect to sync two values").
- Prefer a decision table to a paragraph when there are more than two options.
- No rules about formatting or anything the repo's tools enforce.
- No absolute language without a reason. "Never" needs its why on the same line.

## Shape

Use `templates/practice-skill.template.md`. Sections, in order:

| Section | Content | Size |
|---|---|---|
| Frontmatter | `name`, `description` with concrete triggers (file types, tasks: write, review, refactor, debug), `metadata` with pinned versions and research date | — |
| Overview | Scope line: stack, versions, where it applies; what it deliberately omits | 3–5 lines |
| Quick Reference | The decision table an engineer would tape to a monitor | 8–15 rows |
| Changed — do not write the old way | Old idiom → current idiom → since which version | A table |
| Decisions | The when-X-versus-Y rules | Short sections |
| Footguns | Legal code that fails, with the symptom | A list |
| Verify | How to prove a change works in this stack, in this repo | Commands and what to look at |
| Local | The repo's deliberate choices (repo scope only) | A list with exemplar file paths |
| Review checklist | What to check when reviewing a diff in this domain | 8–12 checks |
| Common Mistakes | The three to six highest-frequency failures, with fixes | Short |

Depth goes in the skill's own `references/` — one file per sub-area
(`state.md`, `data-fetching.md`, `performance.md`), linked from the body, one
level deep. `references/sources.md` is always present.

The description decides whether the skill ever loads. Write it in the third
person, front-load the trigger terms, and name both the artifacts
(`.tsx components, hooks`) and the tasks (`writing, reviewing, refactoring`).
State what it is *not* for when a sibling practice skill covers the neighbor
domain, so the two do not compete.

## Quality gate

Run by the author before returning, and re-checked by the orchestrator.

| Check | Pass condition |
|---|---|
| Structure | Frontmatter parses; `name` equals the directory; description within 1024 characters; body within 500 lines, aiming for about 200 |
| Tutorial test | Delete every line a strong model would produce unprompted. If the skill is still mostly intact, it passes |
| Delta share | Most rules are version-specific, decision rules, or local. A skill of generic advice fails |
| Sourcing | Every rule traces to an entry in `references/sources.md` |
| Version scope | The versions are stated in the overview and in `metadata` |
| Trigger probes | Three prompts: two that should load the skill, one near-miss that should not. The description must discriminate them |
| Conflicts | No rule contradicts the repo instructions, a sibling practice skill, or the linter configuration |
| Enforceables | Every lint-enforceable rule was returned as a lint recommendation |

A skill that fails the tutorial test is not padded until it passes. If a facet
has little delta — the model already handles it well on this version — the
correct output is "no skill needed for this facet", and the slot is waived with
that reason.

## Staleness

Practice skills expire when the stack moves.

- `metadata` records the pinned versions and the research date.
- On a re-run, the orchestrator compares `stack.json` majors with each skill's
  pinned versions. A changed major means re-research and replace; a minor bump
  means re-read the release notes and patch the "Changed" table.
- The playbook tells the engineer to re-run after a major upgrade.
- An adopted third-party skill is re-checked for an upstream update on re-run.
