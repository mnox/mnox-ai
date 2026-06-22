# Permission Profiles — Provider-Agnostic Safe Defaults

Reference data for the permission-recommendation step of onboarding. The
`permission-setup` flow reads this at run time and renders the conservative
posture for the user's detected (provider, surface). **config-chunks never
writes these files itself** — it recommends, shows the exact config, and
delegates the write to the platform (the user, or a platform config skill).

Verified against official docs (mid-2026). Treat post-cutoff specifics as
evolving; each provider section carries source URLs + drift flags.

---

## The canonical model

Every agent permission system, across every provider, reduces to **three dials**
plus one **never-touch** setting:

| Dial | What it controls | Conservative (recommended) |
|---|---|---|
| **Capability** | What the agent can *do* to your machine | Read freely; edits reviewed; no command exec until you opt up |
| **Approval** | *When* it must stop and ask you | Auto-run only known-safe read ops; **ask before** anything that changes, runs, or sends |
| **Network** | Outbound internet access | **Off** (or a tight allowlist of package registries) |
| **⛔ Bypass** | The "do everything without asking" mode | **Never enable** outside a throwaway container/VM |

The recommended default for a less-technical user is the same everywhere —
**Cautious**: read-only or review-gated edits, approval required on anything
risky, network off, bypass disabled. The user opts *up* one rung at a time as
trust grows; they never start at the top.

**The universal footgun** has a different label per tool but is the same thing:
Claude `bypassPermissions` / `--dangerously-skip-permissions`; Codex `--yolo` /
`danger-full-access`+`never`; Cursor "Run Everything"; Windsurf full "Turbo";
Cline "YOLO Mode"; Aider `--yes-always`. Every provider's own docs name the same
concrete risk it removes the guard against: **a prompt injection hidden in a file
or web page running a destructive or exfiltrating command with no chance to stop
it.** A non-engineer cannot judge command safety mid-stream — so this is never a
default, and the flow should warn about it by name.

---

## Claude Code

Single shared `permissions` model across CLI, IDE extension, and Desktop (same
schema, modes, precedence — surfaces differ only in approval UI + isolation).
Config: `settings.json` (`~/.claude/` user · `.claude/` project · `.local` local;
**deny wins at every level**, rules evaluate `deny → ask → allow`).

**Cautious posture (CLI / IDE / Desktop):**
```json
{
  "permissions": {
    "defaultMode": "default",
    "disableBypassPermissionsMode": "disable",
    "allow": ["Bash(npm run test:*)", "Bash(npm run build)", "Bash(git status)", "Bash(git diff:*)"],
    "ask":   ["Bash(git push:*)", "Bash(git commit:*)", "Edit(package.json)", "WebFetch"],
    "deny":  ["Bash(rm:*)", "Bash(curl:*)", "Bash(wget:*)", "Bash(sudo:*)",
              "Read(./.env)", "Read(./.env.*)", "Read(**/.env)", "Read(~/.ssh/**)", "Read(./secrets/**)"]
  }
}
```
- **Read-only ops already run without prompting in every mode** — no allow rule needed for `ls`/`cat`/`grep`.
- **IDE:** keep manual diff approval (do *not* enable auto-accept-edits by default); enable VS Code Restricted Mode on untrusted folders. IDE-specific risk: auto-edits can rewrite IDE config files the editor then auto-executes.
- **Desktop:** same local settings.json model (OAuth auth). Commit project-level rules.
- **Web (`claude.ai/code`, research preview):** user `~/.claude` settings do **not** apply — only repo-committed `.claude/settings.json` does. Rely on **network = Trusted** (default, not Full), keep **auto-fix PRs off**, review diffs before PR.
- **⛔ Never:** `bypassPermissions` / `--dangerously-skip-permissions`. Lock it with `disableBypassPermissionsMode: "disable"`.

