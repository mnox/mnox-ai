#!/usr/bin/env bash
# sync_skills.sh — render every templated skill under its profile and fan out
# to all three consumers, killing the hand-maintained 3-way drift:
#
#   repo plugin tree   ← render(public)      the canonical generic (commit + publish)
#   ~/.claude/skills    ← render(matt-local)  the personal tuned install
#   ~/.codex/skills     ← render(matt-local)  the Codex copy
#
# Safe by default: a skill is only pushed to ~/.claude or ~/.codex if it ALREADY
# exists there (refresh semantics — no surprise additions to a curated set).
# Pass --force to create missing targets. --dry-run shows the plan only.
#
# Usage: sync_skills.sh [--force] [--dry-run] [--profile-local NAME] [SKILL ...]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RENDER=(uv run --python 3.13 "$REPO_ROOT/scripts/render_skill.py")

PROFILE_PUBLIC="public"
PROFILE_LOCAL="matt-local"
CLAUDE_SKILLS="$HOME/.claude/skills"
CODEX_SKILLS="$HOME/.codex/skills"

FORCE=0
DRY=0
declare -a ONLY=()
while [ $# -gt 0 ]; do
  case "$1" in
    --force) FORCE=1 ;;
    --dry-run) DRY=1 ;;
    --profile-local) PROFILE_LOCAL="$2"; shift ;;
    --*) echo "unknown flag: $1" >&2; exit 2 ;;
    *) ONLY+=("$1") ;;
  esac
  shift
done

# Discover templated skills (those that have opted into the customization spine).
declare -a SKILL_DIRS=()
while IFS= read -r tmpl; do
  SKILL_DIRS+=("$(dirname "$tmpl")")
done < <(find "$REPO_ROOT"/plugins/*/skills/*/SKILL.md.tmpl 2>/dev/null | sort -u)

if [ ${#SKILL_DIRS[@]} -eq 0 ]; then
  echo "no templated skills found (plugins/*/skills/*/SKILL.md.tmpl)"; exit 0
fi

run() { if [ "$DRY" -eq 1 ]; then echo "    DRY: ${RENDER[*]} $*"; else "${RENDER[@]}" "$@"; fi; }

# Validate the whole corpus up front; abort before writing anything if drift exists.
echo "── validating templates against contracts ──"
"${RENDER[@]}" --all --profile "$PROFILE_PUBLIC" --check
"${RENDER[@]}" --all --profile "$PROFILE_LOCAL"  --check
echo ""

push_local() {  # <skill> <dest-root> <label>
  local skill="$1" root="$2" label="$3" dest="$2/$1"
  if [ -d "$dest" ] || [ "$FORCE" -eq 1 ]; then
    echo "  → $label: $dest"
    run --skill "$skill" --profile "$PROFILE_LOCAL" --dest "$dest"
  else
    echo "  ⤫ $label: $skill not present (skip; --force to add)"
  fi
}

for sd in "${SKILL_DIRS[@]}"; do
  skill="$(basename "$sd")"
  if [ ${#ONLY[@]} -gt 0 ] && [[ ! " ${ONLY[*]} " == *" $skill "* ]]; then continue; fi
  echo "══ $skill ══"
  echo "  → repo (public): $sd"
  run --skill "$skill" --profile "$PROFILE_PUBLIC" --dest "$sd"   # regenerate committed generic in place
  push_local "$skill" "$CLAUDE_SKILLS" "claude"
  push_local "$skill" "$CODEX_SKILLS"  "codex"
  echo ""
done

if [ "$DRY" -eq 1 ]; then echo "done (dry-run — nothing written)"; else echo "done."; fi
