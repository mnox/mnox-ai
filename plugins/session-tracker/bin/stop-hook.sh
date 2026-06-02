#!/usr/bin/env bash
# Fire-and-forget Stop hook for session-tracker-mcp.
# Captures Claude Code's JSON payload from stdin, then detaches a Bun
# indexer process so the session thread is never blocked.

set -u

PKG_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." &> /dev/null && pwd)"

# Dependencies are installed lazily by bin/server.sh on MCP startup. If they are
# not present yet (very first run), skip rather than race the installer.
[ -d "$PKG_DIR/node_modules" ] || exit 0

LOG_DIR="$HOME/.claude/sessions/logs"
mkdir -p "$LOG_DIR"

# `tty` reads stdin, which is the hook's JSON payload — not useful.
# The parent (claude) inherits the real terminal's tty.
RAW_TTY="$(ps -o tty= -p "$PPID" 2>/dev/null | tr -d ' ')"
if [ -n "$RAW_TTY" ] && [ "$RAW_TTY" != "?" ] && [ "$RAW_TTY" != "??" ]; then
  CAPTURED_TTY="/dev/$RAW_TTY"
else
  CAPTURED_TTY=""
fi

export OPENAI_API_KEY="${OPENAI_API_KEY:-}"

PAYLOAD_FILE="$(mktemp -t session-tracker-payload.XXXXXX.json)"
cat > "$PAYLOAD_FILE"

LOG_FILE="$LOG_DIR/stop-indexer.log"

(
  nohup bun run "$PKG_DIR/src/hooks/stop-indexer.ts" "$PAYLOAD_FILE" "$CAPTURED_TTY" \
    >> "$LOG_FILE" 2>&1
  rm -f "$PAYLOAD_FILE"
) </dev/null >/dev/null 2>&1 &
disown

exit 0
