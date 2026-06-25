#!/usr/bin/env python3
"""Claude Code PreToolUse Bash gate hook.

Reads a hook input JSON on stdin, decides allow/defer, emits hookSpecificOutput
on stdout if allowing, always exits 0 (NEVER blocks Bash on internal failure).

Rules come from bash_gate.yaml. JSONL log appended to bash_gate.log.jsonl.

Phase 2b: compound-command splitting on bare &&, ||, ; tokens. Each segment is
dispatched through the class registry independently; the overall command is
allowed only if EVERY segment is independently allow-safe.

Phase 2c: rm-git-tracked-clean handler. Auto-allow `rm <path>` when every
target is under a dev root, tracked by git, and has no uncommitted changes.

Phase 2d: (1) safe-redirect stripping — recognized stderr/stdout discard
redirects (and stdout-to-safe-path redirects) are stripped off each segment
BEFORE class dispatch. (2) inert-verb recognition — compound segments whose
first verb is NOT in the configured ask_verbs list are treated as INERT (a
non-blocker) since settings.json would not have prompted on them standalone.
(3) rm-gitignored-build-artifact handler — auto-allow rm of files that exist,
sit under a dev root, and are matched by `git check-ignore` (build artifacts
are reproducible from source).

Phase 2e: chmod_safe_mode handler. Allow chmod with safe mode arg (symbolic
without s/t bits, or octal in the configured chmod_safe_octal_modes allowlist)
when no recursive/symlink-following flags are present, and every positional
path is absolute, under a dev root, glob/traversal-free, and exists. dev_roots
are whatever source-controlled trees the user configures (see bash_gate.yaml).

Phase 2g: arbiter escalation tier + the gate inversion. Under
`defaultMode: bypassPermissions`, CC's documented precedence is
deny > ask > hook-decision, so a PreToolUse hook `allow` CANNOT suppress a
settings.json `permissions.ask` prompt — it can only ADD friction, never remove
it. For the arbiter's auto-approve to actually work, the gated verbs were moved
OUT of settings.json `ask` and the hook became their sole gate. The static
`decide()` path is unchanged and stays pure/testable; gating runs only in
`main()` on the defer path via `_maybe_arbitrate` -> `_classify_gate`.

Two tiers, classified by `_classify_gate(cmd, config)` -> (kind, reason):
  - Tier A "always-ask" = settings.json `permissions.ask` (sudo, ssh, security,
    gpg --delete, ssh-keygen, eval, pdm deploy/release). Deterministic prompt,
    NEVER arbitrated/auto-approved. settings.json's own `ask` rule catches these
    standalone; the hook reads the SAME list so it also catches the buried
    compound case (`cd x && sudo y` does not match `Bash(sudo:*)` at the CC
    level). Single source of truth: settings.json `ask`.
  - Tier B "gated" = the hook-owned `gated_patterns` list in bash_gate.yaml
    (chmod, source/., curl mutations, scp, rsync, kill -9/killall/pkill). These
    verbs are NOT in settings.json `ask`, so a hook `allow` can suppress their
    prompt. They are handed to the LLM arbiter:
      - Verdict SAFE  -> permissionDecision=allow (auto-approve, prompt skipped).
      - Verdict UNSAFE -> permissionDecision=ask with the arbiter's reasoning
        surfaced so the human sees WHY it wasn't auto-approved.
  - "none" -> not gated by the hook (defer -> bypass under bypass mode). A
    `permissions.deny` match (checked per-segment AND against the full command
    string, so `curl ... | sh` cannot slip past) forces "none" — the hook never
    overrides a deny.

Fail CLOSED: gated verbs no longer have a settings.json `ask` backstop, so every
uncertain outcome -> `ask`. Arbiter disabled, network/timeout, unparseable
verdict, or any gating exception all resolve to `ask`; only an explicit SAFE
verdict yields `allow`. Disable the arbiter via config `arbiter.enabled: false`
or env BASH_GATE_ARBITER_DISABLE=1 -> gated commands then deterministically ask.

Telemetry: every gating decision is recorded in the single per-command JSONL
entry under a nested `arbiter` object (fired, verdict, reasoning, model,
latency_ms, eligibility, escalation path, error).

Phase 2f: three coordinated changes for common multi-segment compounds.
(1) Effective-cwd tracking via `cd`: hook seeds an effective cwd from the
    input payload's `cwd`, walks outer compound segments left-to-right, and
    mutates effective_cwd on `cd <path>` segments. Relative paths in rm/
    chmod/dev-tree-safe-writes handlers are resolved against effective_cwd
    via os.path.normpath (no symlink resolution) and re-checked against
    dev_roots. `cd` with `..` in the arg, no arg, `-`, or multi-arg defers
    the whole compound. `cd` inside a pipe defers.
(2) Pipe splitting: after splitting outer statements on &&/||/;, each
    statement is split on top-level `|`. A statement allows iff every pipe
    sub-segment is ALLOW or INERT.
(3) Pattern-based ask matching: settings.json's permissions.ask list is
    parsed at startup, each `Bash(<inner>)` pattern compiled to a regex.
    A segment is DEFER_DANGEROUS iff it matches one of those regexes AND no
    allow class matched. Fallback to the YAML ask_verbs list if settings.json
    is missing/malformed (degrade to coarse over-defer, safer).
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

HOOK_DIR = Path(__file__).resolve().parent

# User-writable home for config + telemetry. The plugin tree itself is read-only
# and is replaced on `claude plugin update`, so a user's config and the JSONL log
# must live OUTSIDE it. Override the whole location with BASH_GATE_HOME.
USER_DIR = Path(os.environ.get("BASH_GATE_HOME") or os.path.expanduser("~/.config/bash-gate"))


def _resolve_config_path() -> Path:
    """Layered config resolution, first hit wins:
      1. $BASH_GATE_CONFIG          — explicit file override
      2. <USER_DIR>/config.yaml     — the user's own config (survives updates)
      3. <HOOK_DIR>/bash_gate.yaml  — shipped safe defaults (arbiter off, dev_roots [])
    """
    env = os.environ.get("BASH_GATE_CONFIG", "").strip()
    if env:
        return Path(os.path.expanduser(env))
    user_cfg = USER_DIR / "config.yaml"
    if user_cfg.is_file():
        return user_cfg
    return HOOK_DIR / "bash_gate.yaml"


CONFIG_PATH = _resolve_config_path()
# LOG_PATH honors BASH_GATE_TEST_LOG so the test harness (in-process AND
# subprocess invocations) can redirect telemetry to a throwaway file instead of
# polluting the real log.
LOG_PATH = Path(os.environ.get("BASH_GATE_TEST_LOG") or (USER_DIR / "bash_gate.log.jsonl"))

# Substrings that indicate dynamic evaluation we cannot reason about statically.
UNSAFE_SUBSTRINGS = ("$(", "`")
# Heredoc / here-string markers. If any appear in a command containing a newline,
# we cannot safely normalize line-wrap whitespace away — defer as multiline.
HEREDOC_MARKERS = ("<<", "<<-", "<<<")
# Trailing control operators on a logical line that make a following newline an
# AMBIGUOUS continuation rather than a statement boundary. If the line so far
# (rstripped) ends in one of these (or a backslash line-continuation), we defer
# rather than guess where the statement ends.
_TRAILING_CONTROL_OPERATORS = ("&&", "||", "|", "&")
# First-word "evaluators" we unconditionally defer — dynamic evaluation we
# cannot reason about statically. `source`/`.` are handled by the
# source_dotenv_safe class instead, so they are NOT in this set.
EVAL_FIRST_WORDS = {"eval"}
# Tokens that split a compound command into independent segments.
# `&` (async) IS a command separator: `a & b` backgrounds `a` and runs `b`, so
# BOTH sides execute and each must be independently safe. Omitting it let a
# dangerous verb hide after `&` (`echo x & sudo rm -rf /`) — invisible to the
# deny/always-ask/gated checks, which only inspect a segment's leading verb. A
# trailing `&` (`foo &`) leaves an empty final statement -> malformed-compound
# -> defer. `&&`/`&>`/`2>&1` are tokenized as distinct multi-char tokens before
# the single-`&` fallback, so a lone `&` token only ever means async.
SEGMENT_SEPARATORS = {"&&", "||", ";", "&"}
# Verbs that run their ARGUMENT as a fresh command. The classifier only inspects
# a segment's leading verb, so a dangerous inner verb hidden behind one of these
# (`env sudo rm -rf /`, `timeout 5 chmod 777 …`) would slip the always-ask/gated
# check and fall through to INERT in a compound. We DEFER any segment that leads
# with a wrapper rather than try to unwrap it (fail toward asking). sudo/doas are
# intentionally absent — they are Tier-A always-ask and caught when they lead.
EXEC_WRAPPER_VERBS = {
    "env", "command", "exec", "nice", "ionice", "nohup", "setsid",
    "stdbuf", "time", "timeout", "xargs", "watch", "proxychains", "proxychains4",
}
# Pipe / async / non-redirect tokens we will not reason about -> defer.
# Note: redirect tokens are handled separately by strip_safe_redirects.
NON_REDIRECT_PIPE_TOKENS = {"|", "<", "<<", "<<<"}
# Redirect tokens we know how to reason about. Some are inherently safe
# (2>/dev/null, etc.) and embed the target in the same shlex token. Others
# are bare operators whose target is the next token.
SAFE_INLINE_REDIRECTS = {
    "2>/dev/null",
    ">/dev/null",
    "&>/dev/null",
    "2>&1",
    "1>&2",
}
# Bare redirect operators that consume the next token as a target path.
PATH_TARGET_REDIRECT_OPS = {">", ">>", "2>", "2>>", "&>"}
# Safe absolute path prefixes for redirect targets.
SAFE_REDIRECT_PATH_PREFIXES = ("/tmp/", "/private/tmp/", "/var/tmp/")

# rm flag handling for the rm-git-tracked-clean class.
RM_FORBIDDEN_RECURSIVE_FLAGS = {
    "-r", "-R", "--recursive", "-rf", "-fr", "-Rf", "-fR", "-rF", "-Fr",
}
RM_PERMITTED_FLAGS = {"-f", "--force", "-v", "--verbose", "-i"}
GLOB_CHARS = ("*", "?", "[")

# chmod (Phase 2e).
CHMOD_FORBIDDEN_FLAGS = {
    "-R", "-r", "--recursive",
    "-H", "-L", "-P",
}
# Symbolic mode atom: optional who-class chars, op, perm chars. No s/t bits.
_SYMBOLIC_MODE_ATOM = re.compile(r"^[ugoa]*[+\-=][rwxX]+$")
# Octal mode shape (3 or 4 octal digits). Membership in allowlist checked
# separately against config.
_OCTAL_MODE_SHAPE = re.compile(r"^[0-7]{3,4}$")

# A dotenv assignment line: optional leading `export `, then NAME=...
_DOTENV_ASSIGNMENT = re.compile(r"^\s*(export\s+)?[A-Za-z_][A-Za-z0-9_]*=")
# A comment line.
_DOTENV_COMMENT = re.compile(r"^\s*#")
# Command / process-substitution tokens that make even an assignment unsafe.
_DOTENV_UNSAFE_TOKENS = ("$(", "`", "<(", ">(")


def _is_safe_symbolic_mode(mode_str: str) -> bool:
    """Validate a symbolic chmod mode string. Comma-separated atoms allowed.

    Rejects any atom containing 's' or 't' (setuid/setgid/sticky).
    """
    if not mode_str:
        return False
    if "s" in mode_str or "t" in mode_str:
        return False
    atoms = mode_str.split(",")
    if not atoms:
        return False
    for atom in atoms:
        if not _SYMBOLIC_MODE_ATOM.match(atom):
            return False
    return True


# Compound-segment state constants.
SEG_ALLOW = "ALLOW"
SEG_INERT = "INERT"
SEG_DEFER = "DEFER_DANGEROUS"
# Phase 2f: cd is recognized at the outer-statement level as a cwd-mutating
# special segment; it does not match any allow class.
SEG_CWD_MUTATION = "CWD_MUTATION"

# Phase 2f: settings.json path (read-only).
SETTINGS_PATH = Path(os.path.expanduser("~/.claude/settings.json"))

def _compile_bash_patterns(pattern_list: list[str]) -> list[tuple[str, re.Pattern[str]]]:
    """Compile a list of `Bash(...)` permission patterns into anchored regexes.

    Used for both the hook-owned gated-pattern list (YAML) and the settings.json
    deny list. Each input string is expected to be of the form `Bash(<inner>)`.
    The inner
    may contain literal `*` globs (e.g. `find * -delete`) and may end with
    `:*` (= match-anything-tail). The returned regexes are anchored with `^`
    and a tail group `(\\s.*)?$` (allowing additional args after the literal
    pattern body). Non-Bash patterns and malformed entries are skipped.
    """
    compiled: list[tuple[str, re.Pattern[str]]] = []
    for raw in pattern_list or []:
        if not isinstance(raw, str):
            continue
        s = raw.strip()
        if not (s.startswith("Bash(") and s.endswith(")")):
            continue
        inner = s[len("Bash("):-1]
        if not inner:
            continue
        # Detect trailing :* (match-anything tail sentinel).
        trailing_anything = False
        if inner.endswith(":*"):
            trailing_anything = True
            inner = inner[:-2]
        # Escape regex metacharacters EXCEPT `*`, which becomes `.*`.
        # Replace `*` with a placeholder, escape everything, restore `*`->`.*`.
        placeholder = "\x00STAR\x00"
        body = inner.replace("*", placeholder)
        body = re.escape(body)
        body = body.replace(re.escape(placeholder), ".*")
        if trailing_anything:
            # Allow any tail (with or without leading whitespace), OR exact
            # match at end. Use `(?:\s.*)?$` so an exact body also matches.
            pattern = "^" + body + r"(?:\s.*)?$"
        else:
            pattern = "^" + body + r"$"
        try:
            compiled.append((raw, re.compile(pattern)))
        except re.error:
            continue
    return compiled


def _get_gated_patterns(config: dict) -> list[tuple[str, re.Pattern[str]]]:
    """Compile the hook-owned `gated_patterns` list (from bash_gate.yaml).

    Post-inversion the hook OWNS the danger list: these are the `Bash(...)`
    patterns the hook+arbiter gate (the verbs we deliberately moved OUT of
    settings.json `permissions.ask` so a hook decision can actually suppress the
    prompt). Always returns a list (never None) — an empty list means nothing is
    gated. Honors BASH_GATE_GATED_PATTERNS_OVERRIDE (newline-separated
    `Bash(...)` patterns), parsed fresh per call so the test harness can declare
    a per-fixture gated-list instead of coupling to the live config.
    """
    override = os.environ.get("BASH_GATE_GATED_PATTERNS_OVERRIDE")
    if override is not None:
        return _compile_bash_patterns([p for p in override.split("\n") if p.strip()])
    raw = config.get("gated_patterns") if isinstance(config, dict) else None
    if not isinstance(raw, list):
        return []
    return _compile_bash_patterns(raw)


def _get_always_ask_patterns() -> list[tuple[str, re.Pattern[str]]]:
    """Compile the Tier A "always-ask" list = settings.json `permissions.ask`.

    These are the verbs the hook must ALWAYS gate to a prompt and NEVER
    auto-approve (sudo, ssh, security, gpg --delete, ssh-keygen, eval, pdm
    deploy/release). settings.json's `ask` rule gates them when they START a
    command (CC-level, standalone), but it does NOT catch them when buried in a
    compound (`cd x && sudo y` does not match `Bash(sudo:*)`), so the hook reads
    the same list to gate the buried/compound case too. Single source of truth:
    settings.json `permissions.ask`. Honors BASH_GATE_ALWAYS_ASK_PATTERNS_OVERRIDE
    (newline-separated, parsed fresh) so the test harness stays hermetic.
    Always returns a list (empty if settings.json is unreadable).
    """
    override = os.environ.get("BASH_GATE_ALWAYS_ASK_PATTERNS_OVERRIDE")
    if override is not None:
        return _compile_bash_patterns([p for p in override.split("\n") if p.strip()])
    try:
        with SETTINGS_PATH.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return []
    perms = data.get("permissions") if isinstance(data, dict) else None
    ask = perms.get("ask") if isinstance(perms, dict) else None
    if not isinstance(ask, list):
        return []
    return _compile_bash_patterns(ask)


# Module-level cache for compiled deny patterns (settings.json permissions.deny).
# Used ONLY by the Phase 2g arbiter eligibility gate to ensure the arbiter never
# auto-allows a command a deny rule targets. None if load failed.
_DENY_PATTERN_CACHE: list[tuple[str, re.Pattern[str]]] | None = None
_DENY_PATTERN_LOADED: bool = False


def _load_deny_patterns() -> list[tuple[str, re.Pattern[str]]] | None:
    """Load and compile deny patterns from settings.json. Returns None on failure.

    Honors BASH_GATE_DENY_PATTERNS_OVERRIDE (newline-separated `Bash(...)`
    strings, parsed fresh) so the test harness stays hermetic — when set it is
    used INSTEAD of reading settings.json (empty string => no deny patterns).
    """
    override = os.environ.get("BASH_GATE_DENY_PATTERNS_OVERRIDE")
    if override is not None:
        return _compile_bash_patterns([p for p in override.split("\n") if p.strip()])
    try:
        with SETTINGS_PATH.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return None
    perms = data.get("permissions") if isinstance(data, dict) else None
    deny = perms.get("deny") if isinstance(perms, dict) else None
    if not isinstance(deny, list):
        return None
    return _compile_bash_patterns(deny)


def _get_deny_patterns() -> list[tuple[str, re.Pattern[str]]] | None:
    """Cached accessor for compiled deny patterns. None if load failed/absent."""
    global _DENY_PATTERN_CACHE, _DENY_PATTERN_LOADED
    if _DENY_PATTERN_LOADED:
        return _DENY_PATTERN_CACHE
    _DENY_PATTERN_CACHE = _load_deny_patterns()
    _DENY_PATTERN_LOADED = True
    return _DENY_PATTERN_CACHE


def _matches_any_deny_pattern(
    tokens: list[str],
    patterns: list[tuple[str, re.Pattern[str]]],
) -> tuple[bool, str]:
    """Test a token list's command string against compiled deny patterns.

    Mirrors _matches_any_pattern but is applied both per-segment AND against
    the full command token list (so pipe-spanning deny rules like
    `curl * | sh` are caught even though segment splitting would break the pipe).
    """
    cmd_str = _segment_command_string(tokens)
    if not cmd_str:
        return (False, "")
    for raw, regex in patterns:
        if regex.match(cmd_str):
            return (True, raw)
    return (False, "")


def _segment_command_string(tokens: list[str]) -> str:
    """Join a segment's tokens into a single command string for ask-pattern matching.

    Tokens here are post-shlex (quote stripped) — we just space-join them.
    Leading env-var assignments are stripped (mirrors _first_verb_after_env).
    """
    _verb, effective = _first_verb_after_env(tokens)
    return " ".join(effective)


def _matches_any_pattern(
    tokens: list[str],
    patterns: list[tuple[str, re.Pattern[str]]],
) -> tuple[bool, str]:
    """Test the segment's command string against compiled ask patterns."""
    cmd_str = _segment_command_string(tokens)
    if not cmd_str:
        return (False, "")
    for raw, regex in patterns:
        if regex.match(cmd_str):
            return (True, raw)
    return (False, "")


