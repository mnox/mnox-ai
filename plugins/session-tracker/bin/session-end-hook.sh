#!/usr/bin/env bash
# Fire-and-forget SessionEnd hook for session-tracker-mcp.

set -u

PKG_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." &> /dev/null && pwd)"

# Dependencies are installed lazily by bin/server.sh on MCP startup. If they are
# not present yet (very first run), skip rather than race the installer.
[ -d "$PKG_DIR/node_modules" ] || exit 0

LOG_DIR="${SESSION_TRACKER_LOG_DIR:-${SESSION_TRACKER_HOME:-$HOME/.mnox-ai/session-tracker}/logs}"
mkdir -p "$LOG_DIR"

PAYLOAD_FILE="$(mktemp -t session-tracker-end.XXXXXX.json)"
cat > "$PAYLOAD_FILE"

LOG_FILE="$LOG_DIR/presence.log"

(
  nohup bun run "$PKG_DIR/src/hooks/presence-hook.ts" \
    end "$PAYLOAD_FILE" \
    >> "$LOG_FILE" 2>&1
  rm -f "$PAYLOAD_FILE"
) </dev/null >/dev/null 2>&1 &
disown

exit 0
