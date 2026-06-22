#!/usr/bin/env bash
# install.sh — provider-agnostic bootstrap for config-chunks.
#
# Claude Code users don't need this: `claude plugin install config-chunks@mnox-ai`
# installs the plugin and a SessionStart hook auto-reconciles every session.
#
# This script is the equivalent for ANY OTHER host (Codex, Cursor, Gemini CLI,
# Copilot — anything that reads an AGENTS.md). Point it at your host's AGENTS.md
# and it wires targets, applies a chunk set, and reconciles the bundle into that
# file — out of the box, in one command:
#
#   git clone https://github.com/mnox/mnox-ai ~/.mnox-ai
#   ~/.mnox-ai/plugins/config-chunks/install.sh --agents-path ~/myproject/AGENTS.md
#
# It drives the same engine (scripts/chunks-config.sh) the skills drive — it never
# hand-edits chunks.yaml or any host file. Idempotent: safe to re-run.
set -euo pipefail

# This script lives at the plugin root, so its own dir IS the engine home. Export
# it as CONFIG_CHUNKS_HOME so every engine call resolves the same root regardless
# of the caller's CWD or whether the host exports CLAUDE_PLUGIN_ROOT.
CONFIG_CHUNKS_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CONFIG_CHUNKS_HOME
ENGINE="$CONFIG_CHUNKS_HOME/scripts/chunks-config.sh"

usage() {
  cat <<'EOF'
config-chunks installer (non-Claude hosts)

Usage:
  install.sh [--agents-path PATH | --codex | --claude] [options]

Target selection (pick how the bundle is wired):
  --agents-path PATH   Write the bundle into this AGENTS.md file (Cursor: your
                       project's AGENTS.md; any AGENTS.md-reading host).
  --codex              Shorthand for --agents-path ~/.codex/AGENTS.md.
  --claude             Maintain ~/.claude/CLAUDE.md via @import (Claude Code).
  --targets LIST       Explicit space/comma list, e.g. "claude agents", to
                       maintain more than one target at once.

Chunk selection:
  --group NAME         Subscribe to this group (default: recommended).
  --no-recommended     Don't apply any group — just wire targets and stop.

Convenience:
  --print-home         Print the `export CONFIG_CHUNKS_HOME=...` line and exit.
  -h, --help           This help.

Auto-refresh is Claude-only (SessionStart hook). Everywhere else, re-run the
reconcile to pick up new chunk versions between sessions:
  CONFIG_CHUNKS_HOME=<this dir> bash <this dir>/scripts/reconcile.sh
(install.sh prints the exact command for your checkout when it finishes.)
EOF
}

# --- parse args ---
AGENTS_PATH=""
TARGETS=""
GROUP="recommended"
APPLY_GROUP=1
WANT_CLAUDE=0
WANT_AGENTS=0

while [ $# -gt 0 ]; do
  case "$1" in
    --agents-path) AGENTS_PATH="${2:-}"; WANT_AGENTS=1; shift 2 ;;
    --codex)       AGENTS_PATH="$HOME/.codex/AGENTS.md"; WANT_AGENTS=1; shift ;;
    --claude)      WANT_CLAUDE=1; shift ;;
    --targets)     TARGETS="${2:-}"; shift 2 ;;
    --group)       GROUP="${2:-}"; shift 2 ;;
    --no-recommended) APPLY_GROUP=0; shift ;;
    --print-home)  printf 'export CONFIG_CHUNKS_HOME=%q\n' "$CONFIG_CHUNKS_HOME"; exit 0 ;;
    -h|--help)     usage; exit 0 ;;
    *) echo "install.sh: unknown argument '$1'" >&2; usage >&2; exit 2 ;;
  esac
done

[ -f "$ENGINE" ] || { echo "install.sh: engine not found at $ENGINE — is this the plugin root?" >&2; exit 1; }

# --- resolve the target set ---
# Explicit --targets wins. Otherwise infer from the flags, then fall back to
# auto-detecting Claude. Never guess an AGENTS.md path.
if [ -n "$TARGETS" ]; then
  TARGETS="${TARGETS//,/ }"
  case " $TARGETS " in *" agents "*) WANT_AGENTS=1 ;; esac
  case " $TARGETS " in *" claude "*) WANT_CLAUDE=1 ;; esac
else
  TARGET_LIST=()
  [ "$WANT_CLAUDE" -eq 1 ] && TARGET_LIST+=("claude")
  [ "$WANT_AGENTS" -eq 1 ] && TARGET_LIST+=("agents")
  if [ "${#TARGET_LIST[@]}" -eq 0 ]; then
    # Nothing specified — auto-detect Claude, else require an explicit choice.
    if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] || [ -f "$HOME/.claude/CLAUDE.md" ]; then
      TARGET_LIST+=("claude"); WANT_CLAUDE=1
    else
      echo "install.sh: no target specified and Claude not detected." >&2
      echo "  Pass --agents-path <your AGENTS.md>, --codex, or --claude." >&2
      exit 2
    fi
  fi
  TARGETS="${TARGET_LIST[*]}"
fi

if [ "$WANT_AGENTS" -eq 1 ] && [ -z "$AGENTS_PATH" ]; then
  echo "install.sh: the 'agents' target needs a path — pass --agents-path <AGENTS.md> (or --codex)." >&2
  exit 2
fi

echo "config-chunks installer"
echo "  engine home : $CONFIG_CHUNKS_HOME"
echo "  targets     : $TARGETS"
[ -n "$AGENTS_PATH" ] && echo "  agents_path : $AGENTS_PATH"
echo

# --- drive the engine (idempotent) ---
# shellcheck disable=SC2086  # $TARGETS is an intentional word list of validated tokens.
bash "$ENGINE" set-targets $TARGETS
if [ "$WANT_AGENTS" -eq 1 ]; then
  bash "$ENGINE" set-agents-path "$AGENTS_PATH"
fi
if [ "$APPLY_GROUP" -eq 1 ]; then
  bash "$ENGINE" add-group "$GROUP"
fi

# --- report + refresh guidance ---
echo
echo "Done. The bundle has been reconciled into your target file(s)."
if [ "$WANT_AGENTS" -eq 1 ]; then
  echo "  → $AGENTS_PATH now holds the managed config-chunks block."
fi
if [ "$WANT_CLAUDE" -eq 1 ]; then
  echo "  → ~/.claude/CLAUDE.md now @imports ~/.claude/chunks/bundle.md."
fi
cat <<EOF

To pick up new chunk versions later (no auto-refresh off Claude Code), re-run:

  CONFIG_CHUNKS_HOME=$CONFIG_CHUNKS_HOME bash "$CONFIG_CHUNKS_HOME/scripts/reconcile.sh"

Tip — alias it (add to your shell rc):

  alias config-chunks-refresh='CONFIG_CHUNKS_HOME=$CONFIG_CHUNKS_HOME bash "$CONFIG_CHUNKS_HOME/scripts/reconcile.sh"'

Manage subscriptions any time with the same engine:

  CONFIG_CHUNKS_HOME=$CONFIG_CHUNKS_HOME bash "$ENGINE" list
EOF
