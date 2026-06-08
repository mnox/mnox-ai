#!/usr/bin/env bash
# Fire-and-forget SessionStart hook for session-tracker-mcp.
# Captures tty + parent pid (the host agent process) BEFORE detaching.

set -u

PKG_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." &> /dev/null && pwd)"

# Dependencies are installed lazily by bin/server.sh on MCP startup. If they are
# not present yet (very first run), skip rather than race the installer.
[ -d "$PKG_DIR/node_modules" ] || exit 0

LOG_DIR="${SESSION_TRACKER_LOG_DIR:-${SESSION_TRACKER_HOME:-$HOME/.mnox-ai/session-tracker}/logs}"
mkdir -p "$LOG_DIR"

CAPTURED_PPID="$PPID"
# `tty` reads stdin, which is the hook's JSON payload — not useful.
# The parent agent inherits the real terminal's tty.
RAW_TTY="$(ps -o tty= -p "$CAPTURED_PPID" 2>/dev/null | tr -d ' ')"
if [ -n "$RAW_TTY" ] && [ "$RAW_TTY" != "?" ] && [ "$RAW_TTY" != "??" ]; then
  CAPTURED_TTY="/dev/$RAW_TTY"
else
  CAPTURED_TTY=""
fi

PAYLOAD_FILE="$(mktemp -t session-tracker-start.XXXXXX.json)"
cat > "$PAYLOAD_FILE"

LOG_FILE="$LOG_DIR/presence.log"

(
  nohup bun run "$PKG_DIR/src/hooks/presence-hook.ts" \
    start "$PAYLOAD_FILE" "$CAPTURED_TTY" "$CAPTURED_PPID" \
    >> "$LOG_FILE" 2>&1
  rm -f "$PAYLOAD_FILE"
) </dev/null >/dev/null 2>&1 &
disown

exit 0
