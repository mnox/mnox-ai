#!/usr/bin/env bash
# MCP server launcher for session-tracker.
# Plugin install does not run `bun install`, so we ensure dependencies exist
# (idempotently) before starting the stdio server. All bootstrap chatter goes
# to stderr — stdout is reserved for the JSON-RPC stream.

set -euo pipefail

PKG_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." &> /dev/null && pwd)"

if ! command -v bun >/dev/null 2>&1; then
  echo "session-tracker: 'bun' was not found on PATH. Install Bun (https://bun.sh) and restart your agent host." >&2
  exit 1
fi

if [ ! -d "$PKG_DIR/node_modules" ]; then
  echo "session-tracker: installing dependencies (first run)…" >&2
  ( cd "$PKG_DIR" && bun install --frozen-lockfile >&2 ) \
    || ( cd "$PKG_DIR" && bun install >&2 )
fi

exec bun run "$PKG_DIR/src/server.ts"
