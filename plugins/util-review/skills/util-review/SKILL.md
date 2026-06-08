---
name: util-review
description: "Review Agent Skills, hooks, AGENTS.md/CLAUDE.md files, scripts, MCP configs, or workflow configurations for design flaws, unclosed loops, stale references, side effects, security risks, and portability issues. Use when: 'review this skill', 'audit this hook', '/util-review', 'check this config', or when evaluating any supplementary agent artifact for quality and correctness."
---

## Overview

Perform a deep, systematic review of supplementary agent artifacts — Agent
Skills, hooks, AGENTS.md/CLAUDE.md files, scripts, MCP configurations, or
workflow definitions. Surfaces design flaws, unclosed loops, incorrect
references, stale assumptions, side effects, security risks, portability issues,
and unanswered design questions that structural validators miss.

## Quick Reference

| Severity | Meaning | Blocks Pass? |
|----------|---------|--------------|
| **CRITICAL** | Breaks functionality, security risk, or data loss | Yes |
| **WARNING** | Degrades quality, reliability, or maintainability | No |
| **SUGGESTION** | Improvement opportunity or best practice deviation | No |

| Category | ID | Checks | Applies To |
|----------|----|--------|------------|
| Metadata & Registration | M | 7 | Skills |
| Structure & Format | S | 6 | Skills, AGENTS.md/CLAUDE.md |
| Instruction Quality | C | 6 | All |
| Dependencies & Assumptions | D | 6 | All |
| Reliability & Staleness | R | 5 | All |
| Side Effects | E | 6 | All |
| Security | X | 5 | All |
| Context Gathering | G | 5 | Skills, Hooks |
| Hooks-Specific | H | 7 | Hooks only |

**Pass criteria:** Zero CRITICAL issues.

## Workflow

### Phase 1: Input Detection & Scope

Determine what is being reviewed and read all files.

1. If `$ARGUMENTS` is provided, treat as path to the artifact
2. If no argument, ask the user what to review and where it lives
3. Detect artifact type from file structure:
   - **Skill**: Directory containing `SKILL.md` — also read `references/`, `scripts/`, `agents/`, `orchestrators/`, `templates/`
   - **Hook**: Hook config block in `settings.json` — also read any scripts it references
   - **AGENTS.md / CLAUDE.md**: instruction files — check for imports or linked references and read those too
   - **Script**: Standalone Python script — check PEP 723 metadata, dependencies
   - **MCP Config**: MCP server configuration — check tool references, permissions
   - **Composite**: Multiple types (e.g., a skill that also installs hooks)
4. **Read ALL files in scope before proceeding.** Do not review from memory or assumptions.

### Phase 2: Audience & Invocation Analysis

1. **Who is the audience?** Human users? Host agent auto-invocation? Both? Delegated agents?
2. **How is it invoked?** `/slash-command`? Auto-discovered by description? Event-triggered hook?
3. **Is registration correct?** Frontmatter must match intended invocation:
   - Both human and model → default host-discoverable metadata
   - Human-only → use the host's supported human-invocation flag or adapter metadata
   - Machine-only → use the host's supported model-invocation flag or adapter metadata
4. **Is discovery viable?** Will a host agent's description-matching find this when relevant? Are trigger keywords present? Is the key use case early in the description?

### Phase 3: Systematic Review

Run through each applicable check category. Classify every finding by severity and check ID. See `references/check-catalog.md` for detailed check descriptions.

#### Metadata & Registration (M001-M007)

| Check | What to verify |
|-------|---------------|
| M001 | Frontmatter YAML is valid and parseable |
| M002 | Name: kebab-case, ≤64 chars, matches directory name |
| M003 | Description: trigger conditions present, specific, ≤1024 chars, key use case front-loaded within first 250 chars |
| M004 | Invocation mode flags match intended audience |
| M005 | Context mode appropriate — `fork` for isolated work, default for session-persistent guidance |
| M006 | `allowed-tools` restrictions (if present) are complete and correct for the task |
| M007 | The artifact will actually be discovered and invoked when needed |

#### Structure & Format (S001-S006)

