#!/usr/bin/env bash
# reconcile.sh — assembles the agent-instruction chunk bundle from the shared
# drop dir and wires it into one or more host instruction files.
#
# Runs at SessionStart (Claude Code) or via any host's lifecycle. Boring and
# instant on the fast path: if the sync TTL has not expired AND the registered
# chunk set is byte-identical to last run AND every active target already holds
# its managed block, it exits in a few ms without rewriting anything.
#
# A full reconcile: prunes stale chunks (disabled/uninstalled plugins stop
# re-publishing → their files age out), dedups by `name` keeping the highest
# `version`, sorts by `order`, writes ~/.claude/chunks/bundle.md, and maintains
# a single marker-wrapped block in each active target:
#   - claude  → an @import line in CLAUDE.md (bundle loaded by reference).
#   - agents  → the bundle body INLINED in AGENTS.md (no @import support there).
#
# Targets come from ~/.claude/config/chunks.yaml (`targets:` block-list); with
# no targets key the script auto-detects (CLAUDE.md if it exists, AGENTS.md if
# it exists; neither → default to claude).
set -euo pipefail

CHUNKS_DIR="$HOME/.claude/chunks"
REG_DIR="$CHUNKS_DIR/registered"
BUNDLE="$CHUNKS_DIR/bundle.md"
STAMP="$CHUNKS_DIR/.sync-stamp"
CONFIG_YAML="$HOME/.claude/config/chunks.yaml"
CLAUDE_MD="$HOME/.claude/CLAUDE.md"

OWNER="config-chunks"

# Frequency governor: fast-path skip window when nothing changed.
SYNC_TTL=$(( 24 * 3600 ))
# Staleness governor: a chunk unrefreshed for this long is dropped from the
# bundle. Must comfortably exceed the largest realistic gap between sessions
# (vacations) so cross-plugin SessionStart hook-ordering lag never prunes a
# live chunk. 14 days covers a two-week absence; cost is that an uninstalled
# contributing plugin's chunk lingers up to 14 days before aging out.
PRUNE_TTL=$(( 14 * 24 * 3600 ))

# Body-size guardrails. The bundle is always-on context tax in every session,
# so each chunk has a soft char budget (~4 chars/token). The hard gate lives
# in the chunk-review skill at authoring time; reconcile only WARNS so a user's
# bundle is never silently mutilated.
#
#   INLINE_SOFT_CAP    — full-body chunks (disclosure: inline, the default).
#   POINTER_SOFT_CAP   — pointer chunks (disclosure: pointer). Tighter because
#                        the heavy content is supposed to live in the referenced
#                        skill, not in the always-on stub.
INLINE_SOFT_CAP=2000
POINTER_SOFT_CAP=400

MARK_START="<!-- ${OWNER}:start -->"
MARK_END="<!-- ${OWNER}:end -->"
IMPORT_LINE="@~/.claude/chunks/bundle.md"

# One plugin root, computed with the same fallback publish-chunks.sh uses, so
# the script is safe under `set -u` when CLAUDE_PLUGIN_ROOT is unset (manual or
# hook runs that don't export it).
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
GROUPS_DIR="$PLUGIN_ROOT/groups"

mkdir -p "$REG_DIR"
shopt -s nullglob
now=$(date +%s)

# Portable mtime (GNU first, then BSD/macOS).
mtime_of() { stat -c %Y "$1" 2>/dev/null || stat -f %m "$1"; }

# Parse a single frontmatter key from a chunk file (first occurrence).
fm_value() {
  awk -F': *' -v k="$1" '
    BEGIN { c = 0 }
    /^---[[:space:]]*$/ { c++; next }
    c == 1 && $1 == k { print $2; exit }
    c >= 2 { exit }
  ' "$2"
}

# ---------------------------------------------------------------------------
# YAML helpers (no yq dependency; BSD/macOS awk compatible).
#
# FORMAT REQUIREMENT: list fields MUST use block-list form. Inline-list form
# (e.g. "groups: [a, b]") is NOT supported — BSD awk does not support the
# 3-argument match() used for inline parsing. Always use block form:
#
#   groups:
#     - recommended
#   targets:
#     - claude
#     - agents
# ---------------------------------------------------------------------------

# parse_yaml_list FILE FIELD — reads a named top-level block-list field.
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

# config_scalar FIELD FILE — reads a top-level "field: value" scalar.
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

