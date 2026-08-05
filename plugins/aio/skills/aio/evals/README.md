# AIO skill — eval suite

A skill is a prompt, not a program, so "evals" split into two layers with very different cost
and fidelity profiles.

## Layer 1 — `check_structure.py` (deterministic, cheap, standalone script)

Validates the invariants that must hold or the skill is *structurally* broken — independent of
any LLM behavior. Stdlib Python, no dependencies, no model calls.

```bash
python3 evals/check_structure.py          # full report
python3 evals/check_structure.py --quiet  # only WARN/FAIL + summary
```

Exit code **0** if no FAILs (WARNs are allowed), **1** if any FAIL. The nine checks:

| # | Check | Guards against |
|---|-------|----------------|
| 1 | Files present | A referenced reference-file was deleted/renamed. |
| 2 | Frontmatter valid | `name`/`description` missing or `name` ≠ directory. |
| 3 | Size budgets | Core SKILL.md (always-loaded body) over 350 lines / 2.5K words; KB over 500 (warn) / 600 (fail). |
| 4 | Pointer integrity | A `[KB:id]` with no heading, or a **duplicate** heading (which would break the private `aio-update` maintenance skill's deterministic find-and-update). |
| 5 | **Tier discipline** | Provenance (arxiv/CVE/DOI/"et al") leaking into the core rules tier — the bug this whole restructure exists to prevent. |
| 6 | KB format | A claim block missing its `**Rule:**` line (or `**Evidence:**`, warn, for non-table claims). |
| 7 | Trail discipline | A supersession trail growing unbounded instead of staying compressed. |
| 8 | aio-update paths | The four file paths the private `aio-update` maintenance skill writes to no longer exist (WARN if the paths are maintainer-machine-specific and simply absent here). |
| 9 | Registry cross-check | An arxiv id cited in the KB but **not logged** in the external, maintainer-local sources registry — an unverified or un-logged citation (WARN; the registry may legitimately lag a manual edit, and isn't part of this repo). |

This script is **not wired into this repo's CI** (see `.github/workflows/ci.yml`) and is not
invoked by anything shipped in this plugin — it's a standalone check a maintainer runs by hand,
per its own docstring. The author's private `aio-update` maintenance skill (not part of this
repo) runs it at its own Step 5 and expects exit 0 before reporting success; if you hand-edit the
skill or knowledge base in this repo, run it yourself the same way:

```bash
python3 evals/check_structure.py
```

## Layer 2 — `scenarios.md` (behavioral, LLM-judged, non-deterministic)

Golden scenarios that exercise the skill's *behavior* — does invoking `/aio` on a given input
actually produce the finding it should? Each scenario is an Input + a *Must include* / *Must NOT
do* rubric, targeting a distinctive thing the skill adds (escape-hatch detection, anti-over-
architecture, injection containment, memory pushback, the consolidation mechanic).

These are **not** wired to an automated runner by default — they're flaky and cost model calls.
Two ways to run:

1. **Manual** — paste a scenario's Input into a fresh agent session that has the `aio` skill
   loaded, then score the response against the rubric. Fast spot-check after a meaningful edit.
2. **Harnessed** — drive them through a judge: one agent answers each Input under the skill,
   a second (judge) scores the response against the rubric and returns pass/fail + reason. Run
   the set in parallel. (A `Workflow` or `Agent`-based runner is the natural fit; not committed
   here to keep the suite dependency-free.)

Behavioral coverage should track the rules tier: when the knowledge base picks up a genuinely new
rule (via the author's private `aio-update` maintenance skill, or a manual edit), add a scenario
that would fail if that rule were dropped.

## Why two layers

Layer 1 catches *structural* regressions cheaply and deterministically on every update — the
stuff that should never break silently. Layer 2 catches *behavioral* regressions (the skill stops
giving good advice) but costs model calls and human/LLM judgment. Run Layer 1 always; run Layer 2
when the rules or knowledge base change in a way that could shift the skill's actual output.