# Phase 2f: cd handling.
def _parse_cd_segment(tokens: list[str]) -> tuple[str, str | None, str]:
    """Inspect a segment that begins with `cd`. Returns (kind, new_cwd_arg, reason).

    kind:
      - "not-cd": not a cd segment
      - "cd-valid": valid `cd <one-path>` (arg returned, no `..`, no `-`)
      - "cd-defer": malformed / unsafe cd (defer entire compound)
    new_cwd_arg is the raw arg (still needing tilde-expansion + join).
    """
    if not tokens or tokens[0] != "cd":
        return ("not-cd", None, "")
    rest = tokens[1:]
    if len(rest) == 0:
        return ("cd-defer", None, "cd-no-arg")
    if len(rest) > 1:
        return ("cd-defer", None, "cd-multi-arg")
    arg = rest[0]
    if arg == "-":
        return ("cd-defer", None, "cd-dash")
    if ".." in arg.split("/"):
        return ("cd-defer", None, "cd-traversal")
    return ("cd-valid", arg, "")


def _resolve_cd(current_cwd: str, raw_arg: str) -> str:
    """Apply a `cd <raw_arg>` against current_cwd. Returns the new effective cwd."""
    expanded = _expand_user(raw_arg)
    if expanded.startswith("/"):
        return os.path.normpath(expanded)
    # Relative cd. Join with current_cwd (which is already absolute/normalized
    # or empty). Empty current_cwd + relative cd is impossible because the
    # caller defers when current_cwd is empty.
    joined = os.path.join(current_cwd, expanded)
    return os.path.normpath(joined)