| Check | What to verify |
|-------|---------------|
| S001 | Required sections present: Overview, Quick Reference, Main Content, Common Mistakes |
| S002 | SKILL.md ≤500 lines; detailed material in `references/` (progressive disclosure) |
| S003 | Quick Reference is scannable and genuinely useful, not decorative |
| S004 | Common Mistakes contains realistic anti-patterns with actionable ❌/✅ fixes |
| S005 | Supporting files organized correctly (`references/`, `scripts/`, `assets/`) |
| S006 | Code blocks have proper language tags; tool names are correct (`rg` not `grep`) |

#### Instruction Quality (C001-C006)

| Check | What to verify |
|-------|---------------|
| C001 | Instructions are clear, precise, and unambiguous — a human could follow them |
| C002 | No conflicting or contradictory directives between sections |
| C003 | Ambiguous scope identified — words like "primarily", "generally" collapse to "always" or "never" in practice |
| C004 | Writing style: imperative form, third person ("the agent"), no specific AI names |
| C005 | Degrees of freedom match the task — high for creative, low for critical/fragile operations |
| C006 | Instruction volume within effective budget — compliance degrades past ~150-200 directives |

#### Dependencies & Assumptions (D001-D006)

| Check | What to verify |
|-------|---------------|
| D001 | All referenced file paths exist; resolve portable resources relative to the active `SKILL.md`, not hardcoded absolute paths |
| D002 | All referenced tools/MCP servers exist and are available; MCP names fully qualified (`Server:tool`) |
| D003 | Scripts are Python (not bash), use PEP 723 inline metadata, dependencies declared or stdlib-only |
| D004 | No implicit OS/shell/tool assumptions (`brew`, `apt`, `npm` globals, `osascript`) |
| D005 | Pre-existing file/config/state requirements are documented and checked before use |
| D006 | Portability: can this be shared or moved to another machine without modification? |

#### Reliability & Staleness (R001-R005)

| Check | What to verify |
|-------|---------------|
| R001 | No stale references — file paths, tool schemas, API endpoints all currently valid |
| R002 | No time-sensitive content — hardcoded dates, version numbers, temporal conditional logic |
| R003 | Instructions work across model capability tiers without vendor/model-specific assumptions |
| R004 | Critical content is front-loaded within first ~100 lines (compaction preserves first 5,000 tokens) |
| R005 | Assumption chains identified — if an early assumption breaks, does downstream logic cascade-fail? |

#### Side Effects (E001-E006)

| Check | What to verify |
|-------|---------------|
| E001 | File mutations: creates, modifies, or deletes files? Intentional and documented? |
| E002 | Git state: stages, commits, pushes, or modifies branches? Could interfere with user's working state? |
| E003 | External calls: network requests, API calls, webhooks? Reversible? |
| E004 | Context pollution: injects large content into context window? Cleans up after itself? |
| E005 | Permission escalation: requests broader tool permissions than the task requires? |
| E006 | Hook conflicts: could conflict with other hooks on the same event? (Parallel `updatedInput` rewrites are non-deterministic) |

#### Security (X001-X005)

| Check | What to verify |
|-------|---------------|
| X001 | No credentials embedded — API keys, passwords, tokens, connection strings |
| X002 | Injection surface — user input or external content interpolated into prompts without sanitization? |
| X003 | Excessive agency — tools beyond scope, permissions beyond need, autonomy without human oversight? |
| X004 | System prompt leakage — could instructions be extracted via crafted input? |
| X005 | Destructive operations gated behind confirmation — guardrails against `rm -rf`, force push, etc. |

#### Context Gathering (G001-G005)

| Check | What to verify |
|-------|---------------|
| G001 | All required context is identified — what info does the artifact need to function? |
| G002 | Acquisition strategy defined — user interaction? File reads? Tool calls? Env vars? |
| G003 | Missing context handled gracefully — fails clearly rather than proceeding on assumptions |
| G004 | User interaction quality — structured clarification asks few questions with clear options when the host supports it |
| G005 | Feedback loop closed — the artifact can validate its own output or the user can verify results |