# --- resolve the AGENTS.md target path ---
# env override > config scalar (agents_path) > default. Leading ~ is expanded.
AGENTS_MD="${CONFIG_CHUNKS_AGENTS_MD:-}"
[ -n "$AGENTS_MD" ] || AGENTS_MD="$(config_scalar agents_path "$CONFIG_YAML")"
[ -n "$AGENTS_MD" ] || AGENTS_MD="$HOME/.claude/AGENTS.md"
AGENTS_MD="${AGENTS_MD/#\~/$HOME}"

# --- resolve active targets ---
# Explicit `targets:` list wins; otherwise auto-detect from existing files.
resolve_targets() {
  local t
  t=$(parse_yaml_list "$CONFIG_YAML" "targets" | tr '[:upper:]' '[:lower:]' | sort -u)
  if [ -n "$t" ]; then
    printf '%s\n' "$t"
    return
  fi
  local out=""
  [ -f "$CLAUDE_MD" ] && out="${out}claude"$'\n'
  [ -f "$AGENTS_MD" ] && out="${out}agents"$'\n'
  [ -n "$out" ] || out="claude"$'\n'
  printf '%s' "$out"
}
TARGETS=$(resolve_targets)
want_target() { grep -qxF "$1" <<< "$TARGETS"; }

# --- per-target managed-block presence checks (fast-path gate) ---
claude_block_ok() {
  [ -f "$CLAUDE_MD" ] || return 1
  grep -qF "$MARK_START" "$CLAUDE_MD" \
    && grep -qF "$IMPORT_LINE" "$CLAUDE_MD" \
    && grep -qF "$MARK_END" "$CLAUDE_MD"
}
agents_block_ok() {
  [ -f "$AGENTS_MD" ] || return 1
  grep -qF "$MARK_START" "$AGENTS_MD" && grep -qF "$MARK_END" "$AGENTS_MD"
}
targets_ok() {
  if want_target claude && ! claude_block_ok; then return 1; fi
  if want_target agents && ! agents_block_ok; then return 1; fi
  return 0
}