def _resolve_path_against_cwd(raw_path: str, effective_cwd: str) -> str | None:
    """Resolve a possibly-relative path against effective_cwd.

    Returns the normalized absolute path, or None if it can't be resolved
    (relative path with no effective_cwd).
    """
    expanded = _expand_user(raw_path)
    if expanded.startswith("/"):
        return os.path.normpath(expanded)
    if not effective_cwd:
        return None
    return os.path.normpath(os.path.join(effective_cwd, expanded))


def _normalize_operators(cmd: str) -> str:
    """Insert spaces around bare shell operators so shlex tokenizes them cleanly.

    Quote-aware: skips characters inside single or double quotes. Handles
    multi-char operators (&&, ||, >>, 2>, 2>>, &>, 2>&1, 1>&2) by recognizing
    them as units before single-char fallbacks.

    Backslash escapes the next character. This is a pragmatic preprocessor —
    it does not attempt full POSIX parsing. Output is fed straight to shlex,
    which does the actual tokenization.
    """
    out: list[str] = []
    i = 0
    n = len(cmd)
    in_single = False
    in_double = False

    def emit_op(op: str) -> None:
        if out and not out[-1].isspace():
            out.append(" ")
        out.append(op)
        out.append(" ")

    while i < n:
        c = cmd[i]

        if in_single:
            out.append(c)
            if c == "'":
                in_single = False
            i += 1
            continue
        if in_double:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(cmd[i + 1])
                i += 2
                continue
            if c == '"':
                in_double = False
            i += 1
            continue

        if c == "\\" and i + 1 < n:
            out.append(c)
            out.append(cmd[i + 1])
            i += 2
            continue
        if c == "'":
            in_single = True
            out.append(c)
            i += 1
            continue
        if c == '"':
            in_double = True
            out.append(c)
            i += 1
            continue

        # Multi-char operators (try longest first).
        # 2>&1, 1>&2
        if cmd[i:i + 4] in ("2>&1", "1>&2"):
            emit_op(cmd[i:i + 4])
            i += 4
            continue
        # 2>>, &>
        if cmd[i:i + 3] == "2>>":
            emit_op("2>>")
            i += 3
            continue
        # 2>, &>, &&, ||, >>, <<
        two = cmd[i:i + 2]
        if two in ("2>", "&>", "&&", "||", ">>", "<<"):
            emit_op(two)
            i += 2
            continue
        # Single-char: ;, |, &, >, <
        if c in (";", "|", "&", ">", "<"):
            emit_op(c)
            i += 1
            continue

        out.append(c)
        i += 1

    return "".join(out)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _log(entry: dict) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _emit_allow(reason: str) -> None:
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": reason,
        }
    }
    sys.stdout.write(json.dumps(out))
    sys.stdout.flush()


def _emit_ask(reason: str) -> None:
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }
    sys.stdout.write(json.dumps(out))
    sys.stdout.flush()


def _load_config() -> dict | None:
    try:
        import yaml  # type: ignore
    except ImportError:
        return None
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except Exception:
        return None


def _expand_user(path: str) -> str:
    return os.path.expanduser(path)


def _resolved_dev_roots(config: dict) -> list[str]:
    override = os.environ.get("BASH_GATE_DEV_ROOTS_OVERRIDE", "").strip()
    if override:
        raw_roots = [r for r in override.split(":") if r]
    else:
        raw_roots = [r for r in (config.get("dev_roots") or []) if isinstance(r, str) and r]

    roots: list[str] = []
    for r in raw_roots:
        expanded = os.path.normpath(_expand_user(r))
        if not expanded.endswith("/"):
            expanded += "/"
        roots.append(expanded)
    return roots


def _path_under_dev_root(path: str, dev_roots: list[str]) -> bool:
    normalized = os.path.normpath(path)
    candidate = normalized + "/"
    return any(candidate.startswith(root) for root in dev_roots)


def _is_safe_redirect_path(path: str, dev_roots: list[str]) -> bool:
    """Is this an absolute path safe to redirect output into?"""
    if not path.startswith("/"):
        return False
    normalized = os.path.normpath(path)
    # Compare with trailing-slash boundary semantics.
    test = normalized + "/"
    for prefix in SAFE_REDIRECT_PATH_PREFIXES:
        if test.startswith(prefix):
            return True
    if _path_under_dev_root(normalized, dev_roots):
        return True
    return False


def strip_safe_redirects(
    tokens: list[str], dev_roots: list[str]
) -> tuple[list[str] | None, str]:
    """Strip recognized safe redirect tokens off `tokens`.

    Returns (residual_tokens, "") on success. On unsafe redirect, returns
    (None, "unsafe-redirect(<token-or-path>)"). Unknown redirect-shaped tokens
    that we can't classify also yield None.

    Safe redirects (always stripped):
      - 2>/dev/null, >/dev/null, &>/dev/null, 2>&1, 1>&2 (inline single tokens)

    Path-conditional (stripped when target is under /tmp/, /private/tmp/,
    /var/tmp/, or any dev root):
      - >/path, >>/path, 2>/path, 2>>/path, &>/path  (path inline in token)
      - >  /path, >> /path, 2> /path, 2>> /path, &> /path  (bare op + next tok)

    Pipes / heredocs / input redirects are NOT handled here — caller still
    sees them in residual tokens and defers via the existing pipe-or-redirect
    path.
    """
    residual: list[str] = []
    i = 0
    n = len(tokens)
    while i < n:
        t = tokens[i]

        if t in SAFE_INLINE_REDIRECTS:
            i += 1
            continue

        # Inline path-conditional: token starts with a redirect op and has
        # path inline (e.g. ">/tmp/log", "2>>/tmp/err").
        consumed = False
        for op in sorted(PATH_TARGET_REDIRECT_OPS | {"2>>"}, key=len, reverse=True):
            if t == op:
                continue  # bare op handled below
            if t.startswith(op):
                path = t[len(op):]
                if path in ("/dev/null",):
                    # Already covered by SAFE_INLINE_REDIRECTS for most forms,
                    # but `2>>/dev/null` etc. land here.
                    i += 1
                    consumed = True
                    break
                if _is_safe_redirect_path(path, dev_roots):
                    i += 1
                    consumed = True
                    break
                return (None, f"unsafe-redirect({t})")
        if consumed:
            continue

        # Bare redirect operator: consume next token as path.
        if t in PATH_TARGET_REDIRECT_OPS or t == "2>>":
            if i + 1 >= n:
                return (None, f"unsafe-redirect({t}-no-target)")
            target = tokens[i + 1]
            if target == "/dev/null":
                i += 2
                continue
            if _is_safe_redirect_path(target, dev_roots):
                i += 2
                continue
            return (None, f"unsafe-redirect({t} {target})")

        residual.append(t)
        i += 1

    return (residual, "")


def _classify_dev_tree_safe_writes(
    tokens: list[str], rule: dict, config: dict, effective_cwd: str = ""
) -> tuple[str, str]:
    dev_roots = _resolved_dev_roots(config)
    if not dev_roots:
        return ("defer", "no-dev-roots-configured")

    positional: list[str] = []
    for w in tokens[1:]:
        if w.startswith("-"):
            # cp/mv/ln -t/--target-directory carries a DESTINATION path. Only
            # positionals are containment-checked below, so a smuggled target
            # (`cp --target-directory=/etc/cron.d ~/dev/work/x`) would escape the
            # dev-root check. Reject the flag rather than silently skip it.
            if (
                w in ("-t", "--target-directory")
                or w.startswith("--target-directory=")
                or (w.startswith("-t") and len(w) > 2)
            ):
                return ("defer", f"target-directory-flag({w})")
            continue
        positional.append(w)

    if not positional:
        return ("defer", "no-positional-paths")

    resolved_any_relative = False
    for w in positional:
        if ".." in w.split("/"):
            return ("defer", f"path-traversal(word={w})")
        resolved = _resolve_path_against_cwd(w, effective_cwd)
        if resolved is None:
            return ("defer", f"relative-path-out-of-scope(word={w})")
        if resolved != os.path.normpath(_expand_user(w)) or not _expand_user(w).startswith("/"):
            resolved_any_relative = True
        if not _path_under_dev_root(resolved, dev_roots):
            return ("defer", f"path-outside-dev-roots(word={w})")

    reason = rule.get("allow_reason", "allowed")
    if resolved_any_relative and effective_cwd:
        reason = f"{reason} (resolved relative paths against cwd {effective_cwd})"
    return ("allow", reason)


def _classify_rm(tokens: list[str], rule: dict, effective_cwd: str = "") -> tuple[str, str]:
    allow_when = rule.get("allow_when", {}) or {}
    prefixes = [
        p["prefix"]
        for p in allow_when.get("all_positional_args_match", []) or []
        if isinstance(p, dict) and "prefix" in p
    ]
    no_traversal = allow_when.get("no_path_traversal", True)

    found_path = False
    resolved_relative = False
    for w in tokens[1:]:
        if no_traversal and ".." in w:
            return ("defer", f"path-traversal(word={w})")
        if w.startswith("-"):
            continue
        # Resolve possibly-relative paths against effective_cwd for the
        # prefix check.
        check_path = w
        if not _expand_user(w).startswith("/"):
            resolved = _resolve_path_against_cwd(w, effective_cwd)
            if resolved is None:
                return ("defer", f"non-tmp-target(word={w})")
            check_path = resolved
            resolved_relative = True
        if any(check_path.startswith(p) and len(check_path) > len(p) for p in prefixes):
            found_path = True
            continue
        return ("defer", f"non-tmp-target(word={w})")

    if not found_path:
        return ("defer", "no-path-found")
    reason = rule.get("allow_reason", "allowed")
    if resolved_relative and effective_cwd:
        reason = f"{reason} (resolved relative paths against cwd {effective_cwd})"
    return ("allow", reason)


