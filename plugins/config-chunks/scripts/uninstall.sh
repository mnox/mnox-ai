#!/usr/bin/env bash
# uninstall.sh — strips the chunk sidecar and the managed marker block from
# every host instruction file the engine maintains.
#
# Run this when removing config-chunks. Because the bundle lives at a stable
# path OUTSIDE the plugin dir (~/.claude/chunks/), uninstalling the plugin
# alone would orphan it; this script cleans it up — the bundle, the stamp, the
# registered first-party chunk files, and the managed block in BOTH the
# CLAUDE.md (@import) and AGENTS.md (inlined) targets.
#
# NOTE: there is no documented plugin-uninstall hook event, so this is not
# wired into hooks.json — run it manually after uninstalling the plugin.
set -euo pipefail

OWNER="config-chunks"
CHUNKS_DIR="$HOME/.claude/chunks"
REG_DIR="$CHUNKS_DIR/registered"
BUNDLE="$CHUNKS_DIR/bundle.md"
STAMP="$CHUNKS_DIR/.sync-stamp"
CONFIG_YAML="$HOME/.claude/config/chunks.yaml"
CLAUDE_MD="$HOME/.claude/CLAUDE.md"

MARK_START="<!-- ${OWNER}:start -->"
MARK_END="<!-- ${OWNER}:end -->"

# --- resolve the AGENTS.md target the same way reconcile.sh does ---
# env override > config scalar (agents_path) > default. Leading ~ is expanded.
config_scalar() {
  awk -v field="$1" '
    $0 ~ ("^" field ":[[:space:]]*") {
      line=$0
      sub("^" field ":[[:space:]]*", "", line)
      sub(/[[:space:]]+#.*$/, "", line)
      gsub(/^[[:space:]'"'"'\"]+|[[:space:]'"'"'\"]+$/, "", line)
      print line; exit
    }
  ' "$2" 2>/dev/null
}
AGENTS_MD="${CONFIG_CHUNKS_AGENTS_MD:-}"
[ -n "$AGENTS_MD" ] || AGENTS_MD="$(config_scalar agents_path "$CONFIG_YAML")"
[ -n "$AGENTS_MD" ] || AGENTS_MD="$HOME/.claude/AGENTS.md"
AGENTS_MD="${AGENTS_MD/#\~/$HOME}"

# --- strip the managed marker block from a host file ---
# Same block-stripper reconcile.sh uses: an unmatched start marker only sheds
# the orphan marker line (buffered lines after it are preserved, never user
# instructions). Also drops the single blank separator line directly above the
# start marker, leaving the file byte-identical to pre-install.
strip_block() {
  local file="$1"
  [ -f "$file" ] || return 0
  local tmp
  tmp=$(mktemp)
  awk -v s="$MARK_START" -v e="$MARK_END" '
    $0==s {
      # Drop a single blank separator line buffered directly above the marker.
      if (pend && prev ~ /^[[:space:]]*$/) pend=0
      inblock=1; n=0; buf[++n]=$0; next
    }
    inblock {
      buf[++n]=$0
      if ($0==e) { inblock=0; n=0 }
      next
    }
    {
      if (pend) print prev
      prev=$0; pend=1
    }
    END {
      if (pend) print prev
      # Orphan-start-marker safety: shed only buf[1] (the start marker), keep
      # every buffered line after it.
      for (i=2; i<=n; i++) print buf[i]
    }
  ' "$file" > "$tmp" && mv "$tmp" "$file"
}

strip_block "$CLAUDE_MD"
strip_block "$AGENTS_MD"

# Remove the bundle, stamp, and first-party registered chunk files.
rm -f "$BUNDLE" "$STAMP"
shopt -s nullglob
for f in "$REG_DIR/$OWNER".*.md; do
  rm -f "$f"
done

# NOTE: ~/.claude/config/chunks.yaml (user opt-in) is intentionally NOT removed.
# It persists across uninstall/reinstall so the user's selections survive.
# NOTE: the chunks dir is NOT blown away wholesale — foreign-plugin registered
# chunks (owned by other installed plugins) must survive this uninstall.

echo "${OWNER}: removed bundle/stamp + ${OWNER}.* registered chunks, and stripped the managed block from ${CLAUDE_MD} and ${AGENTS_MD}." >&2