Sources: code.claude.com/docs/en/{permissions,settings,security,claude-code-on-the-web}.
Drift: `auto`/`dontAsk` modes + web surface are research-preview, post-cutoff — verify live.

## Codex

Two independent layers on every surface: **sandbox** (capability) + **approval
policy** (when it asks). Config: `~/.codex/config.toml` (the IDE extension reads
the *same* file).

**Cautious posture (CLI):**
```
codex --sandbox read-only --ask-for-approval on-request
```
```toml
# ~/.codex/config.toml
sandbox_mode    = "read-only"
approval_policy = "on-request"
[sandbox_workspace_write]
network_access = false   # stays off even after moving up to workspace-write
```
- **Sandbox levels:** `read-only` → `workspace-write` (network OFF by default) → `danger-full-access`. **Step up one rung** (`workspace-write` + `on-request`, network off) only when ready to let it edit.
- **IDE:** select **"Chat (Read-Only)"** mode; durable enforcement still lives in `config.toml`. (Exact UI-preset → key mapping is undocumented — drive via `config.toml`, ~85% confidence on the mapping.)
- **Cloud / ChatGPT:** hosted container is always sandboxed; the dominant dial is **internet access — OFF by default**. If needed: **Limited + "Common dependencies" preset + GET/HEAD/OPTIONS only**, never All/Unrestricted.
- **⛔ Never:** `--yolo` / `--dangerously-bypass-approvals-and-sandbox`, or `danger-full-access`+`approval_policy="never"`, or unrestricted cloud internet.

Sources: developers.openai.com/codex/{config-reference,agent-approvals-security,cli/reference,ide/settings,cloud/internet-access}.

## Cursor (desktop IDE, GUI-first)

Config: in-app `Settings → Agents → Run Mode` + `permissions.json`
(`~/.cursor/` and `<workspace>/.cursor/`, which concatenate). Separate
`sandbox.json` for network/fs.

**Cautious posture — set Run Mode = `Allowlist` (NOT Auto-review):** Cursor's own
docs say the Auto-review classifier is "best-effort convenience, **not a security
boundary**" — it can auto-run something a non-engineer wouldn't catch.
```jsonc
// ~/.cursor/permissions.json
{
  "terminalAllowlist": ["git status", "git diff", "git log", "ls", "cat"],
  "mcpAllowlist": ["github:list_*", "github:search_*"],
  "autoRun": {
    "block_instructions": [
      "Block all delete/destructive file operations",
      "Require approval for any database, network, deploy, or push command",
      "Block changes to shell rc files, SSH config, or credentials"
    ]
  }
}
```
- Net: edits reviewed via diff; terminal limited to a read-only allowlist;
  destructive/outward-facing always ask. Add `.cursorignore` to fence sensitive files.
- **Footgun in the file model:** defining a key fully *replaces* the UI allowlist for that type — an empty array means **no allowlist**, not "fall back to UI."
- **⛔ Never:** Run Mode **"Run Everything"** (the old YOLO mode) — any command, no screening, no sandbox.

Sources: cursor.com/docs/{agent/security,agent/tools/terminal,reference/permissions,agent/modes}.
Drift: explicit "auto-apply edits vs ask" setting unconfirmed on the live modes page — verify in-app.

## Other surfaces (pattern-confirmed)

The same review-edits + command-approval + allowlist pattern holds; adding a
provider = adding a profile here.
- **Windsurf** (a.k.a. Devin Desktop): keep **Turbo off**; `windsurf.cascadeCommandsAllowList` + `cascadeCommandsDenyList` (deny beats allow). docs.windsurf.com/windsurf/terminal
- **Cline:** **Auto-Approve off** for execute; safe ops auto-skip. Caveat: safety leans on model judgment (prompt-injectable) — weaker than a static allowlist. Never "YOLO Mode." docs.cline.bot/features/auto-approve
- **Aider:** do **not** pass `--yes-always`; consider `--no-auto-commits`. Binary, no allowlist. aider.chat/docs/config/options.html