def _git_check(repo_dir: str, args: list[str]) -> tuple[bool, str]:
    """Run a git subcommand. Return (success, error_string)."""
    try:
        proc = subprocess.run(
            ["git", "-C", repo_dir] + args,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return (False, "git-timeout")
    except FileNotFoundError:
        return (False, "git-missing")
    except Exception as e:
        return (False, f"git-error({type(e).__name__})")
    if proc.returncode != 0:
        return (False, f"git-rc={proc.returncode}")
    return (True, "")


def _rm_precheck(
    tokens: list[str], config: dict, effective_cwd: str = ""
) -> tuple[list[tuple[str, str]] | None, str]:
    """Shared cheap pre-checks for rm-* handlers.

    Returns (list of (original_word, resolved_abs_path), "") on success, or
    (None, reason) on defer. Resolved path is what git/fs checks should use;
    original word is for log/reason strings.
    """
    if not tokens or tokens[0] != "rm":
        return (None, "not-rm")

    positional: list[str] = []
    for w in tokens[1:]:
        if w.startswith("-"):
            if w in RM_FORBIDDEN_RECURSIVE_FLAGS:
                return (None, f"recursive-flag-rejected({w})")
            if w not in RM_PERMITTED_FLAGS:
                return (None, f"unrecognized-rm-flag({w})")
            continue
        positional.append(w)

    if not positional:
        return (None, "no-positional-paths")

    dev_roots = _resolved_dev_roots(config)
    if not dev_roots:
        return (None, "no-dev-roots-configured")

    resolved: list[tuple[str, str]] = []
    for w in positional:
        if ".." in w.split("/"):
            return (None, f"path-traversal(word={w})")
        if any(g in w for g in GLOB_CHARS):
            return (None, f"glob-rejected(word={w})")
        abs_path = _resolve_path_against_cwd(w, effective_cwd)
        if abs_path is None:
            return (None, f"relative-path-out-of-scope(word={w})")
        if not _path_under_dev_root(abs_path, dev_roots):
            return (None, f"path-outside-dev-roots(word={w})")
        if not os.path.isfile(abs_path):
            return (None, f"not-a-regular-file(word={w})")
        if os.path.islink(abs_path):
            return (None, f"symlink-rejected(word={w})")
        resolved.append((w, abs_path))

    return (resolved, "")


def _classify_rm_git_tracked_clean(
    tokens: list[str], rule: dict, config: dict, effective_cwd: str = ""
) -> tuple[str, str]:
    """Allow rm of files that are dev-root-resident, git-tracked, and clean."""
    positional, err = _rm_precheck(tokens, config, effective_cwd)
    if positional is None:
        return ("defer", err)

    resolved_relative = False
    for w, abs_path in positional:
        if not _expand_user(w).startswith("/"):
            resolved_relative = True
        repo_dir = os.path.dirname(abs_path)
        basename = os.path.basename(abs_path)

        ok, err = _git_check(repo_dir, ["ls-files", "--error-unmatch", "--", basename])
        if not ok:
            return ("defer", f"git-untracked-or-error(word={w},{err})")

        ok, err = _git_check(repo_dir, ["diff", "--quiet", "HEAD", "--", basename])
        if not ok:
            return ("defer", f"git-dirty-vs-head(word={w},{err})")

        ok, err = _git_check(repo_dir, ["diff", "--cached", "--quiet", "--", basename])
        if not ok:
            return ("defer", f"git-staged-changes(word={w},{err})")

    reason = rule.get("allow_reason", "rm targets are git-tracked and clean")
    if resolved_relative and effective_cwd:
        reason = f"{reason} (resolved relative paths against cwd {effective_cwd})"
    return ("allow", reason)


def _classify_rm_gitignored_build_artifact(
    tokens: list[str], rule: dict, config: dict, effective_cwd: str = ""
) -> tuple[str, str]:
    """Allow rm of files under a dev root that git considers ignored (build artifacts)."""
    positional, err = _rm_precheck(tokens, config, effective_cwd)
    if positional is None:
        return ("defer", err)

    resolved_relative = False
    for w, abs_path in positional:
        if not _expand_user(w).startswith("/"):
            resolved_relative = True
        repo_dir = os.path.dirname(abs_path)
        basename = os.path.basename(abs_path)

        # `git check-ignore -q <path>` exits 0 if path matches a gitignore rule,
        # 1 if not, 128 on error (not a repo, etc.).
        ok, err_str = _git_check(repo_dir, ["check-ignore", "-q", "--", basename])
        if not ok:
            return ("defer", f"not-gitignored-or-error(word={w},{err_str})")

    reason = rule.get("allow_reason", "rm targets are gitignored build artifacts")
    if resolved_relative and effective_cwd:
        reason = f"{reason} (resolved relative paths against cwd {effective_cwd})"
    return ("allow", reason)


def _classify_chmod_safe_mode(
    tokens: list[str], rule: dict, config: dict, effective_cwd: str = ""
) -> tuple[str, str]:
    """Allow chmod <safe-mode> <path>... when paths are dev-root-resident and exist."""
    if not tokens or tokens[0] != "chmod":
        return ("defer", "not-chmod")

    octal_allowlist = {
        m for m in (config.get("chmod_safe_octal_modes") or [])
        if isinstance(m, str)
    }

    # Walk flags, find mode arg (first non-flag OR leading symbolic-mode-shaped
    # arg starting with '-'), then positionals.
    mode_arg: str | None = None
    positional: list[str] = []
    for w in tokens[1:]:
        if w.startswith("-") and mode_arg is None:
            if w in CHMOD_FORBIDDEN_FLAGS:
                return ("defer", f"chmod-forbidden-flag({w})")
            # A leading `-`-prefixed token that parses as a safe symbolic mode
            # (e.g. `-x`, `-rwx`) is the mode arg, not a flag.
            if _is_safe_symbolic_mode(w):
                mode_arg = w
                continue
            return ("defer", f"chmod-unknown-flag({w})")
        if w.startswith("-") and mode_arg is not None:
            return ("defer", f"chmod-flag-after-mode({w})")
        if mode_arg is None:
            mode_arg = w
            continue
        positional.append(w)

    if mode_arg is None:
        return ("defer", "chmod-no-mode-arg")
    if not positional:
        return ("defer", "chmod-no-positional-paths")

    # Validate mode arg.
    if _OCTAL_MODE_SHAPE.match(mode_arg):
        if mode_arg not in octal_allowlist:
            return ("defer", f"chmod-octal-not-in-allowlist({mode_arg})")
    elif _is_safe_symbolic_mode(mode_arg):
        pass
    else:
        return ("defer", f"chmod-unsafe-or-malformed-mode({mode_arg})")

    dev_roots = _resolved_dev_roots(config)
    if not dev_roots:
        return ("defer", "no-dev-roots-configured")

    resolved_relative = False
    for w in positional:
        if ".." in w.split("/"):
            return ("defer", f"path-traversal(word={w})")
        if any(g in w for g in GLOB_CHARS):
            return ("defer", f"glob-rejected(word={w})")
        abs_path = _resolve_path_against_cwd(w, effective_cwd)
        if abs_path is None:
            return ("defer", f"relative-path-out-of-scope(word={w})")
        if not _expand_user(w).startswith("/"):
            resolved_relative = True
        if not _path_under_dev_root(abs_path, dev_roots):
            return ("defer", f"path-outside-dev-roots(word={w})")
        # chmod follows symlinks, so a dev-root symlink pointing outside the root
        # would have its TARGET's mode changed under an auto-allow. Reject links
        # (mirrors the rm handlers' islink guard).
        if os.path.islink(abs_path):
            return ("defer", f"symlink-rejected(word={w})")
        if not os.path.exists(abs_path):
            return ("defer", f"path-does-not-exist(word={w})")

    reason = rule.get("allow_reason", "chmod with safe mode on dev-root path(s)")
    if resolved_relative and effective_cwd:
        reason = f"{reason} (resolved relative paths against cwd {effective_cwd})"
    return ("allow", reason)


def _classify_source_dotenv_safe(
    effective_tokens: list[str], rule: dict, config: dict, effective_cwd: str = ""
) -> tuple[str, str]:
    """Allow `source <file>` / `. <file>` when the file is dotenv-safe under a dev root.

    Predicate (ALL must hold):
      - Exactly ONE positional arg after the verb. Zero args, multiple args,
        any flag/option token, and `-` (stdin) defer.
      - The arg resolves (via effective_cwd) and is NOT a symlink.
      - One of two safe cases holds, each still gated on dev-root containment:
        - MISSING-FILE NO-OP: the resolved path does not exist on disk. Sourcing
          a nonexistent file is a guaranteed no-op — the shell writes "no such
          file" to stderr and continues; zero bytes are read or executed. This is
          the `source .env 2>/dev/null` optional-dotenv idiom. We still require
          the resolved path be under a configured dev root (containment is not
          weakened just because the file is absent); `_path_under_dev_root` is a
          pure string comparison on the resolved path, so it is correct for a
          path that does not exist on disk.
        - REGULAR DOTENV FILE: the path is an existing regular file (devices,
          directories, etc. defer) under a configured dev root, and every line is
          blank/whitespace-only, a comment (`^\\s*#`), or a dotenv assignment
          (`^\\s*(export\\s+)?NAME=`). An assignment line is STILL rejected if it
          contains any command/process-substitution token (`$(`, a backtick,
          `<(`, `>(`). Any other line defers.

    Any file-IO error degrades to defer (never raises).
    """
    args = effective_tokens[1:]
    file_args: list[str] = []
    for w in args:
        if w == "-" or w.startswith("-"):
            return ("defer", f"source-flag-or-stdin-rejected(word={w})")
        file_args.append(w)
    if len(file_args) != 1:
        return ("defer", "source-requires-single-file-arg")

    arg = file_args[0]
    resolved = _resolve_path_against_cwd(arg, effective_cwd)
    if resolved is None:
        return ("defer", f"relative-path-out-of-scope(word={arg})")

    if os.path.islink(resolved):
        return ("defer", f"source-symlink-rejected(word={arg})")

    if not os.path.exists(resolved):
        dev_roots = _resolved_dev_roots(config)
        if not dev_roots:
            return ("defer", "no-dev-roots-configured")
        if not _path_under_dev_root(resolved, dev_roots):
            return ("defer", f"path-outside-dev-roots(word={arg})")
        return (
            "allow",
            rule.get("allow_reason", "source-dotenv-safe") + " (missing-file-noop)",
        )

    if not os.path.isfile(resolved):
        return ("defer", f"source-not-a-regular-file(word={arg})")

    dev_roots = _resolved_dev_roots(config)
    if not dev_roots:
        return ("defer", "no-dev-roots-configured")
    if not _path_under_dev_root(resolved, dev_roots):
        return ("defer", f"path-outside-dev-roots(word={arg})")

    try:
        with open(resolved, encoding="utf-8", errors="strict") as fh:
            for line in fh:
                stripped = line.rstrip("\n")
                if not stripped.strip():
                    continue
                if _DOTENV_COMMENT.match(stripped):
                    continue
                if _DOTENV_ASSIGNMENT.match(stripped):
                    if any(tok in stripped for tok in _DOTENV_UNSAFE_TOKENS):
                        return ("defer", f"source-dotenv-unsafe-line(line={stripped.strip()!r})")
                    continue
                return ("defer", f"source-dotenv-unsafe-line(line={stripped.strip()!r})")
    except Exception as e:
        return ("defer", f"source-read-error({type(e).__name__})")

    return ("allow", rule.get("allow_reason", "source-dotenv-safe"))


def _first_verb_after_env(tokens: list[str]) -> tuple[str, list[str]]:
    """Skip leading VAR=value env assignments. Return (verb, remaining-tokens)."""
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if "=" in t:
            head = t.split("=", 1)[0]
            if head and (head[0].isalpha() or head[0] == "_") and all(
                c.isalnum() or c == "_" for c in head
            ):
                i += 1
                continue
        break
    if i >= len(tokens):
        return ("", [])
    return (tokens[i], tokens[i:])


def _dispatch_single(
    tokens: list[str], config: dict, effective_cwd: str = ""
) -> tuple[str, str, str]:
    """Dispatch a single (non-compound) tokenized command through the class registry.

    Returns (decision, reason, log_class). decision in {'allow','defer'}.
    """
    if not tokens:
        return ("defer", "no-tokens", "")

    # Strip leading env-var assignments for verb identification, but pass the
    # stripped tail to handlers so e.g. `MIX_ENV=test mix compile` is handled
    # as `mix compile`.
    first, effective_tokens = _first_verb_after_env(tokens)
    if not first:
        return ("defer", "no-verb-after-env", "")
    if first in EVAL_FIRST_WORDS:
        return ("defer", f"eval-first-word({first})", "")

    first_defer: tuple[str, str, str] | None = None
    matched_any = False
    for rule in config.get("classes", []) or []:
        match_one = rule.get("match_first_word")
        match_many = rule.get("match_first_word_one_of") or []
        if match_one != first and first not in match_many:
            continue
        matched_any = True
        log_class = rule.get("log_as", first)
        handler = rule.get("handler") or ("rm_prefix" if first == "rm" else None)
        if handler == "rm_prefix":
            decision, reason = _classify_rm(effective_tokens, rule, effective_cwd)
        elif handler == "dev_tree_safe_writes":
            decision, reason = _classify_dev_tree_safe_writes(
                effective_tokens, rule, config, effective_cwd
            )
        elif handler == "rm_git_tracked_clean":
            decision, reason = _classify_rm_git_tracked_clean(
                effective_tokens, rule, config, effective_cwd
            )
        elif handler == "rm_gitignored_build_artifact":
            decision, reason = _classify_rm_gitignored_build_artifact(
                effective_tokens, rule, config, effective_cwd
            )
        elif handler == "chmod_safe_mode":
            decision, reason = _classify_chmod_safe_mode(
                effective_tokens, rule, config, effective_cwd
            )
        elif handler == "source_dotenv_safe":
            decision, reason = _classify_source_dotenv_safe(
                effective_tokens, rule, config, effective_cwd
            )
        else:
            decision, reason = ("defer", f"class-not-implemented(handler={handler})")

        if decision == "allow":
            return ("allow", reason, log_class)
        if first_defer is None:
            first_defer = ("defer", reason, log_class)

    if not matched_any:
        return ("defer", f"no-class-match(first={first})", "")
    # matched_any ⇒ a class matched and (no allow returned) first_defer was set.
    # Guard explicitly rather than assert, which `python3 -O` strips.
    if first_defer is None:
        return ("defer", "no-allow-class-matched", "")
    return first_defer


def _classify_segment(
    tokens: list[str], config: dict, effective_cwd: str = ""
) -> tuple[str, str, str]:
    """Classify a compound segment into one of SEG_ALLOW / SEG_INERT / SEG_DEFER.

    A segment is DEFER_DANGEROUS iff it matches a Tier A always-ask pattern
    (settings.json ask) OR a Tier B gated_pattern (bash_gate.yaml) and no allow
    class rescued it; otherwise INERT (it would bypass standalone, so it does not
    block the compound). Catching always-ask patterns here is what stops a buried
    `... && sudo y` from escaping the gate.

    Returns (state, reason, log_class).
    """
    if not tokens:
        return (SEG_DEFER, "empty-segment", "")

    decision, reason, log_class = _dispatch_single(tokens, config, effective_cwd)
    if decision == "allow":
        return (SEG_ALLOW, reason, log_class)

    verb, _ = _first_verb_after_env(tokens)

    # An exec-wrapper would hide the real verb from the pattern checks below
    # (which only see the segment's leading token). Defer rather than INERT.
    if verb in EXEC_WRAPPER_VERBS:
        return (SEG_DEFER, f"exec-wrapper({verb})", verb)

    matched, raw_pat = _matches_any_pattern(tokens, _get_always_ask_patterns())
    if matched:
        return (SEG_DEFER, f"{reason}|always-ask={raw_pat}", log_class)
    matched, raw_pat = _matches_any_pattern(tokens, _get_gated_patterns(config))
    if matched:
        return (SEG_DEFER, f"{reason}|gated-pattern={raw_pat}", log_class)
    return (SEG_INERT, f"inert({verb})", f"inert({verb})")


def _split_outer_statements(tokens: list[str]) -> tuple[list[list[str]] | None, str]:
    """Split tokens on bare &&/||/; into independent outer statements.

    Pipes are NOT split here — they're handled by _split_pipe_subsegments
    per-statement. Input redirects / heredocs in tokens defer the compound.
    Output redirects are stripped before this runs.
    """
    statements: list[list[str]] = []
    current: list[str] = []
    for t in tokens:
        if t in ("<", "<<", "<<<"):
            return (None, f"pipe-or-redirect({t})")
        if t in SEGMENT_SEPARATORS:
            if not current:
                return (None, "malformed-compound")
            statements.append(current)
            current = []
        else:
            current.append(t)
    if not current:
        return (None, "malformed-compound")
    statements.append(current)
    return (statements, "")


def _split_pipe_subsegments(tokens: list[str]) -> tuple[list[list[str]] | None, str]:
    """Split a single statement's tokens on top-level `|` into pipe sub-segments."""
    subs: list[list[str]] = []
    current: list[str] = []
    for t in tokens:
        if t == "|":
            if not current:
                return (None, "malformed-pipe")
            subs.append(current)
            current = []
        else:
            current.append(t)
    if not current:
        return (None, "malformed-pipe")
    subs.append(current)
    return (subs, "")


def _evaluate_statement(
    statement_tokens: list[str],
    config: dict,
    dev_roots: list[str],
    effective_cwd: str,
) -> tuple[str, str, str]:
    """Evaluate a single statement (one element of an &&/||/; split).

    Handles pipe sub-segment splitting, redirect stripping per sub-segment,
    cd-mutation recognition (only at the outer level, NOT inside pipes), and
    classification.

    Returns (state, summary, log_class). state is one of:
      - SEG_ALLOW  : whole statement OK
      - SEG_INERT  : whole statement OK (no allow class needed)
      - SEG_DEFER  : statement defers (reason in summary)
      - SEG_CWD_MUTATION : statement is a `cd <path>`; caller mutates cwd.
                           In this state the summary holds the new cwd.

    Note: SEG_CWD_MUTATION only ever applies to a single-token-flow (no
    pipes); a cd inside a pipe returns SEG_DEFER.
    """
    pipe_subs, pipe_err = _split_pipe_subsegments(statement_tokens)
    if pipe_subs is None:
        return (SEG_DEFER, pipe_err, "")

    if len(pipe_subs) == 1:
        sub = pipe_subs[0]
        # Strip safe redirects.
        residual, redirect_err = strip_safe_redirects(sub, dev_roots)
        if residual is None:
            return (SEG_DEFER, f"unsafe-redirect({redirect_err})", "")
        if not residual:
            return (SEG_DEFER, "empty-segment-after-redirect-strip", "")
        # cd recognition.
        cd_kind, cd_arg, cd_reason = _parse_cd_segment(residual)
        if cd_kind == "cd-defer":
            return (SEG_DEFER, cd_reason, "cd")
        if cd_kind == "cd-valid":
            new_cwd = _resolve_cd(effective_cwd, cd_arg or "")
            return (SEG_CWD_MUTATION, new_cwd, "cd")
        # Normal classify.
        state, reason, log_class = _classify_segment(residual, config, effective_cwd)
        return (state, reason, log_class)

    # Pipe-multi: classify each sub-segment. cd inside pipe defers.
    sub_summaries: list[str] = []
    for sub in pipe_subs:
        residual, redirect_err = strip_safe_redirects(sub, dev_roots)
        if residual is None:
            return (SEG_DEFER, f"unsafe-redirect({redirect_err})", "pipe")
        if not residual:
            return (SEG_DEFER, "empty-pipe-sub-after-redirect-strip", "pipe")
        cd_kind, _cd_arg, _cd_reason = _parse_cd_segment(residual)
        if cd_kind != "not-cd":
            return (SEG_DEFER, "cd-inside-pipe", "pipe")
        state, reason, log_class = _classify_segment(residual, config, effective_cwd)
        if state == SEG_DEFER:
            first_tok = residual[0] if residual else ""
            return (
                SEG_DEFER,
                f"pipe-sub(first={first_tok},reason={reason})",
                "pipe",
            )
        sub_summaries.append(log_class or ("inert" if state == SEG_INERT else "?"))
    # If any sub-segment is ALLOW, the whole pipe is ALLOW; else INERT.
    return (SEG_ALLOW, f"pipe[{', '.join(sub_summaries)}]", "pipe")


def _normalize_line_wraps(cmd: str) -> tuple[str | None, str]:
    """Normalize line-wrap and statement-terminating newlines for parsing.

    The result feeds only the allow/defer DECISION — bash still executes the
    original, unmodified command — so a mis-normalization may at worst force a
    DEFER, never a dangerous allow.

    Predicate: if `cmd` contains no `\\n`, return it unchanged. If any
    heredoc/here-string marker (`<<`, `<<-`, `<<<`) is present, return
    (None, "multiline") — the caller defers (we cannot safely reason about
    here-doc bodies). Otherwise scan left-to-right and classify each `\\n`
    against the logical line accumulated so far (the rstripped output emitted
    up to that point):

      1. `\\n` + horizontal whitespace [ \\t], OR a trailing `\\n` (end of
         string) -> terminal SOFT-WRAP continuation: drop the newline and any
         following horizontal-whitespace run (collapse to "").
      2. `\\n` + non-whitespace, where the logical line so far ends in a
         trailing control operator (`&&`, `||`, `|`, `&`) OR a backslash
         line-continuation (`\\`) -> AMBIGUOUS continuation: return
         (None, "multiline") (conservative defer; no regression).
      3. `\\n` + non-whitespace, where the logical line so far ends in `;`
         -> already separated: drop the newline, inject nothing.
      4. `\\n` + non-whitespace otherwise -> real STATEMENT BOUNDARY: inject
         " ; " so the downstream shlex.split + _split_outer_statements treat
         it as an outer separator.

    Because `;` is injected into the raw pre-shlex string, a boundary `;` that
    lands inside a quote pair stays within a single shlex token and cannot
    manufacture a phantom separator.
    """
    if "\n" not in cmd:
        return (cmd, "")
    for marker in HEREDOC_MARKERS:
        if marker in cmd:
            return (None, "multiline")

    out: list[str] = []
    i = 0
    n = len(cmd)
    while i < n:
        ch = cmd[i]
        if ch != "\n":
            out.append(ch)
            i += 1
            continue

        # Look past a run of horizontal whitespace to find the next real char.
        j = i + 1
        while j < n and cmd[j] in (" ", "\t"):
            j += 1

        # Case 1: trailing newline, or newline followed only by horizontal
        # whitespace then end / another newline -> terminal soft-wrap. Drop
        # the newline and the whitespace run.
        if j >= n:
            i = j
            continue
        if cmd[j] == "\n":
            # Blank line: drop this newline + whitespace run; the next newline
            # is reclassified on its own against the (unchanged) logical line.
            i = j
            continue
        if j > i + 1:
            # There WAS horizontal whitespace after the newline -> soft-wrap.
            i = j
            continue

        # newline immediately followed by a non-whitespace char.
        logical = "".join(out).rstrip()
        if logical.endswith("\\") or logical.endswith(_TRAILING_CONTROL_OPERATORS):
            # Case 2: ambiguous continuation -> defer.
            return (None, "multiline")
        if logical.endswith(";"):
            # Case 3: already separated -> just drop the newline.
            i += 1
            continue
        # Case 4: real statement boundary -> inject a separator.
        out.append(" ; ")
        i += 1

    return ("".join(out).rstrip(), "")


# --------------------------------------------------------------------------- #
# Phase 2g: arbiter escalation tier.
# --------------------------------------------------------------------------- #
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_ARBITER_MODEL = "claude-haiku-4-5"
DEFAULT_ARBITER_MAX_TOKENS = 1024
DEFAULT_ARBITER_TIMEOUT_S = 8

ARBITER_SYSTEM = (
    "You are a safety arbiter for shell commands on a senior software engineer's "
    "development machine. A static permission gate could not prove this command "
    "safe, so it would normally interrupt the engineer for manual confirmation. "
    "Your job: decide whether the command is safe to AUTO-APPROVE without that "
    "confirmation.\n\n"
    "Approve (SAFE) only routine, low-risk development operations whose effects "
    "are read-only, local, and easily reversible: building, testing, linting, "
    "formatting, status/inspection, scoped git operations, package scripts, and "
    "writes confined to the project or temp dirs.\n\n"
    "Decline (UNSAFE) anything destructive or irreversible (mass/recursive "
    "deletion, history rewrites, disk/partition ops), privilege escalation "
    "(sudo to system-mutating actions), credential/secret exfiltration or "
    "deletion, outbound network mutations (POST/PUT/DELETE to non-localhost, "
    "uploads, remote shells, piping a download into a shell), changes to system "
    "or security configuration, or ANYTHING whose blast radius you cannot "
    "confidently bound. When uncertain, choose UNSAFE — a needless confirmation "
    "prompt is cheap; a wrong auto-approval is not.\n\n"
    "Respond with ONLY a single JSON object, no prose, no code fences:\n"
    '{"verdict": "SAFE" | "UNSAFE", "reasoning": "<one or two sentences a '
    'human will read to understand your decision>"}'
)


def _arbiter_config(config: dict) -> dict:
    a = (config.get("arbiter") if isinstance(config, dict) else None) or {}
    enabled = a.get("enabled", True)
    # Test seam: force enabled/disabled independent of the live yaml value so the
    # suite does not couple to whatever `arbiter.enabled` happens to be on disk.
    override = os.environ.get("BASH_GATE_ARBITER_ENABLE_OVERRIDE")
    if override == "1":
        enabled = True
    elif override == "0":
        enabled = False
    return {
        "enabled": bool(enabled),
        "model": a.get("model") or DEFAULT_ARBITER_MODEL,
        "max_tokens": int(a.get("max_tokens") or DEFAULT_ARBITER_MAX_TOKENS),
        "timeout": float(a.get("timeout_seconds") or DEFAULT_ARBITER_TIMEOUT_S),
    }


def _build_arbiter_prompt(cmd: str, cwd: str, defer_reason: str) -> str:
    return (
        f"Working directory: {cwd or '(unknown)'}\n"
        f"Static gate defer reason: {defer_reason or '(none)'}\n\n"
        "Command:\n"
        f"{cmd}\n\n"
        "Is this command safe to auto-approve? Respond with the JSON object only."
    )


def _parse_arbiter_verdict(text: str) -> tuple[str, str]:
    """Parse the model's reply into (verdict, reasoning).

    Lenient: prefers a JSON object, falls back to keyword scan, and defaults to
    UNSAFE when the verdict cannot be determined (fail toward asking the human).
    """
    text = (text or "").strip()
    obj: dict | None = None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            obj = parsed
    except Exception:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(0))
                if isinstance(parsed, dict):
                    obj = parsed
            except Exception:
                obj = None
    if obj is not None:
        verdict = str(obj.get("verdict", "")).strip().upper()
        reasoning = str(obj.get("reasoning", "")).strip()
        if verdict in ("SAFE", "UNSAFE"):
            return (verdict, reasoning or "(no reasoning provided)")
    up = text.upper()
    if "UNSAFE" in up:
        return ("UNSAFE", text[:300] or "(no reasoning provided)")
    if "SAFE" in up:
        return ("SAFE", text[:300] or "(no reasoning provided)")
    return ("UNSAFE", "arbiter reply unparseable; defaulting to UNSAFE")


