# Check Catalog — Detailed Descriptions

Detailed rationale, what-to-look-for, and examples for each check in the `/util-review` framework.

---

## Metadata & Registration (M001-M007)

### M001: Frontmatter YAML Validity
**Severity:** CRITICAL
**Rationale:** Invalid YAML silently breaks skill loading in many hosts; some ignore
the frontmatter and treat the entire file as body content.
**What to look for:** Unclosed quotes, tabs instead of spaces, missing `---` delimiters, colons in unquoted values, special YAML characters (`@`, `#`, `!`) in unquoted strings.

### M002: Name Format
**Severity:** WARNING
**Rationale:** Non-conforming names may not register correctly or may conflict with other skills.
**What to look for:** Must be kebab-case, ≤64 chars, no leading/trailing/consecutive hyphens. Must match the directory name. Cannot contain "anthropic" or "claude".

### M003: Description Quality
**Severity:** CRITICAL (if missing/vague) | WARNING (if merely suboptimal)
**Rationale:** The description is the #1 failure point for auto-discovery. Host
agents use it to decide relevance. Vague descriptions = never invoked.
**What to look for:**
- Contains specific trigger conditions ("Use when...")
- Includes keywords users would naturally say
- Key use case in first 250 chars (truncation point in listings)
- ≤1024 chars total
- Third person voice ("the agent", not "I" or "you")
- Describes what it does AND when to use it

### M004: Invocation Mode
**Severity:** WARNING
**Rationale:** Side-effect-heavy skills (deploy, commit, send-message) should not be auto-invocable. Utility skills hidden from `/` menu frustrate users.
**What to look for:** Does the frontmatter flag combination match the intended invocation pattern?

### M005: Context Mode
**Severity:** WARNING
**Rationale:** `context: fork` runs in an isolated sub-agent — good for self-contained tasks, bad for skills that need to persist guidance in the session.
**What to look for:** Skills providing standing instructions (style guides, conventions) should NOT use fork. Skills performing discrete tasks (review, generate, validate) often should.

### M006: Allowed-Tools Restrictions
**Severity:** WARNING
**Rationale:** Overly broad = security risk. Overly narrow = skill can't complete its task.
**What to look for:** If `allowed-tools` is set, verify every tool the skill instructs the agent to use is in the list. If not set, consider whether it should be.

### M007: Discovery Viability
**Severity:** WARNING
**Rationale:** A well-written skill that never gets invoked is wasted effort.
**What to look for:** Run a mental simulation — if a user says the thing this
skill is for, would a host agent's description-matching select it? Are there
competing skills with similar descriptions?

---

## Structure & Format (S001-S006)

### S001: Required Sections
**Severity:** WARNING
**Rationale:** Consistent structure helps both agents and humans navigate skills
predictably.
**What to look for:** Overview, Quick Reference, main content section(s), Common Mistakes. Missing Common Mistakes is the most frequent omission.

### S002: Length & Progressive Disclosure
**Severity:** WARNING (>500 lines) | SUGGESTION (<500 but could offload)
**Rationale:** SKILL.md stays in context after invocation. After compaction, only 5,000 tokens preserved per skill, 25,000 combined budget across all invoked skills. Bloated skills crowd out other context.
**What to look for:** Line count. Dense reference material that belongs in `references/`. Detailed examples that could be separate files.

### S003: Quick Reference Quality
**Severity:** SUGGESTION
**Rationale:** Quick Reference is the first thing scanned. If it's unhelpful, the agent reads the full body unnecessarily.
**What to look for:** Tables with clear columns. Covers common operations. Scannable at a glance. Not just a repeat of the overview.

### S004: Common Mistakes Quality
**Severity:** SUGGESTION
**Rationale:** The ❌/✅ pattern prevents repeated errors. Weak common mistakes sections don't prevent anything.
**What to look for:** Are anti-patterns realistic (actually happen in practice)? Are fixes actionable and specific? Do they cover the most likely failure modes for this specific artifact?

### S005: Supporting File Organization
**Severity:** WARNING
**Rationale:** Misplaced files won't be found. Wrong directory semantics confuse the agent.
**What to look for:**
- `references/` = detailed documentation (loaded on demand)
- `scripts/` = executable Python scripts
- `assets/` = output templates, boilerplate (NOT loaded into context)
- `agents/` = sub-agent prompts
- `orchestrators/` = workflow definitions
- No README.md, CHANGELOG.md, INSTALLATION_GUIDE.md, CONTRIBUTING.md (these are not skill components)