#### Hooks-Specific (H001-H007)

| Check | What to verify |
|-------|---------------|
| H001 | Correct hook event for the intended trigger (26 events available) |
| H002 | Matcher is specific enough — broad PermissionRequest matchers auto-approve everything |
| H003 | Exit codes correct — 0 (proceed), 2 (block), other (non-blocking error) |
| H004 | No infinite loop risk — Stop hooks must check `stop_hook_active`; PreToolUse must not self-trigger |
| H005 | Shell profile safe — `~/.zshrc`/`~/.bashrc` echo statements won't corrupt JSON I/O |
| H006 | Parallel-safe — no conflicting `updatedInput` rewrites across multiple hooks on same event |
| H007 | JSON I/O compliant — input via stdin, output via stdout, fields ≤10,000 chars |

### Phase 4: Design Questions Audit

Surface unanswered questions from the design process:

1. **Unhappy path**: What happens when files are missing, tools fail, permissions are denied, or input is unexpected?
2. **Wrong context**: What happens when invoked in the wrong project, wrong branch, or without a git repo?
3. **Post-compaction**: Is critical content in the first 5,000 tokens? Will this skill degrade after compaction?
4. **Composition**: How does this interact with other skills/hooks? Conflicts? Redundancy? Ordering?
5. **Blast radius**: If this malfunctions — is damage limited to context, or does it mutate files/push code?
6. **Feedback loop**: Can the output be verified as correct? By the artifact itself? By the user?
7. **Assumption durability**: What assumptions could change? APIs, file structures, team conventions, tool availability?
8. **Maintenance**: Who maintains this? What triggers an update? How will staleness be detected?

### Phase 5: Report

```
## Review: [artifact-name] ([artifact-type])

### Verdict: PASS | FAIL (N critical issues)

### Summary
[2-3 sentences: what this does, overall quality, key concern]

### Findings

#### Critical
- **[ID]**: [description] — [specific location/line]

#### Warnings
- **[ID]**: [description] — [specific location/line]

#### Suggestions
- **[ID]**: [description] — [specific location/line]

### Unanswered Design Questions
[Numbered list from Phase 4 that lack clear answers]

### Positive Aspects
[What the artifact does well]

### Recommendations
[Prioritized, specific, actionable fixes]
```

## Common Mistakes

❌ **Reviewing from memory instead of reading files**
The artifact may have changed. Always read all files fresh in Phase 1.
✅ Read the complete artifact and all supporting files before starting review.

❌ **Checking only structure, ignoring semantics**
Perfect frontmatter and section headers can hide contradictory instructions or nonexistent tool references.
✅ Validate that instructions are correct, consistent, and grounded in current reality.

❌ **Missing transitive dependencies**
A skill references a script that imports a module that requires an MCP server. Each link is a break point.
✅ Trace the full dependency graph, not just first-level references.

❌ **Ignoring compaction behavior**
Skills get truncated to 5,000 tokens after compaction. Critical instructions buried at line 400 disappear.
✅ Verify critical content is front-loaded within the first ~100 lines.

❌ **Treating warning clusters as individual issues**
A single warning is fine. Five warnings in the same category signals systemic design rot.
✅ Look for patterns across warnings — clusters indicate deeper problems.

❌ **Skipping the unhappy path**
The artifact works perfectly with perfect input. What about missing files, tool failures, or unexpected user input?
✅ Explicitly probe failure modes and edge cases in Phase 4.

## Notes

- This review complements `pdm-skill-create` validation. That validates **structure**; this validates **design quality, correctness, and reliability**.
- For hook reviews, behavior differs by host and version. Check the adapter docs
  for the exact event schema.
- Skills using isolated/delegated context must provide enough actionable context
  for the delegated agent to produce useful output — guidelines alone without a
  task prompt return nothing.
- Findings must be specific and actionable. "Description could be better" is useless. "Description missing trigger keywords — add 'review this PR', 'code review' to match natural user phrasing" is useful.
- When reviewing composites (e.g., a plugin with skills + hooks + scripts), review each component individually, then review their interactions as a system.