def _invoke_arbiter(
    cmd: str, cwd: str, defer_reason: str, arb_cfg: dict
) -> tuple[str, str, dict]:
    """Consult the LLM arbiter. Returns (verdict, reasoning, meta).

    verdict in {SAFE, UNSAFE, ERROR}. ERROR means the call failed and the caller
    must fail safe (never auto-allow). Never raises.
    """
    # Test seam: a stubbed verdict short-circuits the network call entirely so
    # the fixture harness can exercise every escalation path hermetically.
    stub = os.environ.get("BASH_GATE_ARBITER_STUB_VERDICT")
    if stub:
        return (
            stub.strip().upper(),
            os.environ.get("BASH_GATE_ARBITER_STUB_REASON", "stubbed verdict"),
            {"model": "stub", "latency_ms": 0},
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return ("ERROR", "ANTHROPIC_API_KEY not set in hook env", {"error": "no-api-key"})

    import time
    import urllib.request

    body = json.dumps(
        {
            "model": arb_cfg["model"],
            "max_tokens": arb_cfg["max_tokens"],
            "system": ARBITER_SYSTEM,
            "messages": [
                {"role": "user", "content": _build_arbiter_prompt(cmd, cwd, defer_reason)}
            ],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=body,
        method="POST",
        headers={
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        },
    )
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=arb_cfg["timeout"]) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except Exception as e:
        return (
            "ERROR",
            f"arbiter call failed ({type(e).__name__})",
            {"error": str(e)[:200], "latency_ms": int((time.monotonic() - t0) * 1000)},
        )
    latency_ms = int((time.monotonic() - t0) * 1000)
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and data.get("type") == "error":
            msg = ((data.get("error") or {}).get("message")) or "unknown api error"
            return (
                "ERROR",
                f"arbiter api error: {msg}",
                {"error": msg[:200], "latency_ms": latency_ms},
            )
        text = "".join(
            b.get("text", "")
            for b in (data.get("content") or [])
            if isinstance(b, dict) and b.get("type") == "text"
        )
    except Exception as e:
        return (
            "ERROR",
            f"arbiter response parse failed ({type(e).__name__})",
            {"error": str(e)[:200], "latency_ms": latency_ms, "raw": raw[:300]},
        )
    verdict, reasoning = _parse_arbiter_verdict(text)
    return (verdict, reasoning, {"model": arb_cfg["model"], "latency_ms": latency_ms})


def _eligibility_segments(cmd: str) -> tuple[list[list[str]] | None, list[str] | None]:
    """Tokenize `cmd` and return (segments, all_tokens) for ask/deny matching.

    Segments are the outer &&/||/; statements further split on top-level `|`,
    with safe redirects left in place (matching is verb-prefix based, so trailing
    redirect tokens do not affect it). all_tokens is the full flat token list,
    used for full-command deny matching (pipe-spanning rules). Returns
    (None, None) when the command cannot be tokenized.
    """
    try:
        normalized = _normalize_operators(cmd)
        tokens = shlex.split(normalized, posix=True, comments=False)
    except ValueError:
        return (None, None)
    if not tokens:
        return (None, None)
    statements, _err = _split_outer_statements(tokens)
    if statements is None:
        # Redirect/heredoc broke the outer split; fall back to one pseudo-segment
        # so ask/deny matching can still run on the flat token list.
        return ([tokens], tokens)
    segs: list[list[str]] = []
    for stmt in statements:
        pipe_subs, _pe = _split_pipe_subsegments(stmt)
        if pipe_subs is None:
            segs.append(stmt)
        else:
            segs.extend(pipe_subs)
    return (segs, tokens)


def _classify_gate(cmd: str, config: dict) -> tuple[str, str]:
    """Classify a deferred command for gating. Returns (kind, reason).

    kind:
      - "none"        -> not gated by the hook (defer -> bypass under bypass
                         mode). Also covers deny matches (the hook never
                         overrides a deny) and untokenizable input.
      - "always-ask"  -> matches a Tier A always-ask pattern (settings.json
                         ask): deterministic prompt, NEVER arbitrated/auto-
                         approved. Catches buried `... && sudo y` too.
      - "gated"       -> matches a Tier B gated_pattern (yaml): hand to the
                         arbiter (SAFE -> allow, else ask).

    Precedence: deny > always-ask > gated. A deny match anywhere (per-segment or
    full-command, to catch pipe-spanning rules) forces "none".
    """
    segs, all_tokens = _eligibility_segments(cmd)
    if segs is None:
        return ("none", "untokenizable")

    deny_patterns = _get_deny_patterns()
    if deny_patterns:
        if all_tokens is not None:
            hit, raw = _matches_any_deny_pattern(all_tokens, deny_patterns)
            if hit:
                return ("none", f"deny-match:{raw}")
        for seg in segs:
            hit, raw = _matches_any_deny_pattern(seg, deny_patterns)
            if hit:
                return ("none", f"deny-match:{raw}")

    always_ask = _get_always_ask_patterns()
    for seg in segs:
        hit, raw = _matches_any_pattern(seg, always_ask)
        if hit:
            return ("always-ask", f"always-ask:{raw}")

    gated = _get_gated_patterns(config)
    for seg in segs:
        hit, raw = _matches_any_pattern(seg, gated)
        if hit:
            return ("gated", f"gated-match:{raw}")
    return ("none", "no-gate-match")


def _maybe_arbitrate(
    cmd: str, payload: dict, config: dict, defer_reason: str
) -> dict | None:
    """Gate a deferred GATED command (hook is the sole gate for these verbs).

    Returns None when the command is not gated (ineligible) — the caller then
    logs the defer, which under bypassPermissions means the command runs. For a
    gated command this NEVER returns a silent bypass: it returns a dict
    {blob, final, reason, [emit_reason]} with `final` in {'allow','ask'}.

    Fail-safe direction: since gated verbs no longer have a settings.json `ask`
    backstop, every uncertain outcome (arbiter disabled, ERROR, or UNSAFE) ends
    in `ask`. Only an explicit arbiter SAFE verdict yields `allow`.
    """
    kind, gate_reason = _classify_gate(cmd, config)
    if kind == "none":
        return None
    if kind == "always-ask":
        # Tier A: deterministic confirmation. NEVER arbitrated/auto-approved,
        # even in a compound where the verb is buried (`... && sudo y`).
        return {
            "blob": {
                "fired": False,
                "eligibility": gate_reason,
                "escalation": "user-confirm",
                "reason": "always-ask",
            },
            "final": "ask",
            "reason": f"always-ask gate ({gate_reason})",
            "emit_reason": "bash-gate: this command always requires your confirmation.",
        }
    # kind == "gated" -> hand to the arbiter (fail-closed on any error).
    try:
        return _gate_eligible(cmd, payload, config, defer_reason, gate_reason)
    except Exception as e:
        # A gated command must never silently bypass — fail closed to ask.
        return {
            "blob": {
                "fired": True,
                "verdict": "ERROR",
                "eligibility": gate_reason,
                "escalation": "error-fallback",
                "error": f"{type(e).__name__}:{e}"[:200],
            },
            "final": "ask",
            "reason": f"gating-error ({gate_reason})",
            "emit_reason": (
                "bash-gate: the safety check errored on this gated command — "
                "confirm to proceed."
            ),
        }


def _gate_eligible(
    cmd: str, payload: dict, config: dict, defer_reason: str, elig_reason: str
) -> dict:
    """Resolve a known-gated command to allow/ask. Called only for eligible cmds."""
    arb_cfg = _arbiter_config(config)
    arbiter_on = arb_cfg["enabled"] and os.environ.get("BASH_GATE_ARBITER_DISABLE") != "1"

    if not arbiter_on:
        # Deterministic gate: no arbiter -> prompt. Preserves the pre-inversion
        # "always confirm this verb" behavior now that it is no longer in
        # settings.json's ask list.
        return {
            "blob": {
                "fired": False,
                "eligibility": elig_reason,
                "escalation": "user-confirm",
                "reason": "arbiter-disabled",
            },
            "final": "ask",
            "reason": f"gated command, arbiter disabled ({elig_reason})",
            "emit_reason": (
                "bash-gate: this command matches a gated pattern and the arbiter "
                "is disabled — confirm to proceed."
            ),
        }

    raw_cwd = payload.get("cwd") or ""
    verdict, reasoning, meta = _invoke_arbiter(cmd, raw_cwd, defer_reason, arb_cfg)

    blob: dict = {
        "fired": True,
        "verdict": verdict,
        "reasoning": reasoning,
        "eligibility": elig_reason,
        "model": meta.get("model"),
        "latency_ms": meta.get("latency_ms"),
    }
    if meta.get("error"):
        blob["error"] = meta["error"]

    if verdict == "SAFE":
        blob["escalation"] = "auto-approved"
        return {
            "blob": blob,
            "final": "allow",
            "reason": f"arbiter-approved ({elig_reason}): {reasoning}",
            "emit_reason": f"bash-gate arbiter auto-approved this command.\nReasoning: {reasoning}",
        }
    if verdict == "UNSAFE":
        blob["escalation"] = "user-confirm"
        return {
            "blob": blob,
            "final": "ask",
            "reason": f"arbiter-declined ({elig_reason})",
            "emit_reason": (
                "bash-gate arbiter could not confirm this command is safe to "
                "auto-run and is escalating to you.\n\n"
                f"Arbiter reasoning: {reasoning}"
            ),
        }
    # ERROR -> fail safe to ask (no settings.json backstop remains).
    blob["escalation"] = "error-fallback"
    return {
        "blob": blob,
        "final": "ask",
        "reason": f"arbiter-error ({elig_reason}): {reasoning}",
        "emit_reason": (
            "bash-gate arbiter could not be reached for a safety check on this "
            f"gated command — confirm to proceed.\n\nDetail: {reasoning}"
        ),
    }


def decide(payload: dict, config: dict | None) -> tuple[str, str, str, str]:
    """Return (decision, reason, log_class, cmd)."""
    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}
    cmd = (tool_input.get("command") or "").strip()

    if tool_name != "Bash":
        return ("skip", "not-bash", "", cmd)
    if not cmd:
        return ("defer", "empty-command", "", cmd)

    for needle in UNSAFE_SUBSTRINGS:
        if needle in cmd:
            return ("defer", "dynamic-eval", "", cmd)

    cmd_for_parse, wrap_err = _normalize_line_wraps(cmd)
    if cmd_for_parse is None:
        return ("defer", wrap_err, "", cmd)

    try:
        normalized = _normalize_operators(cmd_for_parse)
        tokens = shlex.split(normalized, posix=True, comments=False)
    except ValueError as e:
        return ("defer", f"unparseable({e})", "", cmd)

    if not tokens:
        return ("defer", "no-tokens", "", cmd)

    if not config:
        return ("defer", "no-config", "", cmd)

    dev_roots = _resolved_dev_roots(config)

    # Phase 2f: seed effective_cwd from payload.
    raw_cwd = payload.get("cwd") or ""
    if raw_cwd:
        effective_cwd = os.path.normpath(_expand_user(raw_cwd))
    else:
        effective_cwd = ""

    statements, split_err = _split_outer_statements(tokens)
    if statements is None:
        if split_err.startswith("pipe-or-redirect"):
            return ("defer", f"dynamic-eval({split_err})", "", cmd)
        return ("defer", split_err, "", cmd)

    # Walk outer statements left-to-right. cd-mutations update effective_cwd.
    # Single-statement / single-pipe-sub fast path preserves legacy log_class.
    if len(statements) == 1:
        # Check whether it's a pure cd, a single non-pipe segment, or a pipe.
        pipe_subs, _pe = _split_pipe_subsegments(statements[0])
        if pipe_subs is not None and len(pipe_subs) == 1:
            # Single statement, single sub. Behave like the old single-segment path.
            residual, redirect_err = strip_safe_redirects(pipe_subs[0], dev_roots)
            if residual is None:
                return ("defer", f"dynamic-eval({redirect_err})", "", cmd)
            if not residual:
                return ("defer", "empty-segment-after-redirect-strip", "", cmd)
            cd_kind, _arg, cd_reason = _parse_cd_segment(residual)
            if cd_kind == "cd-defer":
                return ("defer", f"compound-segment(first=cd,reason={cd_reason})", "compound", cmd)
            if cd_kind == "cd-valid":
                # A standalone cd is harmless but doesn't allow anything. Defer.
                return ("defer", "standalone-cd-no-effect", "cd", cmd)
            decision, reason, log_class = _dispatch_single(residual, config, effective_cwd)
            return (decision, reason, log_class, cmd)

    # Compound (or single statement with pipes).
    seg_summaries: list[str] = []
    for stmt in statements:
        state, summary, log_class = _evaluate_statement(stmt, config, dev_roots, effective_cwd)
        if state == SEG_DEFER:
            first_tok = stmt[0] if stmt else ""
            return (
                "defer",
                f"compound-segment(first={first_tok},reason={summary})",
                "compound",
                cmd,
            )
        if state == SEG_CWD_MUTATION:
            effective_cwd = summary  # new cwd
            seg_summaries.append(f"cwd(cd:{os.path.basename(summary) or '/'})")
            continue
        if state == SEG_ALLOW:
            seg_summaries.append(log_class or "?")
        else:  # SEG_INERT
            seg_summaries.append(log_class or "inert")

    return (
        "allow",
        f"compound[{', '.join(seg_summaries)}]",
        "compound",
        cmd,
    )