### S006: Code Block Formatting
**Severity:** SUGGESTION
**Rationale:** Wrong tool names in examples teach the host agent to use the wrong
tools.
**What to look for:** `rg` not `grep`, `fd` not `find`, proper language tags on fenced blocks, correct syntax for tool invocations.

---

## Instruction Quality (C001-C006)

### C001: Clarity & Precision
**Severity:** WARNING (unclear) | CRITICAL (uninterpretable)
**Rationale:** If a human would struggle to follow it, the agent will too.
Ambiguous instructions produce inconsistent results.
**What to look for:** Each instruction should have one clear interpretation. Watch for pronouns with ambiguous antecedents, implicit context, and instructions that require domain knowledge not provided.

### C002: Contradictory Directives
**Severity:** CRITICAL
**Rationale:** When instructions conflict, agents pick one non-deterministically.
This produces unpredictable behavior.
**What to look for:** Scan for tension between sections. "Be concise" in one place, verbose examples in another. "Never modify files" in one place, file-editing instructions elsewhere. Strictness in rules vs. permissiveness in examples.

### C003: Ambiguous Scope
**Severity:** WARNING
**Rationale:** Hedge words collapse in practice. "Primarily use X" becomes "always use X" or "sometimes use X" depending on the run.
**What to look for:** "primarily", "generally", "usually", "where possible", "when appropriate", "if needed". Each should be replaced with explicit conditions.

### C004: Writing Style
**Severity:** SUGGESTION
**Rationale:** Consistent style improves instruction-following. Specific AI names create brittleness.
**What to look for:** Imperative form ("Read the file", not "You should read the file"). Third person ("the agent", not "Claude" or "you"). No first person ("I will...").

### C005: Degrees of Freedom
**Severity:** WARNING
**Rationale:** Too much freedom on critical operations = unpredictable results. Too little freedom on creative tasks = rigid, suboptimal output.
**What to look for:** Critical/fragile operations (deployments, destructive actions, data mutations) should have low freedom (exact scripts, no parameters). Creative tasks (writing, refactoring, architecture) should have high freedom (guidelines, not prescriptions).

### C006: Instruction Budget
**Severity:** WARNING
**Rationale:** Research indicates compliance degrades past ~150-200 directives. The system prompt already uses ~50.
**What to look for:** Count distinct instructions/rules/directives. If approaching budget, prioritize ruthlessly. Consider whether some instructions could be moved to examples or references.

---

## Dependencies & Assumptions (D001-D006)

### D001: File Path References
**Severity:** CRITICAL (broken path) | WARNING (non-portable path)
**Rationale:** Hardcoded absolute paths break on any other machine. Missing files break on every machine.
**What to look for:** Host-neutral paths for bundled files, ideally resolved
relative to the active `SKILL.md`. Relative paths for project files. Verify every
referenced path actually exists right now.

### D002: Tool & MCP References
**Severity:** CRITICAL (nonexistent tool) | WARNING (environment-specific)
**Rationale:** Referencing a tool that doesn't exist produces confusing errors. MCP server availability varies by environment.
**What to look for:** Every tool name mentioned in instructions. Fully qualified MCP names (`ServerName:tool_name`). Are these tools guaranteed to be available in all environments where this artifact will be used?

### D003: Script Dependencies
**Severity:** WARNING
**Rationale:** Bash scripts are not cross-platform. Missing PEP 723 metadata means `uv run` can't resolve dependencies.
**What to look for:** All scripts must be Python. PEP 723 inline metadata block present. Dependencies either stdlib or explicitly declared. Shebang line present. `if __name__` guard present.

### D004: Environment Assumptions
**Severity:** WARNING
**Rationale:** Assumptions about installed tools, OS, or shell break portability.
**What to look for:** Platform-specific commands (`osascript`, `notify-send`, `powershell`). Package managers (`brew`, `apt`). Global npm/pip packages. Shell-specific syntax (bash vs zsh vs fish).

### D005: Pre-existing Requirements
**Severity:** WARNING (undocumented) | SUGGESTION (documented)
**Rationale:** If the artifact needs something to exist before it runs, users need to know.
**What to look for:** Config files that must exist. Environment variables that must be set. Other skills/tools that must be installed. Git repo state requirements.

### D006: Portability Assessment
**Severity:** SUGGESTION
**Rationale:** Non-portable artifacts can't be shared and create maintenance burden.
**What to look for:** Could another user on a different machine use this without modification? What would they need to change?

---

## Reliability & Staleness (R001-R005)

