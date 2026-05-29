# Schema / Data-Structures Review — <target>

**Score:** <0–100> / 100 &nbsp;·&nbsp; **Verdict:** <HARD BLOCK | REVIEW | RISKY | SAFE>
**Mode:** <single-pass | multi-agent fan-out> &nbsp;·&nbsp; **Lenses run:** <list>
**Target:** <file / PR / module / doc> &nbsp;·&nbsp; **Date:** <YYYY-MM-DD>

> Verdict key: **HARD BLOCK** = ≥1 CRITICAL · **REVIEW** = ≥1 HIGH · **RISKY** = only MEDIUM · **SAFE** = LOW/NITPICK only.

## Summary

<2–4 sentences: what was reviewed, the headline risks, and the single most important action. Lead with the takeaway.>

| Severity | Count |
|---|---|
| 🔴 CRITICAL | <n> |
| 🟠 HIGH | <n> |
| 🟡 MEDIUM | <n> |
| 🔵 LOW | <n> |
| ⚪ NITPICK | <n> |

## Findings

> Ordered by severity. Each finding: severity + location · confidence (HIGH/CRITICAL) · problem · impact · fix · blocker. Findings that appeared under multiple lenses are merged and cite all lenses.

### 🔴 Critical

**[🔴 CRITICAL] `<table.column / file:line>` — <one-line title>** &nbsp; [confidence: HIGH] &nbsp; _(lens: <lens(es)>)_
<problem — one factual sentence>
**Impact:** <what breaks / corrupts / is exploitable>
**Fix:** <concrete DDL / migration / type change>
**Blocker:** yes

### 🟠 High
<...>

### 🟡 Medium
<...>

### 🔵 Low
<...>

### ⚪ Nitpicks
<terse bullet list>

## Verification notes

<For each CRITICAL/HIGH: one line confirming the failure/attack chain was validated in the main context, or noting what was demoted/dropped and why.>

## Out of scope / could not assess

<Anything that needs runtime data, query patterns, production scale figures, or human judgment to confirm — and what would resolve it. State assumptions explicitly.>
