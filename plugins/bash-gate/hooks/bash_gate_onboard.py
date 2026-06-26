#!/usr/bin/env python3
"""bash_gate_onboard.py — SessionStart onboarding nudge for the bash-gate plugin.

The PreToolUse gate ships SAFE-BY-DEFAULT: with no dev_roots configured it
auto-allows nothing, so a fresh `/plugin install` is a SILENT NO-OP. Nothing
otherwise tells the user the plugin is installed-but-inert or how to activate
it. This SessionStart hook closes that gap with a ONE-TIME nudge.

Behavior (always exits 0 — a SessionStart hook must never block startup):
  - marker present            -> stay silent (already prompted / dismissed).
  - functional install        -> write the marker, stay silent (never nag a
    (PyYAML + non-empty dev_roots)  configured user).
  - otherwise                 -> emit ONE SessionStart additionalContext nudge
    explaining the plugin is inert and how to opt in, then write the marker so
    it never fires again.

The marker file (<USER_DIR>/.onboarded) IS the "has the user been prompted?"
tracker. `bash-gate-setup.sh` writes it too, so running setup also silences the
nudge. Delete the marker to see the nudge again.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Mirror bash_gate.py: the user-writable home survives `claude plugin update`.
USER_DIR = Path(os.environ.get("BASH_GATE_HOME") or os.path.expanduser("~/.config/bash-gate"))
MARKER = USER_DIR / ".onboarded"
USER_CONFIG = USER_DIR / "config.yaml"
# This script lives at <plugin_root>/hooks/bash_gate_onboard.py.
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SETUP_SCRIPT = PLUGIN_ROOT / "scripts" / "bash-gate-setup.sh"


def _pyyaml_ok() -> bool:
    try:
        import yaml  # type: ignore  # noqa: F401
        return True
    except Exception:
        return False


def _dev_roots_configured() -> bool:
    """True only if PyYAML is importable AND the user config declares >=1 dev root.

    That is the exact condition under which the gate can actually auto-allow
    anything path-based — i.e. the install is no longer an inert no-op.
    """
    if not _pyyaml_ok():
        return False
    try:
        import yaml  # type: ignore

        with USER_CONFIG.open() as fh:
            data = yaml.safe_load(fh) or {}
    except Exception:
        return False  # missing/unreadable/garbage config -> not configured
    roots = data.get("dev_roots") if isinstance(data, dict) else None
    return bool([r for r in (roots or []) if isinstance(r, str) and r.strip()])


def _nudge_text() -> str:
    lines = [
        "Show the user this bash-gate onboarding notice once, then continue:",
        "",
        "⚙️  bash-gate is installed but currently INERT — it is auto-allowing "
        "nothing, so you are still approving every Bash command by hand.",
    ]
    if not _pyyaml_ok():
        lines.append(
            "   • Its required PyYAML dependency is missing — the hook cannot "
            "load any config without it."
        )
    lines += [
        "   • No dev roots are configured yet, so no path is eligible for "
        "auto-allow.",
        "",
        "To activate it (one time):",
        f"   1. Run:  bash {SETUP_SCRIPT}",
        '   2. Add your dev roots to ~/.config/bash-gate/config.yaml under '
        '`dev_roots:` (e.g. "~/dev").',
        "",
        "This notice will not appear again.",
    ]
    return "\n".join(lines)


def _write_marker() -> None:
    try:
        USER_DIR.mkdir(parents=True, exist_ok=True)
        MARKER.write_text("bash-gate onboarding shown\n")
    except Exception:
        pass  # best-effort; never break startup over a marker write


def main() -> int:
    try:
        if MARKER.exists():
            return 0  # already prompted / dismissed
        if _dev_roots_configured():
            _write_marker()  # functional install — never nag
            return 0
        out = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": _nudge_text(),
            }
        }
        sys.stdout.write(json.dumps(out))
        _write_marker()
    except Exception:
        # A SessionStart hook must never block the session over its own error.
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