### R001: Stale References
**Severity:** CRITICAL (broken reference) | WARNING (likely to go stale)
**Rationale:** References rot. Files get moved, APIs change, tools get renamed.
**What to look for:** Grep for every file path, URL, tool name, and API endpoint. Verify each exists and is current. Flag any that reference versioned resources without version pinning.

### R002: Time-Sensitive Content
**Severity:** WARNING
**Rationale:** Hardcoded dates and versions become misleading over time.
**What to look for:** Calendar dates, software versions, "current" or "latest" qualifiers, temporal conditional logic ("until Q3", "after the migration").

### R003: Model Sensitivity
**Severity:** SUGGESTION
**Rationale:** Instructions that work for a high-capability model may need more
detail for a smaller model. Model-specific assumptions break when the model field
changes.
**What to look for:** Reliance on capabilities that vary across models (complex
reasoning, long context, tool use patterns). Consider whether the skill specifies
a model or will be used across models.

### R004: Compaction Resilience
**Severity:** WARNING
**Rationale:** After compaction, only the first 5,000 tokens of a skill are preserved. Critical instructions at the end of a long skill disappear.
**What to look for:** Is the most critical content within the first ~100 lines? Could a compacted version of this skill still guide the agent correctly?

### R005: Assumption Chains
**Severity:** WARNING
**Rationale:** When logic builds on assumptions, a single broken assumption cascades through the entire chain.
**What to look for:** Identify the earliest assumptions the artifact makes (file structure, tool availability, project state). Trace what depends on each. Flag single points of failure.

---

## Side Effects (E001-E006)

### E001: File Mutations
**Severity:** WARNING (intentional, documented) | CRITICAL (undocumented or surprising)
**Rationale:** Unexpected file changes can destroy user work.
**What to look for:** Any instruction to create, modify, or delete files. Is each mutation intentional and documented? Could the user be surprised?

### E002: Git State Changes
**Severity:** CRITICAL (undocumented commits/pushes) | WARNING (staging changes)
**Rationale:** Git operations affect shared state and can be difficult to reverse.
**What to look for:** `git add`, `git commit`, `git push`, `git checkout`, `git reset`. Does the artifact touch git state? Is the user warned?

### E003: External Calls
**Severity:** WARNING (API calls) | CRITICAL (irreversible external actions)
**Rationale:** Network requests can have real-world consequences — messages sent, resources created, money spent.
**What to look for:** HTTP requests, webhook invocations, API calls, Slack messages, Jira updates. Are these reversible? Is confirmation required?

### E004: Context Pollution
**Severity:** WARNING
**Rationale:** Large injections consume finite context window space, degrading performance.
**What to look for:** Skills that dump large file contents, verbose logging, or repeated instructions into the conversation. Does the artifact add content proportional to its value?

### E005: Permission Escalation
**Severity:** WARNING
**Rationale:** Principle of least privilege — artifacts should request only what they need.
**What to look for:** `allowed-tools` broader than necessary. Hook `allow` decisions on PermissionRequest. Instructions that encourage bypassing permission checks.

### E006: Hook Conflicts
**Severity:** WARNING
**Rationale:** Multiple hooks on the same event run in parallel. Conflicting writes produce non-deterministic results.
**What to look for:** Other hooks registered on the same event. `updatedInput` rewrites from multiple sources. Ordering assumptions between hooks.

---

## Security (X001-X005)

### X001: Credential Exposure
**Severity:** CRITICAL
**Rationale:** OWASP LLM07 — credentials in prompts can be extracted via prompt injection or system prompt leakage.
**What to look for:** API keys, passwords, tokens, connection strings, private paths to credential files. Even in comments or examples.

### X002: Injection Surface
**Severity:** CRITICAL (direct interpolation) | WARNING (indirect via tool results)
**Rationale:** OWASP LLM01 — prompt injection is the #1 LLM vulnerability, found in 73%+ of production deployments.
**What to look for:** User input concatenated into prompts via f-strings, `.format()`, or template literals. Tool results passed to other tools without validation. External content (URLs, file contents) injected into instructions.

### X003: Excessive Agency
**Severity:** WARNING
**Rationale:** OWASP LLM06 — three root causes: excessive functionality, excessive permissions, excessive autonomy.
**What to look for:** Tools granted beyond what's needed. Permissions broader than the task requires. Autonomous actions without human confirmation gates on irreversible operations.

### X004: System Prompt Leakage
**Severity:** SUGGESTION (general risk) | WARNING (contains sensitive info)
**Rationale:** OWASP LLM07 — research shows models cite decision criteria in 98% of verbose responses.
**What to look for:** Internal business logic, proprietary algorithms, access control patterns, or competitive information embedded in skill instructions that could be extracted.

