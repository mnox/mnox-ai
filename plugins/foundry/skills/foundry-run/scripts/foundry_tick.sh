#!/usr/bin/env bash
# foundry_tick.sh — deterministic state engine for Foundry V0
#
# REPO-AGNOSTIC: the target repo is a profile in repos.json, selected via
# FOUNDRY_REPO env or `init --repo <key>` (default: example). The profile
# supplies repo_dir, findings_dir, worktrees_base, branch_prefix, base,
# setup_cmd, verifier_cmd, and unit_glob — so the engine drives any
# repo/toolchain and any bucket of work-unit contracts (findings are one flavor).
#
# WORK-UNIT CONTRACT: each unit is a `<id>.md` file (matched by the profile's
# unit_glob) with required frontmatter `id` / `title` / `status` and a required
# `## Acceptance Criteria` body section (the Worker's target + Integrator's
# rubric). See unit-contract.md. `validate` lints a bucket against this contract.
#
# SUBCOMMANDS & KEY=value OUTPUT CONTRACT
# ─────────────────────────────────────────────────────────────────────────────
# init [--date YYYYMMDD] [--repo <key>]
#   Ensures bucket branch exists, cut from the profile's `base`. Idempotent.
#   stdout: REPO=<key>  BUCKET=<branch_prefix>-<date>
#
# validate
#   PURE READ preflight. Lints every claimable unit against the work-unit
#   contract (required keys + non-empty Acceptance Criteria; warns on
#   out-of-order depends_on). stdout: VALIDATE=ok|fail|empty. Exit 4 on fail.
#
# next
#   PURE READ. Scans all units (unit_glob), emits one ACTION block:
#     ACTION=integrate  UNIT=<id>  BRANCH=<branch>  WORKTREE=<path>   (agent-code-complete, oldest-updated first)
#     ACTION=implement  UNIT=<id>                                      (open + eligible, lowest lex UNIT-ID first)
#     ACTION=drained
#
# claim <UNIT-ID>
#   open → in-progress, creates worktree off BUCKET TIP, runs the profile setup_cmd.
#   stdout: BRANCH=foundry/<unit-id-lowercased>  WORKTREE=<path>
#
# merge <UNIT-ID>
#   Checks out bucket branch, git merge --no-ff unit-branch.
#   Success: agent-code-complete → merged.  Conflict: aborts, marks merge-conflict, exits non-zero.
#   stdout (success): MERGE=ok  BRANCH=<branch>
#   stdout (conflict): MERGE=conflict
#
# reject <UNIT-ID>
#   agent-code-complete|in-progress → review-rejected, bumps updated.
#   stdout: STATUS=review-rejected  UNIT=<id>
#
# escalate <UNIT-ID>
#   agent-code-complete|in-progress → review-escalated, bumps updated.
#   stdout: STATUS=review-escalated  UNIT=<id>
# ─────────────────────────────────────────────────────────────────────────────
# Invariant 0: this script NEVER pushes or opens a PR. No `git push` anywhere.
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Repo profile resolution ───────────────────────────────────────────────────
# Foundry is repo-agnostic. Each target repo is a profile in repos.json
# (repo_dir, findings_dir, worktrees_base, branch_prefix, base, setup_cmd,
# verifier_cmd, risk_tier). A run is scoped to ONE repo, selected via
# FOUNDRY_REPO (env) or `init --repo <key>`, defaulting to example.
# Individual path env-overrides (REPO_DIR/FINDINGS_DIR/WORKTREES_BASE) still win
# over the profile — handy for tests.
PROFILE_FILE="${FOUNDRY_REPOS:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/repos.json}"

# Capture any pre-set env path-overrides BEFORE the profile clobbers them.
_OVR_REPO_DIR="${REPO_DIR:-}"
_OVR_FINDINGS_DIR="${FINDINGS_DIR:-}"
_OVR_WORKTREES_BASE="${WORKTREES_BASE:-}"