def _explain(cmd: str, cwd: str) -> str:
    """Produce a human-readable segment-by-segment breakdown of how the gate would classify `cmd`.

    Re-uses the existing classification functions. NEVER writes to the JSONL log.
    NEVER emits the hookSpecificOutput JSON. Pure stdout report.
    """
    out: list[str] = []
    config = _load_config()

    out.append(f"command: {cmd}")
    out.append(f"cwd: {cwd}")

    if not cmd.strip():
        out.append("overall: DEFER (empty command)")
        return "\n".join(out)

    # Mirror decide()'s early guards.
    for needle in UNSAFE_SUBSTRINGS:
        if needle in cmd:
            out.append(f"overall: DEFER (dynamic-eval: contains {needle!r})")
            return "\n".join(out)

    cmd_for_parse, wrap_err = _normalize_line_wraps(cmd)
    if cmd_for_parse is None:
        out.append(f"overall: DEFER ({wrap_err})")
        return "\n".join(out)
    if cmd_for_parse != cmd:
        out.append(
            "note: collapsed line-wrap whitespace before parsing (original cmd preserved in log)"
        )

    try:
        normalized = _normalize_operators(cmd_for_parse)
        tokens = shlex.split(normalized, posix=True, comments=False)
    except ValueError as e:
        out.append(f"overall: DEFER (unparseable: {e})")
        return "\n".join(out)

    if not tokens:
        out.append("overall: DEFER (no-tokens)")
        return "\n".join(out)
    if not config:
        out.append("overall: DEFER (no-config)")
        return "\n".join(out)

    dev_roots = _resolved_dev_roots(config)
    effective_cwd = os.path.normpath(_expand_user(cwd)) if cwd else ""

    statements, split_err = _split_outer_statements(tokens)
    if statements is None:
        out.append(f"overall: DEFER ({split_err})")
        return "\n".join(out)

    out.append(f"effective cwd seed: {effective_cwd or '(none)'}")
    out.append(f"outer segments ({len(statements)}):")

    overall_defer_reason: str | None = None

    for idx, stmt in enumerate(statements, 1):
        # Inline segment text reconstructed via shlex-style join.
        seg_text = " ".join(stmt)
        out.append(f"  [{idx}] {seg_text}")

        pipe_subs, pipe_err = _split_pipe_subsegments(stmt)
        if pipe_subs is None:
            out.append(f"       => SEG_DEFER ({pipe_err})")
            if overall_defer_reason is None:
                overall_defer_reason = f"segment {idx}: {pipe_err}"
            continue

        if len(pipe_subs) == 1:
            sub = pipe_subs[0]
            residual, redirect_err = strip_safe_redirects(sub, dev_roots)
            if residual is None:
                out.append(f"       => SEG_DEFER (unsafe-redirect: {redirect_err})")
                if overall_defer_reason is None:
                    overall_defer_reason = f"segment {idx}: unsafe-redirect {redirect_err}"
                continue
            if not residual:
                out.append("       => SEG_DEFER (empty-after-redirect-strip)")
                if overall_defer_reason is None:
                    overall_defer_reason = f"segment {idx}: empty after redirect strip"
                continue
            if residual != sub:
                out.append(f"       residual after redirect strip: {' '.join(residual)}")

            cd_kind, cd_arg, cd_reason = _parse_cd_segment(residual)
            if cd_kind == "cd-defer":
                out.append(f"       classification: CD_DEFER ({cd_reason})")
                out.append("       => SEG_DEFER")
                if overall_defer_reason is None:
                    overall_defer_reason = f"segment {idx}: cd {cd_reason}"
                continue
            if cd_kind == "cd-valid":
                new_cwd = _resolve_cd(effective_cwd, cd_arg or "")
                out.append(f"       classification: CWD_MUTATION (effective_cwd -> {new_cwd})")
                effective_cwd = new_cwd
                continue

            _explain_single(residual, config, effective_cwd, out, idx)
            state = _explain_get_last_state(out)
            if state == SEG_DEFER and overall_defer_reason is None:
                overall_defer_reason = f"segment {idx} is dangerous"
            continue

        # Multi-pipe.
        out.append(f"       pipe sub-segments ({len(pipe_subs)}):")
        any_defer = False
        any_allow = False
        for sidx, sub in enumerate(pipe_subs):
            sub_label = f"{idx}{chr(ord('a') + sidx)}"
            residual, redirect_err = strip_safe_redirects(sub, dev_roots)
            if residual is None:
                out.append(f"         [{sub_label}] {' '.join(sub)}")
                out.append(f"              => SEG_DEFER (unsafe-redirect: {redirect_err})")
                any_defer = True
                continue
            if not residual:
                out.append(f"         [{sub_label}] (empty after redirect strip)")
                out.append("              => SEG_DEFER")
                any_defer = True
                continue
            out.append(f"         [{sub_label}] {' '.join(residual)}")
            cd_kind, _arg, _r = _parse_cd_segment(residual)
            if cd_kind != "not-cd":
                out.append("              => SEG_DEFER (cd-inside-pipe)")
                any_defer = True
                continue
            sub_state = _explain_single(
                residual, config, effective_cwd, out, sub_label, indent="              "
            )
            if sub_state == SEG_DEFER:
                any_defer = True
            elif sub_state == SEG_ALLOW:
                any_allow = True
        if any_defer:
            out.append("       => SEG_DEFER (one or more pipe sub-segments deferred)")
            if overall_defer_reason is None:
                overall_defer_reason = f"segment {idx}: pipe sub-segment deferred"
        elif any_allow:
            out.append("       => SEG_ALLOW (pipe: at least one ALLOW, rest INERT)")
        else:
            out.append("       => SEG_ALLOW (all pipe sub-segments INERT)")

    if overall_defer_reason:
        out.append(f"overall: DEFER ({overall_defer_reason})")
    else:
        out.append("overall: ALLOW")
    return "\n".join(out)