### X005: Destructive Operation Safeguards
**Severity:** CRITICAL (unguarded destructive ops)
**Rationale:** `rm -rf`, `git push --force`, `DROP TABLE` — irreversible operations need gates.
**What to look for:** Any instruction that performs or enables destructive operations. Are there confirmation steps? Is there a rollback path?

---

## Context Gathering (G001-G005)

### G001: Required Context Identification
**Severity:** WARNING
**Rationale:** If the artifact doesn't know what it needs, it can't reliably get it.
**What to look for:** Is there an explicit or implicit list of information the artifact needs to function? Is anything missing?

### G002: Acquisition Strategy
**Severity:** WARNING
**Rationale:** Different strategies have different reliability profiles. User interaction is reliable but slow. File reads are fast but may fail.
**What to look for:** How does the artifact get each piece of required context?
Structured user clarification? File reads? Tool calls? Environment variables? Is
each strategy appropriate for its data?

### G003: Missing Context Handling
**Severity:** CRITICAL (proceeds on wrong assumptions) | WARNING (fails silently)
**Rationale:** The worst outcome is confidently proceeding with incorrect assumptions.
**What to look for:** What happens when a required file doesn't exist? When a tool call fails? When the user can't provide information? Does the artifact fail clearly or silently assume?

### G004: User Interaction Design
**Severity:** SUGGESTION
**Rationale:** Poor interaction design wastes user time and produces worse input.
**What to look for:** A small number of questions per interaction. When the host
supports structured choices, options are mutually exclusive and collectively
exhaustive.

### G005: Feedback Loop Closure
**Severity:** WARNING
**Rationale:** An artifact that can't verify its own output depends entirely on user vigilance.
**What to look for:** Can the artifact run a validator, check, or test after completing its work? If not, is the output format clear enough for the user to manually verify?

---

## Hooks-Specific (H001-H007)

### H001: Event Type Appropriateness
**Severity:** CRITICAL (wrong event)
**Rationale:** 26 hook events exist — using the wrong one means the hook fires at the wrong time or not at all.
**Key events:** `PreToolUse` (block/rewrite before execution), `PostToolUse` (react after execution, can't undo), `Stop` (gate completion), `PermissionRequest` (auto-approve/deny), `SessionStart` (setup), `UserPromptSubmit` (validate input).

### H002: Matcher Specificity
**Severity:** CRITICAL (overly broad on PermissionRequest) | WARNING (overly broad elsewhere)
**Rationale:** A broad PermissionRequest matcher auto-approves everything — shell commands, file writes, everything.
**What to look for:** Empty matchers, `.*` patterns, overly inclusive pipe-separated lists. Matchers are case-sensitive (`bash` ≠ `Bash`).

### H003: Exit Code Handling
**Severity:** CRITICAL (wrong exit code)
**Rationale:** Exit 0 = proceed. Exit 2 = block action. Other = non-blocking error. Getting this wrong means either blocking when you shouldn't or allowing when you shouldn't.
**What to look for:** Every code path in the hook script. Are all exit codes intentional and correct?

### H004: Infinite Loop Risk
**Severity:** CRITICAL
**Rationale:** A stop hook that always returns the host's continue/interrupt code creates an infinite loop — the agent can never finish responding.
**What to look for:** Stop hooks must check `stop_hook_active` field and exit 0 when true. PreToolUse hooks must not trigger tool calls that re-trigger themselves.

### H005: Shell Profile Pollution
**Severity:** WARNING
**Rationale:** Unconditional `echo` in `~/.zshrc` or `~/.bashrc` prepends garbage to hook JSON output, causing parse failures.
**What to look for:** Does the hook rely on parsing JSON from stdout? Does the user's shell profile contain unconditional output? Recommend wrapping profile output in `[[ $- == *i* ]]` guards.

### H006: Parallel Execution Safety
**Severity:** WARNING
**Rationale:** Multiple hooks on the same event run in parallel. Last `updatedInput` write wins non-deterministically.
**What to look for:** Other hooks on the same event. Any `updatedInput` rewrites. Shared state (files, env vars) modified by multiple hooks.

### H007: JSON I/O Protocol
**Severity:** WARNING
**Rationale:** Hooks communicate via stdin/stdout JSON. Malformed output is silently ignored or causes errors.
**What to look for:** Reads input from stdin (not arguments). Writes structured JSON to stdout. Fields ≤10,000 chars. Stderr used only for blocked-action feedback (exit 2) or error messages.
