# Template — practice skill

Fill-in notes — do not copy this section into the output:

- Write the block below to `<destination>/SKILL.md`. The frontmatter `name`
  must equal the directory name.
- Follow `references/practice-skills.md`: only the five buckets (changed,
  decisions, footguns, verification, local), every rule sourced, about 200
  lines.
- The description is the trigger. Third person, trigger terms first, both the
  artifacts and the tasks, and a "not for" clause naming the sibling skill that
  owns the neighboring domain. Keep it within 1024 characters.
- Delete "Local" for a user-scope skill. Delete any section with nothing that
  passes the tutorial test.
- Always write `references/sources.md` beside it.

```markdown
---
name: <skill-name>
description: <Stack> <domain> practices for <facet> <major> — <the decisions it covers>. Use when writing, reviewing, refactoring, or debugging <artifact types and file patterns>, or when asked about <trigger phrases>. Not for <neighbor domain> (use <sibling-skill>).
metadata:
  stack-versions: "<facet>@<major>, <facet>@<major>"
  researched: "<YYYY-MM-DD>"
---

# <Stack> <Domain> Practices

## Overview

Applies to <facet> <major> (with <adjacent pins>) in <where>. Covers only what
changed recently, the decisions that are easy to get wrong, the failure modes
that pass a shallow check, and how to verify a change. It deliberately omits
<basics the model already handles>. Sources: `references/sources.md`.

## Quick Reference

| Situation | Do | Not |
|---|---|---|
| <recognizable moment in the work> | <default> | <the habit to avoid> |

## Changed — do not write the old way

| Old idiom | Current idiom | Since | Why |
|---|---|---|---|
| <pattern> | <pattern> | v<major> | <one line> |

## Decisions

### <Decision: X versus Y>

Default to <X>. Reach for <Y> only when <condition>.
Why: <one line>.

## Footguns

- **<Legal-looking code that fails.>** Symptom: <what you see>. Fix: <what to do>.

## Verify

1. `<command>` — <what a pass means>.
2. <What to observe in the role's medium, and what "working" looks like.>

## Local

- <This repo's deliberate choice.> See `<exemplar path>`.
- The linter enforces <rule family>: fix findings, do not suppress them.

## Review checklist

- [ ] <Check derived from a rule above>
- [ ] <Check derived from a rule above>

## Common Mistakes

### ❌ <The highest-frequency failure>

**Problem:** <what gets written>
**Why it's wrong:** <the consequence>
**Fix:** <the current idiom>
```

`references/sources.md`:

```markdown
# Sources

Checked <YYYY-MM-DD> for <facet>@<major>.

| Source | URL | Version covered | Supports |
|---|---|---|---|
| <Official docs page> | <url> | <major> | <which rules> |
| <Upgrade guide> | <url> | <from> → <to> | <which "Changed" rows> |
```