# --- set hash: registered chunks + opt-in config + group manifests + plugin chunks ---
set_hash=$( {
    cat "$REG_DIR"/*.md </dev/null 2>/dev/null || true
    cat "$CONFIG_YAML" 2>/dev/null || true
    cat "$PLUGIN_ROOT/groups/"*.yaml </dev/null 2>/dev/null || true
    cat "$PLUGIN_ROOT/chunks/"*.md </dev/null 2>/dev/null || true
} | shasum | awk '{print $1}')

# --- fast path: TTL not expired AND set unchanged AND all targets wired ---
if [ -f "$STAMP" ]; then
  last_sync=$(awk -F'=' '/^last_sync=/{print $2}' "$STAMP")
  prev_hash=$(awk -F'=' '/^set_hash=/{print $2}'  "$STAMP")
  if [ -n "${last_sync:-}" ] && [ "${prev_hash:-}" = "$set_hash" ] \
     && [ $(( now - last_sync )) -lt "$SYNC_TTL" ] && targets_ok; then
    exit 0
  fi
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# ---------------------------------------------------------------------------
# resolve_opt_in: parse chunks.yaml + groups/*.yaml into a sorted-unique slug
# set. Missing/empty config yields an empty slug set — plugin-owned chunks are
# skipped (fail-closed). Foreign-plugin chunks are unaffected.
# ---------------------------------------------------------------------------

# Auto-create config template on first run.
if [ ! -f "$CONFIG_YAML" ]; then
  mkdir -p "$(dirname "$CONFIG_YAML")"
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

# agents_path: the AGENTS.md file the `agents` target writes. REQUIRED on any
# non-Claude host — the fallback default (~/.claude/AGENTS.md) is read only by
# Claude Code; no other agent loads it. Point this at YOUR host's real file:
#   Codex   → ~/.codex/AGENTS.md
#   Cursor  → <your-project>/AGENTS.md
#   Gemini/Copilot/etc. → that host's AGENTS.md path
# agents_path: ~/.codex/AGENTS.md

# exclude: chunks to keep OUT of the bundle regardless of owner. The only lever
# over foreign-plugin chunks (otherwise always-on): run a plugin for its
# MCP/skills but drop its config-chunk. Match the registered basename
# `<owner>.<name>` or the bare `<name>`.
exclude:
  # - some-owner.some-chunk
YAML
fi

resolve_opt_in() {
  local config="$1" groups_dir="$2"
  local slug_set=""

  local wanted_groups wanted_chunks
  wanted_groups=$(parse_yaml_list "$config" "groups")
  wanted_chunks=$(parse_yaml_list "$config" "chunks")

  # Expand groups → slugs.
  while IFS= read -r group; do
    [ -n "$group" ] || continue
    local gfile="$groups_dir/$group.yaml"
    if [ ! -f "$gfile" ]; then
      echo "${OWNER}: WARNING: group '$group' not found at $gfile — skipping" >&2
      continue
    fi
    local group_slugs
    group_slugs=$(parse_yaml_list "$gfile" "chunks")
    while IFS= read -r slug; do
      [ -n "$slug" ] && slug_set="${slug_set}${slug}"$'\n'
    done <<< "$group_slugs"
  done <<< "$wanted_groups"

  # Append standalone chunks.
  while IFS= read -r slug; do
    [ -n "$slug" ] && slug_set="${slug_set}${slug}"$'\n'
  done <<< "$wanted_chunks"

  printf '%s' "$slug_set" | sort -u
}

ALLOWED_SLUGS=$(resolve_opt_in "$CONFIG_YAML" "$GROUPS_DIR")

# --- chunk opt-out list -----------------------------------------------------
# `exclude:` is a top-level block-list of chunks to keep OUT of the bundle,
# regardless of owner. It is the only lever over FOREIGN-plugin chunks (which
# are otherwise always-on pass-through): run a plugin for its MCP/skills but
# drop its config-chunk. Entries match the registered basename `<owner>.<name>`
# (e.g. exp-memory-graph.memory-graph-usage) OR the bare `<name>`.
EXCLUDED=$(parse_yaml_list "$CONFIG_YAML" "exclude" | sort -u)
is_excluded() {
  [ -n "$EXCLUDED" ] || return 1
  grep -qxF "$1" <<< "$EXCLUDED" 2>/dev/null
}

# Warn on opted-in slugs that match no registered first-party chunk (typo guard).
if [ -n "$ALLOWED_SLUGS" ]; then
  available_slugs=""
  for f in "$REG_DIR/$OWNER."*.md; do
    b=$(basename "$f" .md)
    available_slugs="${available_slugs}${b#$OWNER.}"$'\n'
  done
  while IFS= read -r slug; do
    [ -n "$slug" ] || continue
    grep -qxF "$slug" <<< "$available_slugs" 2>/dev/null \
      || echo "${OWNER}: WARNING: opted-in chunk '$slug' has no registered first-party chunk — skipping" >&2
  done <<< "$ALLOWED_SLUGS"
fi

# --- collect non-stale chunks: name <TAB> version <TAB> order <TAB> file ---
for f in "$REG_DIR"/*.md; do
  age=$(( now - $(mtime_of "$f") ))
  [ "$age" -gt "$PRUNE_TTL" ] && continue   # staleness prune

  # Determine owner from registered filename: <owner>.<name>.md
  base=$(basename "$f" .md)
  owner="${base%%.*}"

  # Explicit opt-out wins over everything (first-party or foreign).
  if is_excluded "$base" || is_excluded "${base#*.}"; then
    continue
  fi

  # Plugin-owned chunks are opt-in; gate them through the resolved slug set.
  if [ "$owner" = "$OWNER" ]; then
    slug="${base#*.}"
    if ! grep -qxF "$slug" <<< "$ALLOWED_SLUGS" 2>/dev/null; then
      continue   # not opted in; skip
    fi
  fi
  # Foreign-plugin chunks: pass through unchanged (existing behavior).

  name=$(fm_value name "$f")
  [ -n "$name" ] || continue
  ver=$(fm_value version "$f"); [ -n "$ver" ] || ver="0.0.0"
  ord=$(fm_value order "$f");   [ -n "$ord" ] || ord=100
  printf '%s\t%s\t%s\t%s\n' "$name" "$ver" "$ord" "$f" >> "$tmp/all"
done

# --- dedup by name, highest version wins; then sort by order, then name ---
: > "$tmp/winners"
if [ -f "$tmp/all" ]; then
  awk -F'\t' '
    function vcmp(a, b,   ah, al, bh, bl, an, bn, i, x, y, A, B) {
      an = index(a, "-"); ah = (an ? substr(a,1,an-1) : a); al = (an ? substr(a,an+1) : "")
      bn = index(b, "-"); bh = (bn ? substr(b,1,bn-1) : b); bl = (bn ? substr(b,bn+1) : "")
      x = split(ah, A, "."); y = split(bh, B, ".")
      for (i = 1; i <= 3; i++) {
        if ((A[i]+0) > (B[i]+0)) return 1
        if ((A[i]+0) < (B[i]+0)) return -1
      }
      if (al == "" && bl != "") return 1
      if (al != "" && bl == "") return -1
      if (al > bl) return 1
      if (al < bl) return -1
      return 0
    }
    {
      if (!($1 in best) || vcmp($2, bestver[$1]) > 0) {
        best[$1] = $0; bestver[$1] = $2
      }
    }
    END { for (n in best) print best[n] }
  ' "$tmp/all" > "$tmp/winners"
fi
sort -t"$(printf '\t')" -k3,3n -k1,1 "$tmp/winners" > "$tmp/ordered"

# Strip frontmatter and emit body bytes. Used for both rendering and sizing.
strip_frontmatter() {
  awk 'BEGIN{c=0} c<2 && /^---[[:space:]]*$/{c++; next} c>=2{print}' "$1"
}

# --- assemble the bundle (this plugin owns bundle.md wholesale) ---
{
  echo "<!-- GENERATED by ${OWNER} — do not edit by hand. -->"
  echo "<!-- Source of truth: ~/.claude/chunks/registered/  ·  Reconciled: $(date -u +%Y-%m-%dT%H:%M:%SZ) -->"
  echo
  while IFS=$'\t' read -r name ver ord file; do
    [ -n "$name" ] || continue
    disclosure=$(fm_value disclosure "$file")
    [ -n "$disclosure" ] || disclosure="inline"
    skill_ref=$(fm_value skill "$file")
    summary=$(fm_value summary "$file")

    echo "<!-- chunk: $name v$ver  ·  order=$ord  ·  disclosure=$disclosure  ·  $(basename "$file") -->"

    body_file="$tmp/body.$$"
    strip_frontmatter "$file" > "$body_file"
    body_bytes=$(wc -c < "$body_file" | tr -d ' ')

    if [ "$disclosure" = "pointer" ]; then
      # Compact always-on stub: heading + summary + body (rule only) + skill pointer.
      echo "## ${name}"
      [ -n "$summary" ] && echo "**${summary}**"
      echo
      cat "$body_file"
      if [ -n "$skill_ref" ]; then
        echo
        echo "→ For the full procedure, use the \`${skill_ref}\` skill."
      fi
      cap=$POINTER_SOFT_CAP
    else
      cat "$body_file"
      cap=$INLINE_SOFT_CAP
    fi
    rm -f "$body_file"
    echo

    if [ "$body_bytes" -gt "$cap" ]; then
      echo "${OWNER}: WARNING: chunk '$name' body is ${body_bytes} chars (cap: ${cap}, disclosure: ${disclosure}). Trim it, or split heavy content into a 'disclosure: pointer' chunk + skill." >&2
    fi
  done < "$tmp/ordered"
} > "$BUNDLE"

# ---------------------------------------------------------------------------
# write_managed_block FILE BODYFILE
# Ensures FILE holds exactly one marker-wrapped block whose contents are
# BODYFILE. Strips any pre-existing managed block first (an unmatched start
# marker only sheds the orphan marker line — every buffered line after it is
# preserved, never user instructions), then appends a clean block. Creates
# FILE (and its parent dir) if absent.
# ---------------------------------------------------------------------------
write_managed_block() {
  local file="$1" bodyfile="$2"
  if [ -f "$file" ]; then
    awk -v s="$MARK_START" -v e="$MARK_END" '
      $0==s { inblock=1; n=0; buf[++n]=$0; next }
      inblock {
        buf[++n]=$0
        if ($0==e) { inblock=0; n=0 }
        next
      }
      { print }
      END { for (i=2; i<=n; i++) print buf[i] }
    ' "$file" > "$tmp/mb" && mv "$tmp/mb" "$file"
    { printf '\n%s\n' "$MARK_START"; cat "$bodyfile"; printf '%s\n' "$MARK_END"; } >> "$file"
  else
    mkdir -p "$(dirname "$file")"
    { printf '%s\n' "$MARK_START"; cat "$bodyfile"; printf '%s\n' "$MARK_END"; } > "$file"
  fi
}

# --- maintain the managed block in each active target ---
# claude: a static @import line — only (re)written when missing/broken.
# agents: the inlined bundle body — refreshed on every slow-path run so the
#         inlined copy always tracks the freshly-assembled bundle.
if want_target claude; then
  printf '%s\n' "$IMPORT_LINE" > "$tmp/claude_body"
  if ! claude_block_ok; then
    write_managed_block "$CLAUDE_MD" "$tmp/claude_body"
  fi
fi
if want_target agents; then
  write_managed_block "$AGENTS_MD" "$BUNDLE"
fi

# --- record state ---
bundle_hash=$(shasum "$BUNDLE" | awk '{print $1}')
{
  echo "last_sync=$now"
  echo "set_hash=$set_hash"
  echo "bundle_hash=$bundle_hash"
} > "$STAMP"
