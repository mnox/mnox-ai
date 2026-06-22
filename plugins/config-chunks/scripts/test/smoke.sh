#!/usr/bin/env bash
# smoke.sh — end-to-end smoke for chunks-config.sh + publish-chunks.sh +
# reconcile.sh, fully isolated under a temp HOME.
#
# Exercises the engine subcommands (including the new set-targets/add-target),
# then runs publish + reconcile against fabricated fixture chunks and asserts on
# the resulting bundle.md and on BOTH host instruction targets (claude @import,
# agents inlined). Also asserts the TTL+hash fast-path no-op, dedup-by-version,
# and staleness prune.
#
# Run from anywhere; resolves the plugin root via this script's location.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$HERE/../.." && pwd)"
ENGINE="$PLUGIN_ROOT/scripts/chunks-config.sh"
PUBLISH="$PLUGIN_ROOT/scripts/publish-chunks.sh"
RECONCILE="$PLUGIN_ROOT/scripts/reconcile.sh"

pass=0; fail=0
ok()   { printf '  \xe2\x9c\x93 %s\n' "$1"; pass=$((pass+1)); }
nope() { printf '  \xe2\x9c\x97 %s\n' "$1"; fail=$((fail+1)); }

assert_grep() {
  local needle="$1" file="$2" label="$3"
  if grep -qF "$needle" "$file" 2>/dev/null; then ok "$label"; else nope "$label (missing: $needle)"; fi
}
assert_nogrep() {
  local needle="$1" file="$2" label="$3"
  if grep -qF "$needle" "$file" 2>/dev/null; then nope "$label (found: $needle)"; else ok "$label"; fi
}

# Portable file hash.
hash_of() { shasum "$1" 2>/dev/null | awk '{print $1}'; }

TMP=$(mktemp -d)
export HOME="$TMP"
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"
# Pin the AGENTS.md target to a path under the temp HOME.
export CONFIG_CHUNKS_AGENTS_MD="$TMP/.config/AGENTS.md"
trap 'rm -rf "$TMP"' EXIT

CLAUDE_MD="$HOME/.claude/CLAUDE.md"
AGENTS_MD="$CONFIG_CHUNKS_AGENTS_MD"
CONFIG_YAML="$HOME/.claude/config/chunks.yaml"
REG_DIR="$HOME/.claude/chunks/registered"
BUNDLE="$HOME/.claude/chunks/bundle.md"
STAMP="$HOME/.claude/chunks/.sync-stamp"

# ---------------------------------------------------------------------------
echo "smoke: engine subcommands"
# ---------------------------------------------------------------------------

# Cold doctor creates the config file.
bash "$ENGINE" doctor >/dev/null 2>&1 || true
[ -f "$CONFIG_YAML" ] && ok "doctor creates chunks.yaml" || nope "doctor creates chunks.yaml"

# Add-chunk + idempotency.
out=$(bash "$ENGINE" add-chunk demo-inline)
[[ "$out" == *"added: chunks += demo-inline"* ]] && ok "add-chunk reports add" || nope "add-chunk reports add"
out=$(bash "$ENGINE" add-chunk demo-inline)
[[ "$out" == *"already subscribed"* ]] && ok "add-chunk idempotent" || nope "add-chunk idempotent"

# remove + toggle.
bash "$ENGINE" remove-chunk demo-inline >/dev/null
out=$(bash "$ENGINE" remove-chunk demo-inline)
[[ "$out" == *"not subscribed"* ]] && ok "remove-chunk idempotent" || nope "remove-chunk idempotent"
bash "$ENGINE" toggle-chunk demo-inline >/dev/null
toggled=$(awk '/^chunks:/{f=1;next} /^[^[:space:]-]/{f=0} f && /^[[:space:]]*-[[:space:]]/' "$CONFIG_YAML")
[[ "$toggled" == *"- demo-inline"* ]] && ok "toggle-chunk flips on" || nope "toggle-chunk flips on"

# --- new set-targets / add-target surface ---
out=$(bash "$ENGINE" set-targets claude agents)
[[ "$out" == *"set-targets: targets = claude agents"* ]] && ok "set-targets reports both" || nope "set-targets reports both"
tgt=$(awk '/^targets:/{f=1;next} /^[^[:space:]-]/{f=0} f && /^[[:space:]]*-[[:space:]]/' "$CONFIG_YAML")
if [[ "$tgt" == *"- claude"* ]] && [[ "$tgt" == *"- agents"* ]]; then
  ok "set-targets writes both block-list entries"
else
  nope "set-targets writes both block-list entries (got: $tgt)"
