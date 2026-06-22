#!/usr/bin/env bash
# chunks-config.sh — one-liner toggle + doctor for ~/.claude/config/chunks.yaml.
#
# Usage:
#   chunks-config.sh list
#   chunks-config.sh doctor
#   chunks-config.sh add-group    <name>
#   chunks-config.sh remove-group <name>
#   chunks-config.sh toggle-group <name>
#   chunks-config.sh add-chunk    <slug>
#   chunks-config.sh remove-chunk <slug>
#   chunks-config.sh toggle-chunk <slug>
#   chunks-config.sh add-exclude    <owner.name|name>
#   chunks-config.sh remove-exclude <owner.name|name>
#   chunks-config.sh toggle-exclude <owner.name|name>
#   chunks-config.sh add-target   <claude|agents>
#   chunks-config.sh set-targets  <claude|agents>...
#   chunks-config.sh set-agents-path <path>   # AGENTS.md file the `agents` target writes
#
# After any mutation the reconciler runs so the change lands in bundle.md
# immediately — no need to restart the session.
#
# Block-form YAML only (matches reconcile.sh's BSD-awk parser). Idempotent:
# adding what's already there is a no-op, removing what's absent is a no-op.
set -euo pipefail

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
CONFIG_DIR="$HOME/.claude/config"
CONFIG_YAML="$CONFIG_DIR/chunks.yaml"
GROUPS_DIR="$PLUGIN_ROOT/groups"
CHUNKS_SRC_DIR="$PLUGIN_ROOT/chunks"
REG_DIR="$HOME/.claude/chunks/registered"
RECONCILE="$PLUGIN_ROOT/scripts/reconcile.sh"
PUBLISH="$PLUGIN_ROOT/scripts/publish-chunks.sh"

OWNER="config-chunks"

# One process-scoped scratch dir; every helper's temp file lives under it so a
# single EXIT trap reaps them all on any exit path (success, error, or `exit N`).
# Matches reconcile.sh / smoke.sh — avoids per-function cleanup, which a RETURN
# trap can't do safely here (bash's RETURN trap is global and dynamically scoped,
# so it leaks into callers and trips `set -u`).
WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT

# Skeleton kept byte-identical to reconcile.sh's auto-create so the two paths
# never produce drifting templates.
write_skeleton() {
  mkdir -p "$CONFIG_DIR"
  cat > "$CONFIG_YAML" <<'YAML'
# ~/.claude/config/chunks.yaml
# Add group names to opt into all chunks they contain.
# Add individual chunk slugs to opt into a single chunk directly.
# Empty lists = foreign-plugin chunks only (same as pre-groups behavior).
#
# IMPORTANT: use block-list form only. Inline form (e.g. groups: [recommended])
# is NOT supported on macOS BSD awk.
groups:
  # - recommended
chunks:
  # - some-slug

# targets: which host instruction files to maintain. Omit to auto-detect
# (CLAUDE.md if present, AGENTS.md if present). Pin explicitly to force one:
#   - claude  → @import line in ~/.claude/CLAUDE.md
#   - agents  → bundle body inlined in the AGENTS.md target
targets:
  # - claude
  # - agents

# agents_path: override the AGENTS.md file the `agents` target writes.
# Defaults to ~/.claude/AGENTS.md. Example: ~/.codex/AGENTS.md
# agents_path: ~/.claude/AGENTS.md

# exclude: chunks to keep OUT of the bundle regardless of owner. The only lever
# over foreign-plugin chunks (otherwise always-on): run a plugin for its
# MCP/skills but drop its config-chunk. Match the registered basename
# `<owner>.<name>` or the bare `<name>`.
exclude:
  # - some-owner.some-chunk
YAML
}

ensure_config() {
  [ -f "$CONFIG_YAML" ] || write_skeleton
}

# Read frontmatter `name:` value from a chunk file (BSD-awk safe).
fm_name() {
  awk -F': *' '
    BEGIN { c = 0 }
    /^---[[:space:]]*$/ { c++; next }
    c == 1 && $1 == "name" { print $2; exit }
    c >= 2 { exit }
  ' "$1"
}

