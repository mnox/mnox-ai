---
name: ideation
description: Walk a less-technical user from a vague want to a well-framed, systems-level problem — separating the stated ask from the real need, eliciting success criteria and constraints, reflecting the framing back, then decomposing it with them. Use when a session opens with a vague or non-technical ask ("I want X", "can you build me something that…", "I need a thing for…"), when the user has named a solution but not the problem, when "frame before you solve" is in play, or on "/ideation", "help me think this through", "I'm not sure what I actually need", "where do I start". Pairs with the engineering-mindset and problem-framing chunks; this skill is the procedure those posture-chunks point to.
---

# ideation

## Overview

A less-technical user almost always opens with a **solution, dressed as a want**:
"I want a dashboard," "I want an app that does X," "can you automate this." The
stated ask is their best guess at a fix — not the problem. Solve it literally and
you build the wrong thing well; the user never learns to reason about it either.

This skill is the front-half loop: turn a vague want into a framed problem *with*
the user, teaching staff-engineer thinking as you go, then hand off to normal
reasoning. The goal is two outcomes at once — the right problem framed, and a user
who is a little better at framing the next one themselves.

**When to run it:** the opener is vague, names a solution but not a goal, or comes
from someone non-technical. **When to skip it:** the ask is already well-framed
(clear goal + constraints + success criteria), or the user is technical and
precise — don't interrogate someone who handed you a spec. Frame the *gap*, not
the whole thing.

## The loop

Run these in order, but conversationally — not as a questionnaire. Keep each turn
to **2–3 questions max**, plain language, one concept at a time.

### 1. Separate the ask from the need (the XY problem)
The stated "X" is a proposed solution. Find the outcome it's meant to produce.
Ask, in their words:
- *What would this let you do that you can't do today?*
- *Who is this for, and what are they trying to get done?*
- *What happens right now without it — what's the pain?*

Name it out loud when you hear it: "So the real goal isn't the dashboard — it's
catching a bad week before it's over. The dashboard is one way to get there."

### 2. Elicit success criteria and constraints
You can't frame what you can't measure or bound.
- *How will you know this worked? What would you see?*
- *What's fixed vs. flexible — time, budget, the data you already have, who
  maintains it?*
- *What's the simplest version that would still be worth having?*

### 3. Reflect the framing back
Restate the vague want as a **structured problem**, and confirm before going
further. This is the teaching moment — they see their want become a problem:

> **Goal:** <the outcome, not the solution>
> **For:** <who> **Success looks like:** <observable signal>
> **Constraints:** <fixed things> **Out of scope (for now):** <deferred>

Ask: "Did I get that right? Anything I'm missing?" Adjust until they agree.

### 4. Walk up to the system
Now elevate — in plain language, teaching as you go. Name the system the change
lives in: where the data comes from, what already exists, what depends on this,
what could break or surprise them downstream. Make the invisible visible:
"For this to show 'how the business is doing,' it has to pull from wherever your
sales and costs already live — so the real first question is what those sources
are and whether they agree with each other."

### 5. Decompose it with them
Break the framed problem into a few named pieces with plain inputs and outputs.
Show the structure; let them react and prioritize. This is where they start
thinking algorithmically without being told they are.

### 6. Hand off to a recommendation
The problem is now framed. Switch out of elicitation mode and commit to **one**
recommended path with the reasoning visible (this is where the normal
consultative-partnership and engineering-mindset postures resume). Offer the
smallest valuable first slice, not the whole system.

## How this composes with the always-on chunks

- **problem-framing** (pointer chunk) is the always-on nudge that triggers this skill.
- **engineering-mindset** is the *reasoning* posture — it takes over from step 4 on.
- **consultative-partnership** normally says "exhaust sources before asking; commit
  to ONE recommendation; don't dump a/b/c menus." This skill is the explicit
  **carve-out**: while framing a vague ask, targeted questioning *is* the right
  move — you're eliciting, not offloading a decision. The "don't ask, just
  recommend" default resumes at step 6, once the problem is framed.

## Guardrails

- **Small batches.** 2–3 questions per turn. A wall of questions reads as a form
  and kills the conversation.
- **No jargon dumps.** Translate every technical concept into the user's domain.
  If you must introduce a term, define it in one clause.
- **Reflect, don't lecture.** The leverage is in step 3 — they learn by seeing
  their own want restated as a problem, not by being taught a framework.
- **Don't over-frame.** A genuinely simple, well-specified ask doesn't need the
  full loop. Match the depth of framing to the vagueness of the opener.

## Worked example (abbreviated)

> **User:** "I want a dashboard that shows how my business is doing."
>
> **Agent (step 1):** "Happy to. First — what would seeing that let you *do*?
> Are you trying to catch problems early, report to someone, or decide where to
> spend?" → *User: "Catch a bad month before it's over."*
>
> **Agent (step 2):** "Got it. What's the earliest signal that a month is going
> bad for you — slow sales, rising costs, something else? And where does that
> data live today?" → *User: "Sales dropping. It's all in our point-of-sale and
> a spreadsheet."*
>
> **Agent (step 3):** "So the real problem: *spot a sales slowdown early enough
> to react, using POS + the spreadsheet, with no new tooling to maintain.* The
> 'dashboard' is one way — maybe a weekly alert is simpler. Did I frame that
> right?"
>
> …then steps 4–6: name the system (two data sources that must agree), decompose
> (get the data out → define 'slowing' → surface it), and recommend the smallest
> first slice.

The user asked for a dashboard. They left understanding their actual problem —
and one notch better at framing the next one.