_load_profile() {
  local key="$1" out
  out=$(python3 - "$key" "$PROFILE_FILE" <<'PYEOF'
import sys, json, os, shlex
key, pf = sys.argv[1], sys.argv[2]
try:
    with open(os.path.expanduser(pf)) as f:
        repos = json.load(f)
except FileNotFoundError:
    sys.stderr.write(f"ERROR: repo profile registry not found: {pf}\n"); sys.exit(3)
except json.JSONDecodeError as e:
    sys.stderr.write(f"ERROR: repo profile registry is not valid JSON: {e}\n"); sys.exit(3)
profiles = {k: v for k, v in repos.items() if not k.startswith("_")}
if key not in profiles:
    sys.stderr.write(f"ERROR: unknown repo profile '{key}'. Known: {', '.join(sorted(profiles))}\n"); sys.exit(3)
p = profiles[key]
required = ["repo_dir","findings_dir","worktrees_base","branch_prefix","base","setup_cmd","verifier_cmd"]
missing = [k for k in required if not p.get(k)]
if missing:
    sys.stderr.write(f"ERROR: profile '{key}' missing required keys: {', '.join(missing)}\n"); sys.exit(3)
def exp(v): return os.path.expanduser(v) if isinstance(v, str) else v
emit = {
    "PROFILE_REPO_DIR":       exp(p["repo_dir"]),
    "PROFILE_FINDINGS_DIR":   exp(p["findings_dir"]),
    "PROFILE_WORKTREES_BASE": exp(p["worktrees_base"]),
    "PROFILE_BRANCH_PREFIX":  p["branch_prefix"],
    "PROFILE_BASE":           p["base"],
    "PROFILE_SETUP_CMD":      p["setup_cmd"],
    "PROFILE_VERIFIER_CMD":   p["verifier_cmd"],
    "PROFILE_RISK_TIER":      p.get("risk_tier", "unknown"),
    "PROFILE_UNIT_GLOB":      p.get("unit_glob", "UNIT-*.md"),
}
for k, v in emit.items():
    print(f"{k}={shlex.quote(str(v))}")
PYEOF
  ) || exit $?
  eval "$out"
}

# Resolve the active profile and derive all config. Re-callable (init --repo).
_select_profile() {
  REPO_KEY="$1"
  _load_profile "$REPO_KEY"
  REPO_DIR="${_OVR_REPO_DIR:-$PROFILE_REPO_DIR}"
  FINDINGS_DIR="${_OVR_FINDINGS_DIR:-$PROFILE_FINDINGS_DIR}"
  WORKTREES_BASE="${_OVR_WORKTREES_BASE:-$PROFILE_WORKTREES_BASE}"
  BRANCH_PREFIX="$PROFILE_BRANCH_PREFIX"
  BASE_REF_FULL="$PROFILE_BASE"          # e.g. origin/main
  BASE_REMOTE="${BASE_REF_FULL%%/*}"     # origin
  BASE_BRANCH="${BASE_REF_FULL#*/}"      # main
  SETUP_CMD="$PROFILE_SETUP_CMD"
  VERIFIER_CMD="$PROFILE_VERIFIER_CMD"
  RISK_TIER="$PROFILE_RISK_TIER"
  UNIT_GLOB="$PROFILE_UNIT_GLOB"
}

_select_profile "${FOUNDRY_REPO:-example}"
# ─────────────────────────────────────────────────────────────────────────────

# ── Helpers ───────────────────────────────────────────────────────────────────

_today() { date +%Y%m%d; }

_bucket_branch() {
  # Reads the active bucket branch from the target repo's current HEAD
  # or falls back to deriving from the most-recent local bucket. Used by
  # claim/merge (they operate on whatever bucket is live for this profile).
  local branch
  branch=$(git -C "$REPO_DIR" symbolic-ref --short HEAD 2>/dev/null || true)
  if [[ "$branch" == "${BRANCH_PREFIX}-"* ]]; then
    echo "$branch"
    return
  fi
  # If HEAD is not on a bucket branch, find the most-recent one locally
  git -C "$REPO_DIR" branch --list "${BRANCH_PREFIX}-*" \
    | sed 's/^[* ]*//' \
    | sort -r \
    | head -1
}

_require_bucket() {
  local bucket
  bucket=$(_bucket_branch)
  if [[ -z "$bucket" ]]; then
    echo "ERROR: No bucket branch (${BRANCH_PREFIX}-*) found for repo '${REPO_KEY}'. Run 'init' first." >&2
    exit 1
  fi
  echo "$bucket"
}

# Read a single frontmatter key from a finding file.
# Usage: _fm_get <file> <key>
_fm_get() {
  local file="$1" key="$2"
  python3 - "$file" "$key" <<'PYEOF'
import sys, re
file, key = sys.argv[1], sys.argv[2]
with open(file) as f:
    content = f.read()
m = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
if not m:
    sys.exit(0)
fm = m.group(1)
for line in fm.splitlines():
    k, _, v = line.partition(':')
    if k.strip() == key:
        print(v.strip())
        sys.exit(0)
PYEOF
}