# parse_yaml_list FILE KEY — block-form only, identical algorithm to reconcile.sh.
parse_yaml_list() {
  awk -v field="$2" '
    BEGIN { found=0 }
    $0 ~ ("^" field ":") { found=1; next }
    found==1 && /^[[:space:]]*-[[:space:]]/ {
      item=$0
      gsub(/^[[:space:]]*-[[:space:]]+/, "", item)
      sub(/[[:space:]]+#.*$/, "", item)
      gsub(/^[[:space:]'"'"'\"]+|[[:space:]'"'"'\"]+$/, "", item)
      if (item != "") print item
      next
    }
    found==1 && /^[^[:space:]-]/ { found=2 }
    found==2 { next }
  ' "$1" 2>/dev/null
}

# Detect the dangerous BSD-awk-incompatible inline form: `key: [a, b]`.
# Returns 0 if any inline-form list is found anywhere in the config.
has_inline_form() {
  grep -E '^[a-zA-Z_][a-zA-Z0-9_]*:[[:space:]]*\[' "$CONFIG_YAML" >/dev/null 2>&1
}

available_groups() {
  shopt -s nullglob
  local f
  for f in "$GROUPS_DIR"/*.yaml; do
    basename "$f" .yaml
  done | sort -u
}

available_plugin_chunks() {
  shopt -s nullglob
  local f n
  for f in "$CHUNKS_SRC_DIR"/*.md; do
    n=$(fm_name "$f")
    [ -n "$n" ] && echo "$n"
  done | sort -u
}

# Foreign-plugin chunks visible in the registered drop dir (everything not owned
# by config-chunks). These are always-on; you can't toggle them from here.
foreign_registered_chunks() {
  shopt -s nullglob
  local f base
  for f in "$REG_DIR"/*.md; do
    base=$(basename "$f" .md)
    case "$base" in
      "$OWNER".*) ;;
      *) echo "$base" ;;
    esac
  done | sort -u
}

# resolve_slugs: same expansion the reconciler does, used by `list` and `doctor`.
resolve_slugs() {
  ensure_config
  local out=""
  local g s
  while IFS= read -r g; do
    [ -n "$g" ] || continue
    local gfile="$GROUPS_DIR/$g.yaml"
    if [ -f "$gfile" ]; then
      while IFS= read -r s; do
        [ -n "$s" ] && out="${out}${s}"$'\n'
      done < <(parse_yaml_list "$gfile" "chunks")
    fi
  done < <(parse_yaml_list "$CONFIG_YAML" "groups")
  while IFS= read -r s; do
    [ -n "$s" ] && out="${out}${s}"$'\n'
  done < <(parse_yaml_list "$CONFIG_YAML" "chunks")
  printf '%s' "$out" | awk 'NF' | sort -u
}

is_present() {
  parse_yaml_list "$CONFIG_YAML" "$1" | grep -qxF "$2"
}

# Ensure a top-level `key:` exists in chunks.yaml (so add can find it). If the
# key is missing entirely, append it. Block-form only.
ensure_key() {
  local key="$1"
  if ! grep -qE "^${key}:" "$CONFIG_YAML"; then
    printf '\n%s:\n' "$key" >> "$CONFIG_YAML"
  fi
}

# Convert `key: []` (or `key: [ ]`) to bare `key:` block form so the insertion
# path below produces valid YAML. Without this, adding to an inline-empty list
# yields `key: []` followed by an indented `- item` — our BSD-awk parser is
# permissive enough to still extract the item, but any stricter YAML consumer
# would reject the file.
normalize_empty_inline_for_key() {
  local key="$1"
  local tmp
  tmp=$(mktemp "$WORKDIR/XXXXXX")
  awk -v key="$key" '
    {
      # Tolerate a trailing comment (e.g. `groups: []  # none yet`) so users
      # who annotated the documented inline-empty form still get normalized.
      pat = "^" key ":[[:space:]]*\\[[[:space:]]*\\][[:space:]]*(#.*)?$"
      if ($0 ~ pat) print key ":"; else print
    }
  ' "$CONFIG_YAML" > "$tmp" && mv "$tmp" "$CONFIG_YAML"
}

# True if `key:` is in non-empty inline form (e.g. `key: [a, b]`). Mutations
# refuse to operate on this form — we won't try to merge into something the
# reconciler can't parse to begin with.
has_nonempty_inline_for_key() {
  local key="$1"
  awk -v key="$key" '
    {
      pat = "^" key ":[[:space:]]*\\[[[:space:]]*[^][:space:]]"
      if ($0 ~ pat) { found=1; exit }
    }
    END { exit (found ? 0 : 1) }
  ' "$CONFIG_YAML"
}

# Refuse mutation if the target key is in non-empty inline form. Caller should
# treat non-zero as "abort and tell the user to run doctor." Empty inline form
# is auto-normalized to block form (the documented `groups: []` placeholder).
guard_and_normalize_key() {
  local key="$1"
  if has_nonempty_inline_for_key "$key"; then
    cat >&2 <<EOF
config-chunks: refusing mutation — '$key' is in inline-list form
  (e.g. \`$key: [a, b]\`). The reconciler's BSD-awk parser doesn't accept
  this form. Run \`$(basename "$0") doctor\` and convert it to block-list:

      $key:
        - some-slug

EOF
    return 2
  fi
  normalize_empty_inline_for_key "$key"
}

# Add `- item` to the block list under `key`. Inserts after the last existing
# list item under `key` (or directly after the key line if none). Preserves
# leading commented placeholders (`# - some-slug`) since those don't parse as
# real items.
add_item() {
  local key="$1" item="$2"
  ensure_config
  ensure_key "$key"
  guard_and_normalize_key "$key" || return $?
  if is_present "$key" "$item"; then
    return 1   # already present — caller treats as no-op
  fi
  local tmp
  tmp=$(mktemp "$WORKDIR/XXXXXX")
  awk -v key="$key" -v item="$item" '
    BEGIN { in_key=0; emitted=0; last_dash_line=0 }
    {
      lines[NR]=$0
      if ($0 ~ ("^" key ":")) { in_key=1; key_line=NR; next_check=1; next }
      if (in_key) {
        if ($0 ~ /^[[:space:]]*-[[:space:]]/) { last_dash_line=NR }
        else if ($0 ~ /^[^[:space:]#-]/) { in_key=0 }
      }
    }
    END {
      insert_after = (last_dash_line > 0 ? last_dash_line : key_line)
      for (i = 1; i <= NR; i++) {
        print lines[i]
        if (i == insert_after) print "  - " item
      }
    }
  ' "$CONFIG_YAML" > "$tmp" && mv "$tmp" "$CONFIG_YAML"
  return 0
}

remove_item() {
  local key="$1" item="$2"
  ensure_config
  guard_and_normalize_key "$key" || return $?
  if ! is_present "$key" "$item"; then
    return 1   # not present — caller treats as no-op
  fi
  local tmp
  tmp=$(mktemp "$WORKDIR/XXXXXX")
  awk -v key="$key" -v item="$item" '
    BEGIN { in_key=0 }
    {
      if ($0 ~ ("^" key ":")) { in_key=1; print; next }
      if (in_key) {
        if ($0 ~ /^[[:space:]]*-[[:space:]]/) {
          stripped=$0
          gsub(/^[[:space:]]*-[[:space:]]+/, "", stripped)
          sub(/[[:space:]]+#.*$/, "", stripped)
          gsub(/^[[:space:]'"'"'\"]+|[[:space:]'"'"'\"]+$/, "", stripped)
          if (stripped == item) { next }   # drop this line
        } else if ($0 ~ /^[^[:space:]#-]/) { in_key=0 }
      }
      print
    }
  ' "$CONFIG_YAML" > "$tmp" && mv "$tmp" "$CONFIG_YAML"
  return 0
}

run_publish_quiet() {
  [ -f "$PUBLISH" ] || return 0
  bash "$PUBLISH" >/dev/null 2>&1 || \
    echo "config-chunks: warning — publish-chunks.sh exited non-zero; re-run manually to see errors" >&2
}

run_reconcile_quiet() {
  [ -f "$RECONCILE" ] || return 0
  bash "$RECONCILE" >/dev/null 2>&1 || \
    echo "config-chunks: warning — reconcile.sh exited non-zero; re-run manually to see errors" >&2
}

# After any mutation: publish first-party chunks to registered/, then reconcile.
# Self-contained so toggling on a fresh install actually lands the chunk in the
# bundle without waiting for SessionStart.
publish_then_reconcile() {
  run_publish_quiet
  run_reconcile_quiet
}

# --- targets: validation + block rewrite -----------------------------------
# `targets:` is a top-level block-list whose only legal values are `claude` and
# `agents`. Unlike groups/chunks (free-form slugs), targets are a closed set, so
# add-target/set-targets validate each value before writing.

valid_target() {
  case "$1" in
    claude|agents) return 0 ;;
    *) return 1 ;;
  esac
}

# Rewrite the entire top-level `targets:` block-list to exactly the given values
# (block form, one `  - value` per line). Creates the key if absent, replaces
# the whole list if present. Mirrors remove_item's in-key scan for the boundary.
#
# Two-step to stay BSD-awk-safe (awk -v cannot carry literal newlines): first
# strip the old list with awk emitting a sentinel right after the header, then
# splice the fresh `  - value` lines in at the sentinel with a plain shell loop.
set_targets_block() {
  ensure_config
  guard_and_normalize_key "targets" || return $?
  ensure_key "targets"
  local tmp out sentinel="__CONFIG_CHUNKS_TARGETS_SENTINEL__"
  tmp=$(mktemp "$WORKDIR/XXXXXX")
  awk -v key="targets" -v sentinel="$sentinel" '
    BEGIN { in_key=0 }
    {
      if ($0 ~ ("^" key ":")) {
        in_key=1
        print            # keep the `targets:` header line
        print sentinel   # mark where the fresh list is spliced in
        next
      }
      if (in_key) {
        # Drop every old block-list item line under the key...
        if ($0 ~ /^[[:space:]]*-[[:space:]]/) { next }
        # ...drop in-block comment placeholders too...
        else if ($0 ~ /^[[:space:]]*#/) { next }
        # ...until the next top-level key (or blank line) ends the block.
        else { in_key=0 }
      }
      print
    }
  ' "$CONFIG_YAML" > "$tmp"

  out=$(mktemp "$WORKDIR/XXXXXX")
  while IFS= read -r line; do
    if [ "$line" = "$sentinel" ]; then
      local t
      for t in "$@"; do printf '  - %s\n' "$t"; done
    else
      printf '%s\n' "$line"
    fi
  done < "$tmp" > "$out"
  mv "$out" "$CONFIG_YAML"
  return 0
}

cmd_set_targets() {
  local t
  for t in "$@"; do
    if ! valid_target "$t"; then
      echo "config-chunks: invalid target '$t' — must be 'claude' or 'agents'" >&2
      exit 2
    fi
  done
  # Dedup while preserving order.
  local seen="" uniq=()
  for t in "$@"; do
    case "$seen" in *"|$t|"*) continue ;; esac
    seen="${seen}|$t|"
    uniq+=("$t")
  done
  set_targets_block "${uniq[@]}" || exit $?
  echo "set-targets: targets = ${uniq[*]}"
  publish_then_reconcile
}

cmd_add_target() {
  local item="$1"
  if ! valid_target "$item"; then
    echo "config-chunks: invalid target '$item' — must be 'claude' or 'agents'" >&2
    exit 2
  fi
  if add_item "targets" "$item"; then
    echo "added: targets += $item"
    publish_then_reconcile
  else
    rc=$?
    case "$rc" in
      1) echo "already a target: targets has $item" ;;
      *) exit "$rc" ;;
    esac
  fi
}

# --- agents_path: set the AGENTS.md file the `agents` target writes ----------
# A top-level scalar (not a block-list), REQUIRED on non-Claude hosts — the
# fallback (~/.claude/AGENTS.md) is read only by Claude Code. Idempotent: strips
# any existing real `agents_path:` line, then appends the fresh value. The
# commented skeleton line (`# agents_path:`) is left untouched — config_scalar
# skips comments, so it never shadows the real value.
cmd_set_agents_path() {
  local path="$1"
  if [ -z "$path" ]; then
    echo "config-chunks: set-agents-path needs a non-empty path" >&2
    exit 2
  fi
  ensure_config
  local tmp
  tmp=$(mktemp "$WORKDIR/XXXXXX")
  # Drop any existing uncommented agents_path line; keep everything else.
  awk '!/^agents_path:[[:space:]]*/' "$CONFIG_YAML" > "$tmp"
  printf 'agents_path: %s\n' "$path" >> "$tmp"
  mv "$tmp" "$CONFIG_YAML"
  echo "set-agents-path: agents_path = $path"
  publish_then_reconcile
}

cmd_list() {
  ensure_config
  echo "config: $CONFIG_YAML"
  echo
  echo "Subscribed groups:"
  local any=0 g
  while IFS= read -r g; do
    [ -n "$g" ] || continue
    any=1
    local gfile="$GROUPS_DIR/$g.yaml"
    if [ -f "$gfile" ]; then
      local members
      members=$(parse_yaml_list "$gfile" "chunks" | paste -sd ', ' -)
      echo "  - $g → ${members:-(empty)}"
    else
      echo "  - $g (UNKNOWN — no group file at $gfile)"
    fi
  done < <(parse_yaml_list "$CONFIG_YAML" "groups")
  [ "$any" -eq 1 ] || echo "  (none)"
  echo
  echo "Standalone chunks:"
  any=0
  local s
  while IFS= read -r s; do
    [ -n "$s" ] || continue
    any=1
    echo "  - $s"
  done < <(parse_yaml_list "$CONFIG_YAML" "chunks")
  [ "$any" -eq 1 ] || echo "  (none)"
  echo
  echo "Excluded chunks (kept out of the bundle, any owner):"
  any=0
  local x
  while IFS= read -r x; do
    [ -n "$x" ] || continue
    any=1
    echo "  - $x"
  done < <(parse_yaml_list "$CONFIG_YAML" "exclude")
  [ "$any" -eq 1 ] || echo "  (none)"
  echo
  echo "Active targets:"
  any=0
  local t
  while IFS= read -r t; do
    [ -n "$t" ] || continue
    any=1
    echo "  - $t"
  done < <(parse_yaml_list "$CONFIG_YAML" "targets")
  [ "$any" -eq 1 ] || echo "  (none — auto-detect: CLAUDE.md/AGENTS.md if present, else claude)"
  echo
  echo "Resolved slug set (first-party, opted-in):"
  local resolved
  resolved=$(resolve_slugs)
  if [ -n "$resolved" ]; then
    echo "$resolved" | sed 's/^/  - /'
  else
    echo "  (none)"
  fi
  echo
  echo "Available plugin groups:"
  local avail
  avail=$(available_groups)
  if [ -n "$avail" ]; then echo "$avail" | sed 's/^/  - /'; else echo "  (none)"; fi
  echo
  echo "Available plugin chunks:"
  avail=$(available_plugin_chunks)
  if [ -n "$avail" ]; then echo "$avail" | sed 's/^/  - /'; else echo "  (none)"; fi
  echo
  echo "Foreign-plugin chunks in your bundle (always-on, not togglable here):"
  local excludes
  excludes=$(parse_yaml_list "$CONFIG_YAML" "exclude")
  any=0
  local fc
  while IFS= read -r fc; do
    [ -n "$fc" ] || continue
    # Skip any foreign chunk that's excluded (match owner.name or bare name).
    if grep -qxF "$fc" <<< "$excludes" 2>/dev/null \
       || grep -qxF "${fc#*.}" <<< "$excludes" 2>/dev/null; then
      continue
    fi
    any=1
    echo "  - $fc"
  done < <(foreign_registered_chunks)
  [ "$any" -eq 1 ] || echo "  (none)"
}

cmd_doctor() {
  local status=0
  echo "config-chunks doctor"
  echo "--------------------"

  if [ ! -f "$CONFIG_YAML" ]; then
    write_skeleton
    echo "✓ created $CONFIG_YAML (was missing)"
  else
    echo "✓ config present: $CONFIG_YAML"
  fi

  if has_inline_form; then
    echo "✗ inline list form detected (e.g. \`groups: [...]\`) — BSD awk silently parses these to empty."
    echo "  Fix: convert to block form:"
    echo "      groups:"
    echo "        - recommended"
    status=1
  else
    echo "✓ no inline-form footgun"
  fi

  # Validate targets: only claude/agents are legal values.
  local t
  while IFS= read -r t; do
    [ -n "$t" ] || continue
    if ! valid_target "$t"; then
      echo "✗ invalid target '$t' in chunks.yaml — must be 'claude' or 'agents'"
      status=1
    fi
  done < <(parse_yaml_list "$CONFIG_YAML" "targets")

  local avail_g avail_c
  avail_g=$(available_groups)
  avail_c=$(available_plugin_chunks)

  local g
  while IFS= read -r g; do
    [ -n "$g" ] || continue
    if ! grep -qxF "$g" <<< "$avail_g"; then
      echo "✗ subscribed group '$g' has no group file at $GROUPS_DIR/$g.yaml"
      status=1
    fi
  done < <(parse_yaml_list "$CONFIG_YAML" "groups")

  local s
  while IFS= read -r s; do
    [ -n "$s" ] || continue
    if ! grep -qxF "$s" <<< "$avail_c"; then
      echo "✗ subscribed standalone chunk '$s' matches no plugin chunk in $CHUNKS_SRC_DIR/"
      status=1
    fi
  done < <(parse_yaml_list "$CONFIG_YAML" "chunks")

  if [ ! -d "$REG_DIR" ]; then
    echo "⚠ $REG_DIR does not exist yet — start a new session so publish-chunks.sh can drop files there."
  else
    echo "✓ drop dir present: $REG_DIR"
    # Flag subscribed first-party slugs that aren't yet in registered/. This is
    # the "I subscribed but the bundle is empty" gotcha: the engine now
    # auto-publishes after mutations, but a config edited externally can leave
    # subscriptions with no matching published file until the next session.
    local resolved s
    resolved=$(resolve_slugs)
    while IFS= read -r s; do
      [ -n "$s" ] || continue
      if [ ! -f "$REG_DIR/$OWNER.$s.md" ]; then
        echo "✗ subscribed first-party slug '$s' is not yet published to $REG_DIR/$OWNER.$s.md"
        echo "  Fix: run \`bash \$CLAUDE_PLUGIN_ROOT/scripts/publish-chunks.sh\` (the engine does this automatically after every toggle)."
        status=1
      fi
    done <<< "$resolved"
  fi

  if [ "$status" -eq 0 ]; then
    echo
    echo "All checks passed."
  else
    echo
    echo "Doctor found issues — see above."
  fi
  return $status
}

mutate_then_reconcile() {
  local verb="$1" key="$2" item="$3"
  case "$verb" in
    add)
      if add_item "$key" "$item"; then rc=0; else rc=$?; fi
      case "$rc" in
        0) echo "added: $key += $item";  publish_then_reconcile ;;
        1) echo "already subscribed: $key has $item" ;;
        *) exit "$rc" ;;
      esac
      ;;
    remove)
      if remove_item "$key" "$item"; then rc=0; else rc=$?; fi
      case "$rc" in
        0) echo "removed: $key -= $item"; publish_then_reconcile ;;
        1) echo "not subscribed: $key does not contain $item" ;;
        *) exit "$rc" ;;
      esac
      ;;
    toggle)
      # Run the guard once up front so non-empty inline form aborts cleanly
      # before flipping anything.
      guard_and_normalize_key "$key" || exit $?
      if is_present "$key" "$item"; then
        remove_item "$key" "$item"
        echo "removed: $key -= $item"
      else
        add_item "$key" "$item"
        echo "added: $key += $item"
      fi
      publish_then_reconcile
      ;;
  esac
}