fi
# set-targets replaces (not appends): shrink to a single target.
bash "$ENGINE" set-targets claude >/dev/null
tgt=$(awk '/^targets:/{f=1;next} /^[^[:space:]-]/{f=0} f && /^[[:space:]]*-[[:space:]]/' "$CONFIG_YAML")
if [[ "$tgt" == *"- claude"* ]] && [[ "$tgt" != *"- agents"* ]]; then
  ok "set-targets replaces the whole list"
else
  nope "set-targets replaces the whole list (got: $tgt)"
fi
# add-target appends idempotently.
out=$(bash "$ENGINE" add-target agents)
[[ "$out" == *"added: targets += agents"* ]] && ok "add-target appends" || nope "add-target appends"
out=$(bash "$ENGINE" add-target agents)
[[ "$out" == *"already a target"* ]] && ok "add-target idempotent" || nope "add-target idempotent"
# Reject invalid target.
if bash "$ENGINE" set-targets bogus >/dev/null 2>&1; then
  nope "set-targets rejects invalid value"
else
  ok "set-targets rejects invalid value"
fi
if bash "$ENGINE" add-target bogus >/dev/null 2>&1; then
  nope "add-target rejects invalid value"
else
  ok "add-target rejects invalid value"
fi

# --- set-agents-path: scalar write + idempotent replace ---
bash "$ENGINE" set-agents-path "/tmp/host-a/AGENTS.md" >/dev/null
scalar=$(awk '/^agents_path:[[:space:]]*/{sub(/^agents_path:[[:space:]]*/,"");print;exit}' "$CONFIG_YAML")
[ "$scalar" = "/tmp/host-a/AGENTS.md" ] && ok "set-agents-path writes the scalar" \
  || nope "set-agents-path writes the scalar (got: $scalar)"
# Re-run with a different path: old value must be replaced, not duplicated.
bash "$ENGINE" set-agents-path "/tmp/host-b/AGENTS.md" >/dev/null
count=$(grep -c '^agents_path:' "$CONFIG_YAML")
scalar=$(awk '/^agents_path:[[:space:]]*/{sub(/^agents_path:[[:space:]]*/,"");print;exit}' "$CONFIG_YAML")
if [ "$count" -eq 1 ] && [ "$scalar" = "/tmp/host-b/AGENTS.md" ]; then
  ok "set-agents-path replaces (no duplicate scalar)"
else
  nope "set-agents-path replaces (count=$count, value=$scalar)"
fi
# Reject empty path.
if bash "$ENGINE" set-agents-path >/dev/null 2>&1; then
  nope "set-agents-path rejects missing path"
else
  ok "set-agents-path rejects missing path"
fi

# ---------------------------------------------------------------------------
echo "smoke: provider-agnostic reconcile (claude + agents)"
# ---------------------------------------------------------------------------

# Reset to a known config: opt into our fixtures, target BOTH hosts.
cat > "$CONFIG_YAML" <<YAML
groups:
chunks:
  - demo-inline
  - demo-pointer
targets:
  - claude
  - agents
agents_path: $AGENTS_MD
YAML

mkdir -p "$REG_DIR"

INLINE_MARKER="Validate every external payload at the trust boundary."
# Inline fixture.
cat > "$REG_DIR/config-chunks.demo-inline.md" <<EOF
---
name: demo-inline
version: 1.0.0
owner: config-chunks
order: 10
summary: Validate input at trust boundaries.
---

## Trust Boundary Validation

$INLINE_MARKER
EOF

# Pointer fixture.
cat > "$REG_DIR/config-chunks.demo-pointer.md" <<'EOF'
---
name: demo-pointer
version: 1.0.0
owner: config-chunks
order: 20
disclosure: pointer
skill: demo-procedure
summary: Prefer the safe path.
---

Always reach for the safe path before the clever one.
EOF

# Foreign-plugin fixture — owner is not config-chunks. Always-on regardless of
# opt-in.
FOREIGN_MARKER="This came from a foreign plugin and must be in the bundle unconditionally."
cat > "$REG_DIR/some-other-plugin.foreign-rule.md" <<EOF
---
name: foreign-rule
version: 1.0.0
owner: some-other-plugin
order: 15
summary: Foreign rule that should always render regardless of opt-in.
---

$FOREIGN_MARKER
EOF

# Run publish then reconcile.
bash "$PUBLISH" >/dev/null
bash "$RECONCILE" >/dev/null

# bundle.md exists and contains the expected chunk body text.
[ -f "$BUNDLE" ] && ok "bundle.md exists" || nope "bundle.md exists"
assert_grep "$INLINE_MARKER"  "$BUNDLE" "bundle contains inline chunk body"
assert_grep "## demo-pointer" "$BUNDLE" "bundle contains pointer heading"
assert_grep "$FOREIGN_MARKER" "$BUNDLE" "bundle contains foreign chunk (always-on)"