def _explain_single(
    residual: list[str],
    config: dict,
    effective_cwd: str,
    out: list[str],
    label,
    indent: str = "       ",
) -> str:
    """Append classification detail for a single non-pipe, non-cd segment. Returns state."""
    decision, reason, log_class = _dispatch_single(residual, config, effective_cwd)
    verb, _ = _first_verb_after_env(residual)

    # Enumerate which classes matched the verb, for explain output.
    matched_classes: list[str] = []
    for rule in config.get("classes", []) or []:
        match_one = rule.get("match_first_word")
        match_many = rule.get("match_first_word_one_of") or []
        if match_one == verb or verb in match_many:
            matched_classes.append(rule.get("name") or rule.get("log_as") or "?")

    if matched_classes:
        out.append(
            f"{indent}candidate allow classes for verb '{verb}': {', '.join(matched_classes)}"
        )
    else:
        out.append(f"{indent}no allow class matches verb '{verb}'")

    # Always-ask (Tier A) check (settings.json permissions.ask), then gated
    # (Tier B) check (hook-owned gated_patterns). Always-ask takes precedence.
    aa_matched, aa_pat = _matches_any_pattern(residual, _get_always_ask_patterns())
    if aa_matched:
        out.append(f"{indent}always-ask match: {aa_pat}")
    else:
        out.append(f"{indent}always-ask match: none")

    matched, raw_pat = _matches_any_pattern(residual, _get_gated_patterns(config))
    if matched:
        out.append(f"{indent}gated-pattern match: {raw_pat}")
    else:
        out.append(f"{indent}gated-pattern match: none")

    if decision == "allow":
        out.append(f"{indent}=> SEG_ALLOW via {log_class} ({reason})")
        return SEG_ALLOW

    # decision == "defer". Now decide INERT vs DEFER_DANGEROUS via gated-pattern.
    state, state_reason, _lc = _classify_segment(residual, config, effective_cwd)
    if state == SEG_INERT:
        out.append(f"{indent}=> SEG_INERT (no gated-pattern match; would auto-allow in compound)")
        return SEG_INERT
    if state == SEG_ALLOW:
        out.append(f"{indent}=> SEG_ALLOW ({state_reason})")
        return SEG_ALLOW
    out.append(f"{indent}dispatch defer reason: {reason}")
    out.append(f"{indent}=> SEG_DEFER_DANGEROUS")
    return SEG_DEFER


