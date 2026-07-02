# Authoring Contract — write skills that work everywhere

The rules `create-skill` writes against. **Default output is spec-pure**: the open
Agent Skills standard's portable core, read unmodified by ~30+ hosts. Claude-only
affordances are an **opt-in adapter**, never smuggled into the portable body.

> Full research note (citations, fast-moving host deltas):
> `/Users/matt.noxon/dev/work/dawks/spaces/ClaudeTooling/create-skill/portable-skill-authoring-contract.md`

**Contents**
- [1. Universal core](#1-universal-core-all-hosts)
- [2. Claude-Code-only surface](#2-claude-code-only-surface--omit-or-quarantine)
- [3. Per-host placement](#3-per-host-placement)
- [4. The description (highest-leverage field)](#4-the-description-the-single-highest-leverage-field)

## 1. Universal core (all hosts)

**Structure.** A skill is a directory `<name>/` with entrypoint `SKILL.md` (YAML
frontmatter + markdown body). Optional siblings by convention: `scripts/` (run via
bash — output enters context, code does not), `references/` (loaded on demand),
`assets/` (templates/data). **`name` must equal the directory name** — a hard rule.

**Portable frontmatter — the ONLY reliably cross-host fields:**

| Field | Req | Constraints |
|---|---|---|
| `name` | ✅ | 1–64 chars; lowercase `a-z0-9`+hyphens; no leading/trailing/consecutive hyphens; = dir name; no `claude`/`anthropic` |
| `description` | ✅ | 1–1024 chars; third person; states **what + when**; front-load keywords |
| `license` | — | SPDX name or bundled-file ref |
| `compatibility` | — | ≤500 chars; declares env/package/network needs |
| `metadata` | — | string→string map; **the sanctioned extension point** for host-specific extras |

Community fields (`version`, `author`, `tags`) are **not** in the spec — nest them
inside `metadata`, don't hoist to top-level. `allowed-tools` is in-spec but
**experimental** (value grammar is host-specific) — treat as non-portable.

**Progressive disclosure (3 levels):** L1 = name+description (always loaded, ~100
tok) · L2 = body (on match, **<500 lines / <5k tokens**) · L3 = `references/` (only
when the body points to them). References **one level deep**; files >100 lines get a
TOC. The body **persists for the session once invoked** — write tight standing
instructions that stay correct without the original request in view.

**Script portability (where "portable" skills actually break):**
- Forward slashes only; relative paths from the skill root.
- **No `npx` / `brew` / `uvx` / runtime `pip install` assumptions** — the Claude API
  runtime has no network and no install. Prefer **stdlib-only**; if deps are
  unavoidable, declare via `compatibility` + a PEP 723 header so the requirement is
  explicit, not a silent failure. *(Matt's rule: never `npx` at all.)*
- `scripts/` execution is "supported," not guaranteed — sandboxed hosts degrade a
  script-skill to read-only. **Don't hinge core behavior on a bundled binary running.**
- Scripts **solve, don't punt** (handle `FileNotFoundError`/`PermissionError`); no
  unexplained magic constants.

**Authoring quality (model-agnostic):** concise is key (context is a public good — add
only what the model lacks); degrees of freedom matched to task fragility; build 3 eval
scenarios *before* extensive docs; no time-sensitive info; one term per concept; one
default + an escape hatch.

**Two silent cross-host differences — design around them:** auto-invocation is
model-dependent (must-run capability → explicit invocation, not auto-trigger faith);
MCP tool refs need fully-qualified `Server:tool` names.

## 2. Claude-Code-only surface — omit or quarantine

Keep these **out of the portable body**; if genuinely needed, isolate in a labeled
Claude-only adapter, never inline:
- **Invocation-control frontmatter:** `disable-model-invocation`, `user-invocable`,
  `context: fork`, `agent`, `model`, `effort`, `argument-hint`, `paths`, `hooks`,
  `shell`, `disallowed-tools`.
- **Install-path vars:** `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_SKILL_DIR}`,
  `${CLAUDE_PROJECT_DIR}`, `$ARGUMENTS`, `$N` → replace with relative paths.
- **Dynamic injection:** inline `` !`cmd` `` / fenced ` ```! ` → other hosts render it
  as literal text.
- **Model/effort coupling:** `ultrathink`, Opus/Sonnet/Haiku references.
- **Hook/lifecycle dependence:** document the asymmetry — hosts without Stop/
  SessionStart events get no auto-wiring.
- **Plugin packaging** (`plugin.json`, `marketplace.json`, `.claude-plugin/`) is **the
  portability cliff**: the skill body travels, the packaging does not. Treat the skill
  as the portable unit and re-wire packaging per host.

## 3. Per-host placement

`.agents/skills/` is now the **broadly-shared project convention** (Copilot, Cursor,
Codex, Gemini, Amp, Cline, OpenCode, Warp all read it). Target it, or symlink
`.claude/skills/` → `.agents/skills/`.

| Host | Project placement | Caveat |
|---|---|---|
| Claude Code | `.claude/skills/` | reference host; all of §2 works here only |
| Codex | **`.agents/skills/`** | `.codex/skills/` is NOT a discovery path (silent zero-discovery); follows symlinks; MCP tools-only |
| Cursor 2.4+ | `.cursor/` · `.agents/` · `.claude/skills/` | reads `~/.claude/skills/` directly (biggest compat win); Inline Edit ignores skills |
| Copilot | `.github/skills/` · `.claude/` · `.agents/` | `gh skill install` CLI (Apr 2026); merges AGENTS.md |
| Gemini CLI | per extension docs | needs `context` block in `.gemini/settings.json` to prefer AGENTS.md |
| Zed / Windsurf | AGENTS.md + native skill dirs | also ACP hosts; Workflows are Windsurf's primary unit |
| Aider / Continue | — (no skills) | port = AGENTS.md / rules prose only |

**Prove placement with a real host-load** (point an actual `codex exec` / Cursor
session at the dir) — never trust a copier's identical-bytes output; that's portable
*by convention*, not *by contract*.

## 4. The description (the single highest-leverage field)

The host selects among 100+ skills on `description` alone. Rules:
- **Third person.** "Processes Excel files…", never "I/You can…". It's injected into
  the system prompt; mixed POV breaks discovery.
- **What + when**, with concrete trigger keywords, **front-loaded** — per-host budgets
  truncate it (Claude ~1,536-char combined listing; Codex ~8k / ~2% of context).
- A generic description that never fires is the **Invisible Skill** failure (see
  `judge-rubric.md`). Make the trigger specific enough to fire at the right moment and
  *only* then.
