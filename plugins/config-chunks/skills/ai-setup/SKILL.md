---
name: ai-setup
description: First-run guided onboarding that sets up an agent for a less-technical user — leads with a one-shot recommended set of guidance "chunks" (or 2–3 plain-language questions to tailor), confirms, applies them by driving the config-chunks engine into CLAUDE.md / AGENTS.md, then offers safe permission setup. Use when the user says "/ai-setup", "set up my agent", "set up my agent guidance", "onboard me to chunks", "configure my CLAUDE.md guidance", "first-run setup", "recommend chunks for me", "help me get started with config-chunks", "which chunks should I use", or otherwise wants a guided walkthrough to subscribe to guidance chunks. Re-runnable any time; for piecemeal management afterward use /chunks, for permissions use /permission-setup, and to author new chunks use /chunk-review.
---

# ai-setup

## Overview

`config-chunks` is a package manager for **guidance chunks** — small, versioned
Markdown files of agent-instruction guidance that are concatenated into an
always-on context bundle and wired into the user's host instruction files
(`@import`ed into CLAUDE.md and/or inlined into AGENTS.md). Each chunk is an
opt-in. The user subscribes by **group** (a named bundle of chunk slugs) or by
individual **chunk slug**, and picks which host **targets** receive the bundle.

This skill is the **first-run guided layer**. It does NOT invent a new config
surface — it interviews the user, maps their answers to a concrete set of
group/chunk slugs + targets, shows that set for confirmation, and then applies
it by driving the existing engine (the same one `/chunks` drives). It is
re-runnable any time the user wants to revisit their setup.

Distinction from the companion skill:

- **`/chunks`** — ongoing, single-action management ("add this chunk", "set my
  targets", "doctor"). Use it for piecemeal edits after setup.
- **`/ai-setup`** (this skill) — the guided interview that produces a *whole
  recommended set at once* for someone starting fresh.

## Resolving paths (do this first)

Everything this skill reads or runs lives under the **engine home** — the
directory holding `scripts/`, `chunks/`, `groups/`, and `references/`. This skill
must **self-discover that home before doing anything else**; do not assume an env
var is set and do not rely on a bare `../../` path (it only resolves when the
shell's working directory is this skill directory — Claude Code sets that, but
Cursor/Codex and other hosts run from the project root).

You know the **absolute path of this skill's own directory** — it's where you're
reading this `SKILL.md` from. Substitute it for `<skill-dir>` below and run the
probe. It checks candidate homes in precedence order and binds `ENGINE` to the
first one that actually exists:

```bash
# Substitute <skill-dir> with the ABSOLUTE path of THIS skill directory,
# e.g. /Users/you/.cursor/skills/ai-setup  (or .../.claude/plugins/.../skills/ai-setup).
SKILL_DIR="<skill-dir>"

ENGINE=""
for cand in \
  "${CONFIG_CHUNKS_HOME:+$CONFIG_CHUNKS_HOME/scripts/chunks-config.sh}" \
  "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/scripts/chunks-config.sh}" \
  "$SKILL_DIR/../.engines/config-chunks/scripts/chunks-config.sh" \
  "$SKILL_DIR/../../scripts/chunks-config.sh"; do
  [ -n "$cand" ] && [ -f "$cand" ] && { ENGINE="$cand"; break; }
done

if [ -z "$ENGINE" ]; then
  echo "config-chunks engine not found near this skill." >&2
  echo "Fix: re-export with 'python3 scripts/export_skills.py --with-engine', or" >&2
  echo "     set CONFIG_CHUNKS_HOME to the engine home (the dir holding scripts/)." >&2
else
  ROOT="$(cd "$(dirname "$ENGINE")/.." && pwd)"   # engine home, absolute
  echo "engine: $ENGINE"
fi
```

The four candidates, in order: an explicit `CONFIG_CHUNKS_HOME` (set by
`install.sh` / `export_skills.py --with-engine`), Claude Code's
`CLAUDE_PLUGIN_ROOT`, the **`--with-engine` exported layout** (the engine is a
deterministic sibling at `<skill-dir>/../.engines/config-chunks/`), and finally
the **in-repo / Claude-plugin layout** (`<skill-dir>/../../`). The exported-sibling
probe is what lets the interactive flow work on Cursor/Codex with **zero env
vars** — neither host injects one, but the engine ships right next to the skill.

Throughout this skill, read `../../chunks/`, `../../groups/`, and
`../../references/` as `$ROOT/chunks/`, `$ROOT/groups/`, and `$ROOT/references/` —
absolute paths, not CWD-relative ones.

## The engine it drives

Run the engine via Bash, always through the absolute `$ENGINE` path:

```bash
bash "$ENGINE" <command> [args]
```

Subcommands this skill uses:

| Command | Effect |
|---|---|
| `list` | Show current subscriptions, targets, resolved slugs, and what's available. |
| `set-targets <claude\|agents>...` | Replace the target set with exactly the listed hosts. |
| `add-group <name>` | Subscribe to a group (e.g. `recommended`). Idempotent. |
| `add-chunk <slug>` | Opt into a standalone chunk. Idempotent. |
| `doctor` | Validate the config and bundle health. |

Every mutation auto-publishes the first-party chunks and runs the reconciler, so
the change lands in the bundle (and the host files) immediately — no session
restart needed. **Never hand-edit `~/.claude/config/chunks.yaml`** from this
skill; only drive the engine.

## The chunk roster

The shipped first-party chunks live at `../../chunks/*.md`. Each chunk file's
frontmatter carries a `name:` (its slug) and a `summary:` (its one-line
description). The current roster:

| Slug | What it gives the agent |
|---|---|
| `problem-framing` | When you open with a vague "I want X", frame the real problem before building — draws the goal, success criteria, and constraints out of you first. |
| `engineering-mindset` | Reason about your request at a systems level: see the whole system, decompose before solving, name the tradeoffs out loud. |
| `context-hygiene` | Keep the main thread a coordination layer; delegate discovery to sub-agents; protect the context budget. |
| `consultative-partnership` | Reduce the user's cognitive load; exhaust sources, recommend one path, flag adjacent risks proactively. |
| `discovery-pipeline` | Exhaust sources in a fixed order before asking or guessing. |
| `code-skepticism` | Treat existing code as evidence of what was built, not what is correct; reason from requirements. |
| `communication-style` | Brevity by default; lead with the takeaway; frame at the right altitude. |
| `coding-style` | Self-documenting code, type strictness, no legacy/back-compat shims. |

The first two — **`problem-framing`** and **`engineering-mindset`** — are the
ones that matter most for a **less-technical user**: together they make the agent
draw the real problem out of a vague ask and then reason about it like a staff
engineer, instead of literally building the first thing you say. Headline them
when recommending to someone who isn't an engineer.

The one-shot `recommended` group bundles the sensible defaults. Read its members
at run time from `../../groups/recommended.yaml`.

> Always read the **live** roster and group membership at run time (`../../chunks/`
> and `../../groups/`) rather than trusting this table — the library evolves.
> Each chunk's authoritative one-line summary is the `summary:` field in its
> frontmatter.

## On rubric scores — don't show them to the user

Each chunk has an authoring-quality rubric score in
`../../references/chunk-scores.md`. **That score is an internal authoring metric —
do not surface it in the user-facing onboarding.** To a non-engineer it's noise
that invites "why is this one a 60?" detours during a setup that should just land
a good default. Present chunks by their plain-language summary only. (The scores
remain available via `/chunk-review` for anyone authoring or auditing chunks.)

---

## Flow

### Step 0 — Frame it, and lead with the fast path

Tell the user, in two plain sentences, what chunks are and that this is a one-time
(re-runnable) guided setup that ends by writing the assembled guidance bundle into
their instruction files.

**Lead with the fast path — make it the default, not a fallback:** *"The simplest
option is the `recommended` set — eight chunks that make me frame your problem
before building, reason at a systems level, recommend one clear path, and write
clean code. Most people should just take it. Want me to apply the recommended set
(I'll confirm before writing anything), or walk through a couple of questions to
tailor it?"* Only run the interview (Step 2) if they choose to tailor; otherwise
go straight to Step 4 with the `recommended` group.

### Step 1 — Preflight, then read the live state

**Preflight first — the guardrail around discovery.** Before interviewing,
confirm the engine resolved and the config is healthy. If the probe left
`$ENGINE` empty, **stop and surface the remediation it printed** (re-export
`--with-engine`, or set `CONFIG_CHUNKS_HOME`) — do not continue, there's nothing
to drive. Otherwise validate config health and read current state:

```bash
[ -n "$ENGINE" ] || { echo "engine unresolved — see Resolving paths remediation"; exit 1; }
bash "$ENGINE" doctor   # config/bundle health; surface any ✗ line verbatim
bash "$ENGINE" list     # current subscriptions, targets, resolved slugs
```

Read both before interviewing. Also read `$ROOT/references/chunk-scores.md` (for
scores), the `summary:` line of each `$ROOT/chunks/*.md` (for one-liners), and
`$ROOT/groups/recommended.yaml` (for the group's membership). If the user is
already subscribed to things, acknowledge it and frame this run as a revisit.

### Step 2 — Tailor it (only if they declined the fast path)

Skip this entirely if the user took the recommended set in Step 0. Otherwise ask
**2–3 short, outcome-framed questions in plain language** — no engineering jargon,
no one-question-per-chunk interrogation. Recommend a default for each so the user
can accept with a word, and use the host's native question UI if available.

1. **Which tool(s) do you use?** Claude Code / a tool that reads an `AGENTS.md`
   (Codex, Cursor, etc.) / both. → maps to **targets**: `claude`, `agents`, or
   both. *Default: whatever `list` auto-detected; if unsure, both.*
   - **If they pick a non-Claude (`agents`) host, you must also pin the AGENTS.md
     path.** The engine's fallback is `~/.claude/AGENTS.md`, which *only Claude
     Code reads* — leaving it there writes the bundle to a file Codex/Cursor never
     load. Ask where their `AGENTS.md` lives (e.g. `~/.codex/AGENTS.md`, or
     `<project>/AGENTS.md` for Cursor) and carry that path into Step 5. Auto-refresh
     is also Claude-only on these hosts — tell them they'll re-run the reconcile
     themselves (point to the plugin README's **Host support** section).
2. **What will you mostly do with the agent?** Mostly *planning, writing, and
   thinking things through* — or also *having it write and change code*?
   - **Planning / writing / thinking** → the non-code chunks: `problem-framing`,
     `engineering-mindset`, `consultative-partnership`, `communication-style`,
     `discovery-pipeline`, `context-hygiene`.
   - **Also writing code** → all of the above **plus** `code-skepticism` and
     `coding-style`. *Default: include the code chunks — they're harmless if you
     don't code, and there when you do.*

That's it. The whole recommended set is the union of both; this question just
decides whether to drop the two code-specific chunks for a non-coder. If the user
wants finer control, point them to **`/chunks`** for per-chunk management rather
than expanding this interview.

### Step 3 — Map answers → a concrete selection

Translate the answers into:

- **targets**: a list of `claude` and/or `agents`.
- **groups**: include `recommended` if the user chose the fast path or accepted
  the full default set.
- **chunks**: the individual slugs for each affirmative answer (used when the
  user customized rather than taking the whole group). If the user's selection
  equals the `recommended` group's membership, prefer subscribing to the group
  (`add-group recommended`) over enumerating every slug.

### Step 4 — Present the recommended set, then CONFIRM

Show a table of the chosen chunks before applying anything — **summary only, no
rubric scores**:

| Chunk | What it does for you |
|---|---|
| `<slug>` | `<summary: from the chunk file, in plain language>` |

Below the table, state the chosen **targets** (e.g. "Targets: claude, agents")
and which host files that means writing to (`~/.claude/CLAUDE.md` for `claude`,
the AGENTS.md target for `agents`). Then **explicitly ask for confirmation** —
this step writes to the user's instruction files. Do not proceed without a clear
yes.

### Step 5 — Apply via the engine

On confirmation, run the engine. Set targets first, then subscribe:

```bash
# 1) targets — replace the set with exactly the chosen hosts
bash "$ENGINE" set-targets <claude and/or agents>

# 1b) if `agents` is targeted on a NON-Claude host, pin that host's AGENTS.md
#     (skip for Claude-only — its default is correct). Use the path from Step 2.
bash "$ENGINE" set-agents-path <~/.codex/AGENTS.md | project AGENTS.md>

# 2a) fast path / full defaults — one group covers it
bash "$ENGINE" add-group recommended

# 2b) customized — opt into each chosen chunk individually
bash "$ENGINE" add-chunk consultative-partnership
bash "$ENGINE" add-chunk communication-style
# ...one add-chunk per affirmative answer
```

Run `set-agents-path` **only** when the user targets a non-Claude `agents` host —
it's the durable, engine-driven way to set the path (never hand-edit
`chunks.yaml`). Claude-only users skip it; the `~/.claude/AGENTS.md` default is
correct for them.

Capture stdout/stderr from every call. Each mutation auto-publishes and
reconciles. If any call prints a `warning` or non-zero result, surface it
verbatim and recommend `doctor`.

### Step 6 — Verify it landed, then report

**Close the guardrail loop: confirm the bundle actually reached the target files.**
A clean engine exit is necessary but not sufficient — verify the marker is present
in each host file you targeted:

```bash
# claude target → marker-wrapped @import in ~/.claude/CLAUDE.md
grep -q 'config-chunks:start' ~/.claude/CLAUDE.md && echo "claude: landed"

# agents target → inlined body marker in the AGENTS.md path you set in Step 5
grep -q 'config-chunks:start' <agents-path> && echo "agents: landed"
```

If a marker is missing, the write didn't reach that file — run `bash "$ENGINE"
doctor`, surface its output, and check the AGENTS.md path (the most common cause
on non-Claude hosts is the bundle landing in the default `~/.claude/AGENTS.md`
instead of the host's real path; re-run `set-agents-path`).

On success, confirm in a few sentences:

- the **subscriptions** that now apply (groups and/or standalone chunks),
- the active **targets**,
- that the bundle **reconciled** into their CLAUDE.md (`@import`) and/or AGENTS.md
  (inlined body) — no restart needed.

Optionally run `bash "$ENGINE" list` and quote the resolved slug set as proof.

### Step 7 — Offer permission setup

Guidance chunks shape *how the agent thinks*; permissions decide *what it's
allowed to do*. They're independent modules of the same onboarding — having
landed the chunks, offer the second: *"Want me to help set safe permissions too?
It's a quick conservative starting point so the agent asks before doing anything
risky."* On yes, **invoke the `permission-setup` skill** (it detects the
provider/surface, recommends the Cautious posture, and delegates the write —
config-chunks never writes security config itself). On no, mention they can run
`/permission-setup` any time. This step is independent of the chunk write above —
declining it doesn't undo anything.

### Step 8 — Point forward

Close by pointing forward: **`/chunks`** for ongoing management (add/remove a
single chunk, change targets, doctor), **`/permission-setup`** to revisit
permissions, and **`/chunk-review`** for authoring or reviewing new chunks.

## Guardrails

- This skill never hand-edits `chunks.yaml` or any host file — only the engine
  mutates state, and only the reconciler writes the bundle into CLAUDE.md /
  AGENTS.md. It **never writes security config** either — permissions are
  delegated to the `permission-setup` skill, which itself only recommends.
- Never apply anything before the Step 4 confirmation.
- **Never show users the rubric scores** — they're an internal authoring metric.
  Present chunks by their plain-language summary only.
- Read the live roster and group membership at run time; don't trust a static
  list if the directories disagree.