# Set (or add) one or more frontmatter keys in a finding file.
# Preserves all other keys and the markdown body.
# Usage: _fm_set <file> key1=val1 key2=val2 ...
_fm_set() {
  local file="$1"; shift
  python3 - "$file" "$@" <<'PYEOF'
import sys, re

file = sys.argv[1]
updates = {}
for arg in sys.argv[2:]:
    k, _, v = arg.partition('=')
    updates[k] = v

with open(file) as f:
    content = f.read()

m = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
if not m:
    sys.stderr.write(f"ERROR: no frontmatter in {file}\n")
    sys.exit(1)

fm_text = m.group(1)
body    = m.group(2)

lines   = fm_text.splitlines()
new_lines = []
seen    = set()

for line in lines:
    k, _, v = line.partition(':')
    key = k.strip()
    if key in updates:
        new_lines.append(f"{key}: {updates[key]}")
        seen.add(key)
    else:
        new_lines.append(line)

# Append any keys not already present
for key, val in updates.items():
    if key not in seen:
        new_lines.append(f"{key}: {val}")

new_content = '---\n' + '\n'.join(new_lines) + '\n---\n' + body
with open(file, 'w') as f:
    f.write(new_content)
PYEOF
}

# Find a finding file by UNIT-ID (case-insensitive match on filename)
_find_finding() {
  local unit_id="$1"
  # Normalize: uppercase for glob
  local upper; upper=$(echo "$unit_id" | tr '[:lower:]' '[:upper:]')
  local file="${FINDINGS_DIR}/${upper}.md"
  if [[ ! -f "$file" ]]; then
    echo "ERROR: Finding not found: $file" >&2
    exit 1
  fi
  echo "$file"
}

# ── Subcommands ───────────────────────────────────────────────────────────────

