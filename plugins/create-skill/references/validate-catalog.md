# Validate Catalog — what gets checked, and by whom

Two tiers of checking, deliberately separated so each runs at the right cost:

1. **Deterministic structural lint** — `scripts/validate_skill.py`. Fast, free,
   always-run. Mechanical facts only (does it parse, are sections present). No
   judgment.
2. **Design-quality judgment** — the **judge** stage (`judge-rubric.md`) + a call to
   **`util-review`**. Everything the script *can't* decide mechanically.

The split exists because the original `skill-create` validator conflated them and
silently skipped tier 2. This catalog makes tier 2 explicit so it never gets dropped.

**Contents**
- [Tier 1: deterministic checks](#tier-1-deterministic-checks-validate_skillpy)
- [Tier 2: the gap backlog](#tier-2-the-gap-backlog-judgment-required)
- [Routing](#routing)

## Tier 1: deterministic checks (`validate_skill.py`)

Run on every skill. Errors fail the gate (exit 1); warnings inform.

| ID | Severity | Checks |
|---|---|---|
| `skill_md_exists` | error | SKILL.md present in the skill dir |
| `frontmatter_present` | error | YAML frontmatter block exists |
| `frontmatter_parses` | error | Frontmatter is parseable |
| `name_present` | error | `name` field present |
| `name_kebab_case` | error | lowercase `a-z0-9` + hyphens, no leading/trailing/consecutive hyphens |
| `name_length` | error | ≤ 64 chars |
| `name_no_forbidden_token` | error | no `claude` / `anthropic` |
| `description_present` | error | `description` field present |
| `description_length` | error | ≤ 1024 chars |
| `section_overview` | error | `## Overview` present |
| `section_quick_reference` | error | `## Quick Reference` present |
| `section_main_content` | error | ≥1 H2 beyond the 4 reserved headers |
| `section_common_mistakes` | error | `## Common Mistakes` present |
| `forbidden_files` | error | no README.md / CHANGELOG.md inside the skill dir |
| `path_exists` | error | (CLI) the target path resolves |
| `line_budget` | warning | SKILL.md ≤ 500 lines |
| `forward_slash_paths` | warning | no backslash paths in the body |

These map to the open-standard hard rules (name↔dir match, description bounds) and
the house section set (Overview / Quick Reference / Main Content / Common Mistakes).

## Tier 2: the gap backlog (judgment required)

These are the checks `skill-create` historically **missed** — none are decidable by a
regex. They are the design-quality backlog the judge stage owns. (This list is the
spine; keep it complete.)

1. **Script quality** — the scripts actually run, are correct, PEP 723 deps resolve.
2. **Quick Reference usefulness** — the table *helps*, not just *exists*.
3. **Body ↔ description consistency** — the body does what the frontmatter promises.
4. **Example quality** — examples are realistic and correct.
5. **Reference-file relevance** — `references/*.md` actually grounds the body (no orphans).
6. **Tool-usage appropriateness** — the right tools for the job.
7. **`allowed-tools` correctness** — declared tools match what the body invokes.
8. **Common Mistakes realism** — the ❌ items are real failure modes, not filler.
9. **Word-count / section-depth balance** — no bloated or skeletal sections.
10. **Performance** — no needless re-reads, no token waste.
11. **Edge-case coverage** — the body names the real edge cases.
12. **Experience-level accessibility** — usable without unstated context.
13. **Hook validity** — any `hooks:` frontmatter is sound *(Claude-only; flag if present in a portable skill)*.
14. **Portability** — see `authoring-contract.md` §2; no Claude-only surface smuggled into a "portable" skill, no `npx`/`brew` assumptions, forward slashes, relative paths.
15. **Trigger specificity** — the description fires at the right moment and *only* then (guards against the over-triggering "Invisible Skill" and context-polluting failure modes).
16. **Not-a-skeleton** — no empty tables / TODO stubs shipped as "done."

## Routing

- Items **1–12, 15–16** → the **judge** stage, scored via `judge-rubric.md`.
- Items that touch hooks/configs/CLAUDE.md/side-effects/security (**13** and anything
  beyond the skill body itself) → **`util-review`**. Don't re-implement its catalog
  here; invoke it.
- **14 (portability)** → checked against `authoring-contract.md`; the deterministic
  slice (backslashes, forbidden files) is already in Tier 1.