def _explain_get_last_state(out: list[str]) -> str:
    """Peek at the last line appended by _explain_single to infer state for overall calc."""
    for line in reversed(out):
        s = line.strip()
        if s.startswith("=>"):
            if "SEG_ALLOW" in s:
                return SEG_ALLOW
            if "SEG_INERT" in s:
                return SEG_INERT
            if "SEG_DEFER" in s:
                return SEG_DEFER
            return ""
    return ""


def _run_explain_cli(argv: list[str]) -> int:
    """CLI entry point for --explain mode. Returns process exit code."""
    cmd: str | None = None
    cwd: str = os.getcwd()
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--cmd":
            if i + 1 >= len(argv):
                sys.stderr.write("--cmd requires an argument\n")
                return 2
            cmd = argv[i + 1]
            i += 2
            continue
        if a.startswith("--cmd="):
            cmd = a.split("=", 1)[1]
            i += 1
            continue
        if a == "--cwd":
            if i + 1 >= len(argv):
                sys.stderr.write("--cwd requires an argument\n")
                return 2
            cwd = argv[i + 1]
            i += 2
            continue
        if a.startswith("--cwd="):
            cwd = a.split("=", 1)[1]
            i += 1
            continue
        if a == "--explain":
            i += 1
            continue
        sys.stderr.write(f"unknown arg: {a}\n")
        return 2
    if cmd is None:
        sys.stderr.write("--cmd is required in --explain mode\n")
        return 2
    sys.stdout.write(_explain(cmd, cwd) + "\n")
    return 0


def main() -> int:
    # --explain CLI mode: do NOT read stdin, do NOT touch the log, do NOT emit hookSpecificOutput.
    if "--explain" in sys.argv[1:] or "--cmd" in sys.argv[1:] or any(
        a.startswith("--cmd=") for a in sys.argv[1:]
    ):
        return _run_explain_cli(sys.argv[1:])

    raw = ""
    payload: dict = {}
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception as e:
        _log(
            {
                "ts": _now_iso(),
                "session_id": "",
                "cwd": os.getcwd(),
                "cmd": raw[:200],
                "class": "",
                "decision": "defer",
                "reason": f"malformed-input({type(e).__name__})",
            }
        )
        return 0

    config = _load_config()

    try:
        decision, reason, log_class, cmd = decide(payload, config)
    except Exception as e:
        _log(
            {
                "ts": _now_iso(),
                "session_id": payload.get("session_id", ""),
                "cwd": payload.get("cwd") or os.getcwd(),
                "cmd": (payload.get("tool_input") or {}).get("command", "")[:500],
                "class": "",
                "decision": "defer",
                "reason": f"internal-error({type(e).__name__}:{e})",
                "trace": traceback.format_exc()[-500:],
            }
        )
        return 0

    if decision == "skip":
        return 0

    arbiter_blob: dict | None = None
    emit: tuple[str, str] | None = ("allow", reason) if decision == "allow" else None

    if decision == "defer":
        try:
            arb = _maybe_arbitrate(cmd, payload, config or {}, reason)
        except Exception as e:
            # The arbiter must never block Bash. Any unexpected failure degrades
            # to the legacy defer (CC's own rules prompt), recorded in telemetry.
            arb = None
            arbiter_blob = {
                "fired": True,
                "verdict": "ERROR",
                "escalation": "error-fallback",
                "error": f"{type(e).__name__}:{e}"[:200],
            }
        if arb is not None:
            arbiter_blob = arb["blob"]
            log_class = "arbiter"
            reason = arb["reason"]
            decision = arb["final"]  # allow | ask | defer
            if arb["final"] == "allow":
                emit = ("allow", arb["emit_reason"])
            elif arb["final"] == "ask":
                emit = ("ask", arb["emit_reason"])

    entry = {
        "ts": _now_iso(),
        "session_id": payload.get("session_id", ""),
        "cwd": payload.get("cwd") or os.getcwd(),
        "cmd": cmd,
        "class": log_class,
        "decision": decision,
        "reason": reason,
    }
    if arbiter_blob:
        entry["arbiter"] = arbiter_blob
    _log(entry)

    if emit is not None:
        if emit[0] == "allow":
            _emit_allow(emit[1])
        else:
            _emit_ask(emit[1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