cmd_init() {
  local date_arg=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --date)
        if [[ $# -lt 2 ]]; then
          echo "ERROR: --date requires a YYYYMMDD value" >&2; exit 1
        fi
        date_arg="$2"; shift 2 ;;
      --repo)
        if [[ $# -lt 2 ]]; then
          echo "ERROR: --repo requires a profile key" >&2; exit 1
        fi
        _select_profile "$2"; shift 2 ;;
      *) echo "ERROR: unknown arg to init: $1" >&2; exit 1 ;;
    esac
  done
  local date="${date_arg:-$(_today)}"
  local bucket="${BRANCH_PREFIX}-${date}"

  echo "Fetching ${BASE_REMOTE} ${BASE_BRANCH} for repo '${REPO_KEY}'..." >&2
  git -C "$REPO_DIR" fetch "$BASE_REMOTE" "$BASE_BRANCH" >&2

  if git -C "$REPO_DIR" branch --list "$bucket" | grep -q .; then
    echo "Bucket branch $bucket already exists — no-op." >&2
  else
    echo "Creating bucket branch $bucket from ${BASE_REF_FULL}..." >&2
    git -C "$REPO_DIR" branch "$bucket" "$BASE_REF_FULL"
    echo "Created $bucket." >&2
  fi

  echo "REPO=${REPO_KEY}"
  echo "BUCKET=${bucket}"
}

cmd_next() {
  # PURE READ — mutate nothing

  # Priority 1: any agent-code-complete → ACTION=integrate (oldest updated first)
  local best_file="" best_updated="9999-99-99"
  while IFS= read -r -d '' file; do
    local status; status=$(_fm_get "$file" status)
    [[ "$status" == "agent-code-complete" ]] || continue
    local upd; upd=$(_fm_get "$file" updated)
    # Lexicographic date comparison (YYYY-MM-DD sorts correctly)
    if [[ "$upd" < "$best_updated" ]]; then
      best_updated="$upd"
      best_file="$file"
    fi
  done < <(find "$FINDINGS_DIR" -maxdepth 1 -name "$UNIT_GLOB" -print0 | sort -z)

  if [[ -n "$best_file" ]]; then
    local unit_id;    unit_id=$(_fm_get    "$best_file" id)
    local branch;   branch=$(_fm_get   "$best_file" branch)
    local worktree; worktree=$(_fm_get "$best_file" worktree)
    echo "ACTION=integrate"
    echo "UNIT=${unit_id}"
    echo "BRANCH=${branch}"
    echo "WORKTREE=${worktree}"
    return
  fi

  # Priority 2: any open (eligible) → ACTION=implement
  # Order deterministically by lexicographic sort of the full UNIT-ID string.
  # This is crash-proof across all ID forms (numeric, lettered UNIT-B01, UNIT-T01, etc.)
  # and avoids bash arithmetic pitfalls (octal trap on 08/09, unbound-var on B01).
  # Numeric IDs naturally sort before lettered IDs under LC_ALL=C (digits < letters).
  local implement_file=""
  while IFS= read -r file; do
    local status; status=$(_fm_get "$file" status)
    [[ "$status" == "open" ]] || continue
    # Check foundry_skip
    local skip; skip=$(_fm_get "$file" foundry_skip 2>/dev/null || true)
    [[ "$skip" == "true" ]] && continue
    implement_file="$file"
    break  # first match in lex order wins
  done < <(find "$FINDINGS_DIR" -maxdepth 1 -name "$UNIT_GLOB" | LC_ALL=C sort)

  if [[ -n "$implement_file" ]]; then
    local unit_id; unit_id=$(_fm_get "$implement_file" id)
    echo "ACTION=implement"
    echo "UNIT=${unit_id}"
    return
  fi

  echo "ACTION=drained"
}

cmd_claim() {
  [[ $# -ge 1 ]] || { echo "ERROR: claim requires <UNIT-ID>" >&2; exit 1; }
  local unit_id; unit_id=$(echo "$1" | tr '[:lower:]' '[:upper:]')
  local file; file=$(_find_finding "$unit_id")

  # Verify current status
  local current_status; current_status=$(_fm_get "$file" status)
  if [[ "$current_status" != "open" ]]; then
    echo "ERROR: $unit_id status is '$current_status', expected 'open'." >&2
    exit 1
  fi

  # Determine bucket branch (must exist)
  local bucket; bucket=$(_require_bucket)

  # Derive branch and worktree path
  local unit_lower; unit_lower=$(echo "$unit_id" | tr '[:upper:]' '[:lower:]')
  local branch="foundry/${unit_lower}"
  local worktree_path="${WORKTREES_BASE}/foundry-${unit_lower}"

  echo "Claiming $unit_id on bucket $bucket..." >&2
  echo "  branch:   $branch" >&2
  echo "  worktree: $worktree_path" >&2

  # Check for pre-existing worktree/branch — detect + reuse or error clearly
  local branch_exists=false worktree_exists=false
  if git -C "$REPO_DIR" branch --list "$branch" | grep -q .; then
    branch_exists=true
    echo "WARNING: branch $branch already exists — will reuse." >&2
  fi
  if [[ -d "$worktree_path" ]]; then
    worktree_exists=true
    echo "WARNING: worktree path $worktree_path already exists — will reuse." >&2
  fi

  if [[ "$branch_exists" == false && "$worktree_exists" == false ]]; then
    # Normal path: create worktree off bucket TIP
    git -C "$REPO_DIR" worktree add "$worktree_path" -b "$branch" "$bucket"
    echo "Worktree created." >&2
  elif [[ "$branch_exists" == true && "$worktree_exists" == false ]]; then
    # Branch exists but no worktree: add worktree pointing at existing branch
    git -C "$REPO_DIR" worktree add "$worktree_path" "$branch"
    echo "Worktree added for existing branch." >&2
  elif [[ "$worktree_exists" == true ]]; then
    # Worktree dir exists — verify it's a registered git worktree.
    # Anchor match with trailing space to prevent UNIT-1 partial-matching UNIT-14.
    if git -C "$REPO_DIR" worktree list | grep -qF -- "${worktree_path} "; then
      echo "Reusing existing registered worktree." >&2
    else
      echo "ERROR: directory $worktree_path exists but is not a registered git worktree. Remove it manually and retry." >&2
      exit 1
    fi
  fi

  # Run the profile's setup command in the worktree
  echo "Running setup [${SETUP_CMD}] in ${worktree_path} ..." >&2
  (cd "$worktree_path" && eval "$SETUP_CMD") >&2

  # Update frontmatter: status, branch, worktree, verifier, updated
  local today; today=$(date +%Y-%m-%d)
  _fm_set "$file" \
    "status=in-progress" \
    "branch=${branch}" \
    "worktree=${worktree_path}" \
    "verifier=${VERIFIER_CMD}" \
    "updated=${today}"

  echo "Finding $unit_id updated to in-progress." >&2
  echo "BRANCH=${branch}"
  echo "WORKTREE=${worktree_path}"
}

cmd_merge() {
  [[ $# -ge 1 ]] || { echo "ERROR: merge requires <UNIT-ID>" >&2; exit 1; }
  local unit_id; unit_id=$(echo "$1" | tr '[:lower:]' '[:upper:]')
  local file; file=$(_find_finding "$unit_id")

  local current_status; current_status=$(_fm_get "$file" status)
  if [[ "$current_status" != "agent-code-complete" ]]; then
    echo "ERROR: $unit_id status is '$current_status', expected 'agent-code-complete'." >&2
    exit 1
  fi

  local unit_branch; unit_branch=$(_fm_get "$file" branch)
  local title;       title=$(_fm_get       "$file" title)

  if [[ -z "$unit_branch" ]]; then
    echo "ERROR: $unit_id has no 'branch' frontmatter key. Was it claimed?" >&2
    exit 1
  fi

  local bucket; bucket=$(_require_bucket)

  echo "Checking out bucket branch $bucket..." >&2
  git -C "$REPO_DIR" checkout "$bucket" >&2

  echo "Merging $unit_branch --no-ff into $bucket..." >&2
  local merge_msg="Foundry: merge ${unit_id} — ${title}"

  # Attempt merge; capture exit code without letting set -e fire
  if git -C "$REPO_DIR" merge --no-ff "$unit_branch" -m "$merge_msg" >&2; then
    # Success
    local today; today=$(date +%Y-%m-%d)
    _fm_set "$file" \
      "status=merged" \
      "updated=${today}"
    echo "Merge succeeded. Finding $unit_id → merged." >&2
    # Keep worktree for inspection (V0 default; remove manually when done)
    echo "MERGE=ok"
    echo "BRANCH=${unit_branch}"
  else
    # Conflict — abort and signal
    echo "Merge conflict detected. Aborting..." >&2
    git -C "$REPO_DIR" merge --abort >&2 || true
    local today; today=$(date +%Y-%m-%d)
    _fm_set "$file" \
      "status=merge-conflict" \
      "updated=${today}"
    echo "Finding $unit_id → merge-conflict." >&2
    echo "MERGE=conflict"
    exit 1
  fi
}

cmd_reject() {
  [[ $# -ge 1 ]] || { echo "ERROR: reject requires <UNIT-ID>" >&2; exit 1; }
  local unit_id; unit_id=$(echo "$1" | tr '[:lower:]' '[:upper:]')
  local file; file=$(_find_finding "$unit_id")

  local current_status; current_status=$(_fm_get "$file" status)
  case "$current_status" in
    agent-code-complete|in-progress) ;;
    *)
      echo "ERROR: $unit_id status is '$current_status'; can only reject agent-code-complete or in-progress." >&2
      exit 1
      ;;
  esac

  local today; today=$(date +%Y-%m-%d)
  _fm_set "$file" \
    "status=review-rejected" \
    "updated=${today}"

  echo "Finding $unit_id → review-rejected." >&2
  echo "STATUS=review-rejected"
  echo "UNIT=${unit_id}"
}

cmd_escalate() {
  [[ $# -ge 1 ]] || { echo "ERROR: escalate requires <UNIT-ID>" >&2; exit 1; }
  local unit_id; unit_id=$(echo "$1" | tr '[:lower:]' '[:upper:]')
  local file; file=$(_find_finding "$unit_id")

  local current_status; current_status=$(_fm_get "$file" status)
  case "$current_status" in
    agent-code-complete|in-progress) ;;
    *)
      echo "ERROR: $unit_id status is '$current_status'; can only escalate agent-code-complete or in-progress." >&2
      exit 1
      ;;
  esac

  local today; today=$(date +%Y-%m-%d)
  _fm_set "$file" \
    "status=review-escalated" \
    "updated=${today}"

  echo "Finding $unit_id → review-escalated." >&2
  echo "STATUS=review-escalated"
  echo "UNIT=${unit_id}"
}

cmd_validate() {
  # PREFLIGHT LINT — mutate nothing. Verifies every claimable unit honors the
  # work-unit contract: required frontmatter (id/title/status) + a non-empty
  # `## Acceptance Criteria` body section. Also warns on out-of-order depends_on.
  # Exit 0 = bucket is run-ready; exit 4 = at least one contract violation.
  python3 - "$FINDINGS_DIR" "$UNIT_GLOB" <<'PYEOF'
import sys, os, re, glob

units_dir, unit_glob = sys.argv[1], sys.argv[2]
files = sorted(glob.glob(os.path.join(units_dir, unit_glob)))
if not files:
    print(f"VALIDATE=empty  ({units_dir}/{unit_glob} matched nothing)")
    sys.exit(0)

# Statuses that still need to RUN — those must honor the full contract.
# Terminal/closed statuses are exempt (they're history, not queued work).
CLAIMABLE = {"open", "in-progress", "agent-code-complete"}

def parse(path):
    s = open(path).read()
    m = re.match(r'^---\n(.*?)\n---\n(.*)', s, re.DOTALL)
    fm, body = ({}, s)
    if m:
        body = m.group(2)
        for line in m.group(1).splitlines():
            k, _, v = line.partition(':')
            if k.strip():
                fm[k.strip()] = v.strip()
    return fm, body

def has_acceptance(body):
    # A heading matching "acceptance criteria" / "acceptance" / "validation criteria"
    # followed by at least one non-blank, non-heading content line.
    m = re.search(r'(?im)^\s{0,3}#{1,6}\s*(acceptance\s*criteria|acceptance|validation\s*criteria)\b.*$',
                  body)
    if not m:
        return False
    tail = body[m.end():]
    for line in tail.splitlines():
        if re.match(r'^\s{0,3}#{1,6}\s', line):   # next heading → section ended
            break
        if line.strip():                          # any content line counts
            return True
    return False

ids = {}
errors, warnings = [], []
for f in files:
    fm, body = parse(f)
    name = os.path.basename(f)
    status = fm.get("status", "")
    fid = fm.get("id", "")
    if fid:
        ids[fid] = name
    if status not in CLAIMABLE:
        continue  # closed/terminal units are exempt from the contract lint
    for key in ("id", "title", "status"):
        if not fm.get(key):
            errors.append(f"{name}: missing required frontmatter `{key}`")
    if not has_acceptance(body):
        errors.append(f"{name}: missing/empty `## Acceptance Criteria` section (required by the unit contract)")

# Dependency ordering: depends_on must lexically PRECEDE this unit (claimed earlier).
for f in files:
    fm, _ = parse(f)
    if fm.get("status") not in CLAIMABLE:
        continue
    fid = fm.get("id", "")
    dep_raw = fm.get("depends_on", "")
    if not dep_raw:
        continue
    deps = [d.strip().strip('[]') for d in re.split(r'[,\s]+', dep_raw) if d.strip().strip('[]')]
    for d in deps:
        if d not in ids:
            warnings.append(f"{os.path.basename(f)}: depends_on `{d}` not found in bucket")
        elif fid and d >= fid:
            warnings.append(f"{os.path.basename(f)}: depends_on `{d}` sorts at/after `{fid}` — it would be claimed LATER (no auto-retry will strand this unit)")

for w in warnings:
    print(f"WARN  {w}")
for e in errors:
    print(f"FAIL  {e}")

claimable = sum(1 for f in files if parse(f)[0].get("status") in CLAIMABLE)
if errors:
    print(f"VALIDATE=fail  ({len(errors)} violation(s), {len(warnings)} warning(s), {claimable} claimable unit(s))")
    sys.exit(4)
print(f"VALIDATE=ok  ({claimable} claimable unit(s) honor the contract, {len(warnings)} warning(s))")
PYEOF
}

# ── Dispatch ──────────────────────────────────────────────────────────────────
[[ $# -ge 1 ]] || { echo "Usage: foundry_tick.sh <init|next|claim|merge|reject|escalate|validate> [args...]" >&2; exit 1; }

subcommand="$1"; shift

case "$subcommand" in
  init)     cmd_init     "$@" ;;
  next)     cmd_next          ;;
  claim)    cmd_claim    "$@" ;;
  merge)    cmd_merge    "$@" ;;
  reject)   cmd_reject   "$@" ;;
  escalate) cmd_escalate "$@" ;;
  validate) cmd_validate      ;;
  *)
    echo "ERROR: unknown subcommand '$subcommand'. Valid: init next claim merge reject escalate validate" >&2
    exit 1
    ;;
esac