usage() {
  sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//'
}

main() {
  local cmd="${1:-}"; shift || true
  case "$cmd" in
    list)          cmd_list ;;
    doctor)        cmd_doctor ;;
    add-group)     [ $# -eq 1 ] || { usage; exit 2; }; mutate_then_reconcile add    groups "$1" ;;
    remove-group)  [ $# -eq 1 ] || { usage; exit 2; }; mutate_then_reconcile remove groups "$1" ;;
    toggle-group)  [ $# -eq 1 ] || { usage; exit 2; }; mutate_then_reconcile toggle groups "$1" ;;
    add-chunk)     [ $# -eq 1 ] || { usage; exit 2; }; mutate_then_reconcile add    chunks "$1" ;;
    remove-chunk)  [ $# -eq 1 ] || { usage; exit 2; }; mutate_then_reconcile remove chunks "$1" ;;
    toggle-chunk)  [ $# -eq 1 ] || { usage; exit 2; }; mutate_then_reconcile toggle chunks "$1" ;;
    add-exclude)   [ $# -eq 1 ] || { usage; exit 2; }; mutate_then_reconcile add    exclude "$1" ;;
    remove-exclude)[ $# -eq 1 ] || { usage; exit 2; }; mutate_then_reconcile remove exclude "$1" ;;
    toggle-exclude)[ $# -eq 1 ] || { usage; exit 2; }; mutate_then_reconcile toggle exclude "$1" ;;
    add-target)    [ $# -eq 1 ] || { usage; exit 2; }; cmd_add_target "$1" ;;
    set-targets)   [ $# -ge 1 ] || { usage; exit 2; }; cmd_set_targets "$@" ;;
    set-agents-path) [ $# -eq 1 ] || { usage; exit 2; }; cmd_set_agents_path "$1" ;;
    ""|-h|--help|help) usage ;;
    *) echo "unknown command: $cmd" >&2; usage; exit 2 ;;
  esac
}

main "$@"
