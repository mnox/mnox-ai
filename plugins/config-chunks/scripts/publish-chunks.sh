#!/usr/bin/env bash
# publish-chunks.sh — the config-chunks "registry interface".
#
# A contributing plugin ships a copy of THIS file plus a `chunks/` dir of
# template-conformant chunk files, and wires a SessionStart hook to run it:
#
#   { "type": "command", "command": "bash ${CLAUDE_PLUGIN_ROOT}/scripts/publish-chunks.sh" }
#
# It copies the plugin's own chunks into the shared drop dir, stamping a fresh
# mtime each session. The config-chunks reconciler picks them up from there.
# A plugin that is disabled/uninstalled stops re-publishing → its chunks go
# stale → the reconciler prunes them. That is how "uninstall = unsubscribe".
set -euo pipefail

# Engine home: CONFIG_CHUNKS_HOME (explicit override) > CLAUDE_PLUGIN_ROOT
# (Claude Code) > dirname fallback (run in place from a clone).
SRC="${CONFIG_CHUNKS_HOME:-${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}}/chunks"
DEST="$HOME/.claude/chunks/registered"

[ -d "$SRC" ] || exit 0
mkdir -p "$DEST"
shopt -s nullglob

# Parse a single frontmatter key from a chunk file (first occurrence).
fm_value() {
  awk -F': *' -v k="$1" '
    BEGIN { c = 0 }
    /^---[[:space:]]*$/ { c++; next }
    c == 1 && $1 == k { print $2; exit }
    c >= 2 { exit }
  ' "$2"
}

for f in "$SRC"/*.md; do
  name=$(fm_value name "$f")
  owner=$(fm_value owner "$f")
  if [ -z "$name" ] || [ -z "$owner" ]; then
    echo "config-chunks: skipping $(basename "$f") — missing name/owner frontmatter" >&2
    continue
  fi
  # Kebab-case only — forbids path separators and traversal in the dest path.
  kebab='^[a-z0-9]+(-[a-z0-9]+)*$'
  if [[ ! "$name" =~ $kebab ]] || [[ ! "$owner" =~ $kebab ]]; then
    echo "config-chunks: skipping $(basename "$f") — invalid name/owner (must be kebab-case)" >&2
    continue
  fi
  cp "$f" "$DEST/${owner}.${name}.md"
done