# CLAUDE.md target: marker block + @import line (NOT inlined body).
assert_grep "<!-- config-chunks:start -->"      "$CLAUDE_MD" "CLAUDE.md has marker block"
assert_grep "@~/.claude/chunks/bundle.md"       "$CLAUDE_MD" "CLAUDE.md has @import line"
assert_nogrep "$INLINE_MARKER"                  "$CLAUDE_MD" "CLAUDE.md does NOT inline bundle body"

# AGENTS.md target: marker block + INLINED bundle body (NOT @import).
assert_grep "<!-- config-chunks:start -->"      "$AGENTS_MD" "AGENTS.md has marker block"
assert_grep "$INLINE_MARKER"                    "$AGENTS_MD" "AGENTS.md inlines bundle body"
assert_nogrep "@~/.claude/chunks/bundle.md"     "$AGENTS_MD" "AGENTS.md does NOT use @import"

# ---------------------------------------------------------------------------
echo "smoke: fast-path no-op (TTL + hash)"
# ---------------------------------------------------------------------------
claude_before=$(hash_of "$CLAUDE_MD")
agents_before=$(hash_of "$AGENTS_MD")
bash "$RECONCILE" >/dev/null
claude_after=$(hash_of "$CLAUDE_MD")
agents_after=$(hash_of "$AGENTS_MD")
[ "$claude_before" = "$claude_after" ] && ok "CLAUDE.md byte-identical on fast-path re-run" \
  || nope "CLAUDE.md byte-identical on fast-path re-run"
[ "$agents_before" = "$agents_after" ] && ok "AGENTS.md byte-identical on fast-path re-run" \
  || nope "AGENTS.md byte-identical on fast-path re-run"

# ---------------------------------------------------------------------------
echo "smoke: dedup by version"
# ---------------------------------------------------------------------------
# Two registered files, same `name`, different `version`. Only the highest
# version's body must appear in the bundle. Opt the slug in.
bash "$ENGINE" add-chunk dupe >/dev/null 2>&1 || true
cat > "$REG_DIR/config-chunks.dupe.md" <<'EOF'
---
name: dupe
version: 1.0.0
owner: config-chunks
order: 40
summary: dupe v1.
---

DUPE_BODY_V1_OLD
EOF
cat > "$REG_DIR/config-chunks.dupe-hi.md" <<'EOF'
---
name: dupe
version: 2.0.0
owner: config-chunks
order: 40
summary: dupe v2.
---

DUPE_BODY_V2_NEW
EOF
# NOTE: both files publish the same `name: dupe`; the slug opted in is `dupe`,
# and the reconciler gates first-party by the registered filename slug. The
# higher-version file's stem (dupe-hi) is not opted in, so to test dedup purely
# we register both under the opted-in slug by colliding on `name`. Reconcile
# gates on filename slug for first-party; align both filenames' slugs to `dupe`
# is impossible (unique paths), so opt in both slugs.
bash "$ENGINE" add-chunk dupe-hi >/dev/null 2>&1 || true
rm -f "$STAMP"
bash "$RECONCILE" >/dev/null
assert_grep   "DUPE_BODY_V2_NEW" "$BUNDLE" "dedup keeps highest version body"
assert_nogrep "DUPE_BODY_V1_OLD" "$BUNDLE" "dedup drops lower version body"

# ---------------------------------------------------------------------------
echo "smoke: staleness prune (>14 days)"
# ---------------------------------------------------------------------------
bash "$ENGINE" add-chunk stale-demo >/dev/null 2>&1 || true
cat > "$REG_DIR/config-chunks.stale-demo.md" <<'EOF'
---
name: stale-demo
version: 1.0.0
owner: config-chunks
order: 50
summary: stale demo.
---

STALE_DEMO_BODY_SHOULD_AGE_OUT
EOF
# Backdate mtime > 14 days. GNU touch -d first, BSD touch -t fallback.
backdated=0
if touch -d "30 days ago" "$REG_DIR/config-chunks.stale-demo.md" 2>/dev/null; then
  backdated=1
else
  # BSD: compute a yyyymmddHHMM ~30 days back.
  if old=$(date -v-30d +%Y%m%d%H%M 2>/dev/null); then
    touch -t "$old" "$REG_DIR/config-chunks.stale-demo.md" 2>/dev/null && backdated=1
  fi
fi
rm -f "$STAMP"
bash "$RECONCILE" >/dev/null
if [ "$backdated" -eq 1 ]; then
  assert_nogrep "STALE_DEMO_BODY_SHOULD_AGE_OUT" "$BUNDLE" "stale (>14d) chunk pruned from bundle"
else
  echo "  ! skipped staleness prune assert — no portable backdating available on this platform"
fi

# ---------------------------------------------------------------------------
echo
echo "smoke: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
