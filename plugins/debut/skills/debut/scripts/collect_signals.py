# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""debut :: collect_signals.py

SAFE, READ-ONLY deterministic pre-scan for the `debut` public-readiness audit.
Runs ONCE in Phase 0; the orchestrator hands each domain sub-agent only its slice.

Hard rules:
  * Python STDLIB ONLY (subprocess, json, pathlib, re, argparse, shutil, datetime).
  * NEVER shells out to bash; every external program is invoked via subprocess
    with an explicit argv list (no shell=True).
  * READ-ONLY: never mutates the repo, never writes inside --repo. Output JSON
    goes to --out (and stdout) only.
  * GRACEFUL DEGRADATION: a missing tool, a missing file, a non-git dir, or any
    subprocess error yields an {"available": false, ...} style entry — it never
    crashes. Worst case a section is partial; the process always exits 0 with
    valid JSON.

This is a SIGNAL collector, not a scanner. It does NOT run gitleaks/trufflehog/
eslint/tsc/npm-audit — those heavier domain scans are the sub-agents' job. Here
we only probe tool availability and gather cheap structural facts.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# subprocess helpers (all read-only, all bounded)
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 20  # seconds; git history walks can be slowish on big repos


def run(argv, cwd=None, timeout=DEFAULT_TIMEOUT):
    """Run argv read-only. Returns dict {ok, code, out, err}. Never raises."""
    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            timeout=timeout,
            text=True,
        )
        return {
            "ok": proc.returncode == 0,
            "code": proc.returncode,
            "out": proc.stdout or "",
            "err": (proc.stderr or "").strip(),
        }
    except FileNotFoundError:
        return {"ok": False, "code": None, "out": "", "err": "not-found"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "code": None, "out": "", "err": "timeout"}
    except Exception as exc:  # noqa: BLE001 - never let a probe crash the collector
        return {"ok": False, "code": None, "out": "", "err": f"error: {exc}"}


def git(repo, args, timeout=DEFAULT_TIMEOUT):
    return run(["git"] + args, cwd=repo, timeout=timeout)


def first_existing(repo, names):
    """Return the first relative name in `names` that exists under repo, else None."""
    for name in names:
        if (repo / name).exists():
            return name
    return None


# ---------------------------------------------------------------------------
# tool-availability probe
# ---------------------------------------------------------------------------

TOOLS = [
    "git", "gitleaks", "trufflehog", "eslint", "prettier", "tsc",
    "npm", "npx", "depcheck", "gh", "git-sizer", "ts-prune",
]


def probe_tools():
    out = {}
    for tool in TOOLS:
        path = shutil.which(tool)
        out[tool] = {"available": path is not None, "path": path}
    return out


# ---------------------------------------------------------------------------
# git facts
# ---------------------------------------------------------------------------

def is_git_repo(repo):
    res = git(repo, ["rev-parse", "--is-inside-work-tree"])
    return res["ok"] and res["out"].strip() == "true"


def collect_git(repo, tools):
    git_avail = tools.get("git", {}).get("available", False)
    if not git_avail:
        return {"available": False, "reason": "git not installed"}
    if not is_git_repo(repo):
        return {"available": False, "reason": "not a git work tree"}

    info = {"available": True}

    branch = git(repo, ["rev-parse", "--abbrev-ref", "HEAD"])
    info["branch"] = branch["out"].strip() if branch["ok"] else None

    remote = git(repo, ["remote", "get-url", "origin"])
    info["remote_url"] = remote["out"].strip() if remote["ok"] else None

    upstream = git(repo, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    info["upstream"] = upstream["out"].strip() if upstream["ok"] else None

    # unpushed-commit count (informs mode: PRE-PUSH when > 0)
    if info["upstream"]:
        cnt = git(repo, ["rev-list", "--count", "@{u}..HEAD"])
        info["unpushed_commits"] = _to_int(cnt["out"]) if cnt["ok"] else None
    else:
        # no upstream configured: count all commits on the branch as "unpushed"
        cnt = git(repo, ["rev-list", "--count", "HEAD"])
        info["unpushed_commits"] = _to_int(cnt["out"]) if cnt["ok"] else None
        info["no_upstream"] = True

    total = git(repo, ["rev-list", "--count", "--all"])
    info["total_commits_all_refs"] = _to_int(total["out"]) if total["ok"] else None

    head = git(repo, ["rev-parse", "HEAD"])
    info["head_sha"] = head["out"].strip() if head["ok"] else None

    return info


def collect_visibility(repo, tools):
    """Public/private + GitHub metadata via gh (optional)."""
    if not tools.get("gh", {}).get("available", False):
        return {"available": False, "reason": "gh not installed"}
    res = run(
        ["gh", "repo", "view", "--json",
         "visibility,isPrivate,nameWithOwner,description,licenseInfo,repositoryTopics,homepageUrl"],
        cwd=repo,
    )
    if not res["ok"]:
        return {"available": False, "reason": "gh repo view failed", "detail": res["err"][:200]}
    try:
        data = json.loads(res["out"])
    except (ValueError, TypeError):
        return {"available": False, "reason": "gh returned non-JSON"}
    topics = data.get("repositoryTopics") or []
    license_info = data.get("licenseInfo") or {}
    return {
        "available": True,
        "visibility": data.get("visibility"),
        "is_private": data.get("isPrivate"),
        "name_with_owner": data.get("nameWithOwner"),
        "description": data.get("description"),
        "description_set": bool((data.get("description") or "").strip()),
        "homepage_url": data.get("homepageUrl"),
        "topics": [t.get("name") for t in topics if isinstance(t, dict)],
        "topic_count": len(topics),
        "license_spdx": license_info.get("spdxId"),
        "license_name": license_info.get("name"),
    }


# ---------------------------------------------------------------------------
# file-presence matrix
# ---------------------------------------------------------------------------

PRESENCE_SPEC = {
    "readme": ["README.md", "README.rst", "README.txt", "README"],
    "license": ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "COPYING.md"],
    "contributing": ["CONTRIBUTING.md", ".github/CONTRIBUTING.md", "docs/CONTRIBUTING.md"],
    "code_of_conduct": [
        "CODE_OF_CONDUCT.md", ".github/CODE_OF_CONDUCT.md", "docs/CODE_OF_CONDUCT.md",
    ],
    "security": ["SECURITY.md", ".github/SECURITY.md", "docs/SECURITY.md"],
    "support": ["SUPPORT.md", ".github/SUPPORT.md"],
    "codeowners": ["CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS"],
    "funding": [".github/FUNDING.yml", "FUNDING.yml"],
    "gitignore": [".gitignore"],
    "gitattributes": [".gitattributes"],
    "pr_template": ["PULL_REQUEST_TEMPLATE.md", ".github/PULL_REQUEST_TEMPLATE.md",
                    ".github/pull_request_template.md", "docs/PULL_REQUEST_TEMPLATE.md"],
    "changelog": ["CHANGELOG.md", "CHANGELOG", "docs/CHANGELOG.md", "HISTORY.md"],
    "editorconfig": [".editorconfig"],
    "package_json": ["package.json"],
    "tsconfig": ["tsconfig.json"],
    "dependabot": [".github/dependabot.yml", ".github/dependabot.yaml"],
    "renovate": ["renovate.json", ".github/renovate.json", ".renovaterc", ".renovaterc.json"],
}

LOCKFILES = ["package-lock.json", "pnpm-lock.yaml", "yarn.lock", "npm-shrinkwrap.json"]

LINT_CONFIGS = ["eslint.config.js", "eslint.config.mjs", "eslint.config.cjs", "eslint.config.ts",
                ".eslintrc", ".eslintrc.js", ".eslintrc.cjs", ".eslintrc.json", ".eslintrc.yml",
                ".eslintrc.yaml", "biome.json", "biome.jsonc"]

FORMAT_CONFIGS = [".prettierrc", ".prettierrc.json", ".prettierrc.js", ".prettierrc.cjs",
                  ".prettierrc.yml", ".prettierrc.yaml", "prettier.config.js",
                  "prettier.config.cjs", "biome.json", "biome.jsonc"]


def collect_presence(repo):
    matrix = {}
    for key, names in PRESENCE_SPEC.items():
        hit = first_existing(repo, names)
        matrix[key] = {"present": hit is not None, "path": hit}

    # lockfiles (multiple may exist)
    matrix["lockfiles"] = {
        "present": [name for name in LOCKFILES if (repo / name).exists()],
    }
    matrix["lockfiles"]["any"] = bool(matrix["lockfiles"]["present"])

    matrix["lint_config"] = {"path": first_existing(repo, LINT_CONFIGS)}
    matrix["lint_config"]["present"] = matrix["lint_config"]["path"] is not None
    matrix["format_config"] = {"path": first_existing(repo, FORMAT_CONFIGS)}
    matrix["format_config"]["present"] = matrix["format_config"]["path"] is not None

    # issue templates dir
    issue_dir = repo / ".github" / "ISSUE_TEMPLATE"
    issue_template_md = repo / ".github" / "ISSUE_TEMPLATE.md"
    templates = []
    if issue_dir.is_dir():
        try:
            templates = sorted(p.name for p in issue_dir.iterdir() if p.is_file())
        except OSError:
            templates = []
    matrix["issue_templates"] = {
        "dir_present": issue_dir.is_dir(),
        "single_file_present": issue_template_md.exists(),
        "templates": templates,
    }

    # CI workflows
    wf_dir = repo / ".github" / "workflows"
    workflows = []
    if wf_dir.is_dir():
        try:
            workflows = sorted(
                p.name for p in wf_dir.iterdir()
                if p.is_file() and p.suffix in (".yml", ".yaml")
            )
        except OSError:
            workflows = []
    matrix["ci_workflows"] = {"present": bool(workflows), "files": workflows}

    return matrix


# ---------------------------------------------------------------------------
# tracked-cruft scan (uses git ls-files — read-only)
# ---------------------------------------------------------------------------

CRUFT_RE = re.compile(
    r"(^|/)("
    r"\.env(\..*)?"
    r"|.*\.pem"
    r"|.*\.key"
    r"|id_rsa(\.pub)?"
    r"|\.DS_Store"
    r"|Thumbs\.db"
    r"|\.idea/"
    r"|\.vscode/"
    r"|node_modules/"
    r"|dist/"
    r"|build/"
    r"|\.terraform/"
    r"|.*\.log"
    r")",
    re.IGNORECASE,
)

CRUFT_CAP = 200


def collect_tracked_cruft(repo, git_available):
    if not git_available:
        return {"available": False, "reason": "git not available"}
    res = git(repo, ["ls-files"])
    if not res["ok"]:
        return {"available": False, "reason": "git ls-files failed"}
    hits = []
    for line in res["out"].splitlines():
        line = line.strip()
        if not line:
            continue
        if CRUFT_RE.search(line):
            hits.append(line)
            if len(hits) >= CRUFT_CAP:
                break
    return {
        "available": True,
        "count": len(hits),
        "capped": len(hits) >= CRUFT_CAP,
        "files": hits,
    }


# ---------------------------------------------------------------------------
# commit-message smell scan (bounded)
# ---------------------------------------------------------------------------

SMELL_RE = re.compile(
    r"(?i)\b(wip|fixup|squash|todo|hack|temp|asdf|oops|nvm|fuck|shit|damn|crap)\b"
)

COMMIT_SCAN_LIMIT = 1000  # most recent N commits across all refs


def collect_commit_smells(repo, git_available):
    if not git_available:
        return {"available": False, "reason": "git not available"}
    res = git(
        repo,
        ["log", "--all", "--no-merges", "-n", str(COMMIT_SCAN_LIMIT),
         "--pretty=format:%h\x1f%s"],
    )
    if not res["ok"]:
        return {"available": False, "reason": "git log failed"}
    hits = []
    scanned = 0
    for line in res["out"].splitlines():
        if not line.strip():
            continue
        scanned += 1
        parts = line.split("\x1f", 1)
        sha = parts[0]
        subject = parts[1] if len(parts) > 1 else ""
        m = SMELL_RE.search(subject)
        if m:
            hits.append({"sha": sha, "subject": subject[:160], "term": m.group(0).lower()})
    return {
        "available": True,
        "scanned": scanned,
        "scan_limit": COMMIT_SCAN_LIMIT,
        "hit_count": len(hits),
        "hits": hits[:100],
    }


# ---------------------------------------------------------------------------
# tsconfig strict parse (tolerant of JSONC comments / trailing commas)
# ---------------------------------------------------------------------------

def _strip_jsonc(text):
    """Best-effort strip of // and /* */ comments and trailing commas for JSONC."""
    # remove block comments
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    # remove line comments (not inside strings — best-effort)
    text = re.sub(r"(?m)//.*$", "", text)
    # remove trailing commas before } or ]
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    return text


def collect_tsconfig(repo, tsconfig_path):
    if not tsconfig_path:
        return {"available": False, "reason": "no tsconfig.json"}
    path = repo / tsconfig_path
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {"available": False, "reason": f"read failed: {exc}"}
    try:
        data = json.loads(_strip_jsonc(raw))
    except (ValueError, TypeError):
        return {"available": True, "parsed": False, "reason": "JSONC parse failed"}
    if not isinstance(data, dict):
        return {"available": True, "parsed": False, "reason": "not an object"}
    co = data.get("compilerOptions") or {}
    if not isinstance(co, dict):
        co = {}
    return {
        "available": True,
        "parsed": True,
        "extends": data.get("extends"),
        "strict": co.get("strict"),
        "no_implicit_any": co.get("noImplicitAny"),
        "strict_null_checks": co.get("strictNullChecks"),
        "no_unchecked_indexed_access": co.get("noUncheckedIndexedAccess"),
    }


# ---------------------------------------------------------------------------
# package.json summary
# ---------------------------------------------------------------------------

def collect_package_json(repo, present_path):
    if not present_path:
        return {"available": False, "reason": "no package.json"}
    path = repo / present_path
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {"available": False, "reason": f"read failed: {exc}"}
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return {"available": True, "parsed": False, "reason": "JSON parse failed"}
    if not isinstance(data, dict):
        return {"available": True, "parsed": False, "reason": "not an object"}
    scripts = data.get("scripts") or {}
    deps = data.get("dependencies") or {}
    dev_deps = data.get("devDependencies") or {}
    if not isinstance(scripts, dict):
        scripts = {}
    if not isinstance(deps, dict):
        deps = {}
    if not isinstance(dev_deps, dict):
        dev_deps = {}
    known_runners = ["jest", "vitest", "mocha", "ava", "@playwright/test",
                     "tap", "node:test", "uvu", "jasmine"]
    all_dep_names = set(deps) | set(dev_deps)
    return {
        "available": True,
        "parsed": True,
        "name": data.get("name"),
        "version": data.get("version"),
        "license": data.get("license"),
        "private": data.get("private"),
        "type": data.get("type"),
        "script_names": sorted(scripts.keys()),
        "has_test_script": "test" in scripts,
        "has_lint_script": "lint" in scripts,
        "has_typecheck_script": any(k in scripts for k in ("typecheck", "type-check", "tsc")),
        "dependency_count": len(deps),
        "dev_dependency_count": len(dev_deps),
        "test_runners_detected": sorted(r for r in known_runners if r in all_dep_names),
    }


# ---------------------------------------------------------------------------
# SemVer git tags
# ---------------------------------------------------------------------------

SEMVER_RE = re.compile(r"^v?\d+\.\d+\.\d+")


def collect_tags(repo, git_available):
    if not git_available:
        return {"available": False, "reason": "git not available"}
    res = git(repo, ["tag", "--list"])
    if not res["ok"]:
        return {"available": False, "reason": "git tag failed"}
    tags = [t.strip() for t in res["out"].splitlines() if t.strip()]
    semver = [t for t in tags if SEMVER_RE.match(t)]
    return {
        "available": True,
        "total_tags": len(tags),
        "semver_tags": semver[:50],
        "semver_tag_count": len(semver),
        "has_semver_tag": bool(semver),
    }


# ---------------------------------------------------------------------------
# test-file count (bounded glob, skips heavy dirs)
# ---------------------------------------------------------------------------

TEST_NAME_RE = re.compile(r"\.(test|spec)\.[cm]?[jt]sx?$", re.IGNORECASE)
SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", "coverage",
             ".terraform", "vendor", ".venv", "__pycache__"}
TEST_SCAN_CAP = 5000  # files examined, not matched


def collect_test_files(repo):
    count = 0
    examined = 0
    samples = []
    capped = False
    try:
        for path in repo.rglob("*"):
            # prune skip dirs by checking parts
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if not path.is_file():
                continue
            examined += 1
            if examined > TEST_SCAN_CAP:
                capped = True
                break
            if TEST_NAME_RE.search(path.name):
                count += 1
                if len(samples) < 20:
                    try:
                        samples.append(str(path.relative_to(repo)))
                    except ValueError:
                        samples.append(path.name)
    except OSError:
        pass
    return {
        "available": True,
        "test_file_count": count,
        "examined": examined,
        "capped": capped,
        "samples": samples,
    }


# ---------------------------------------------------------------------------
# misc helpers
# ---------------------------------------------------------------------------

def _to_int(text):
    try:
        return int((text or "").strip())
    except (ValueError, TypeError):
        return None


def detect_mode_hint(git_info):
    """Heuristic only — orchestrator makes the final mode call w/ user intent."""
    if not git_info.get("available"):
        return {"suggested": "readiness", "reason": "not a git repo; full sweep"}
    unpushed = git_info.get("unpushed_commits")
    if isinstance(unpushed, int) and unpushed > 0:
        return {
            "suggested": "pre-push",
            "reason": f"{unpushed} unpushed commit(s); pre-push diff mode is a candidate",
            "unpushed_commits": unpushed,
        }
    return {"suggested": "readiness", "reason": "no unpushed commits; full sweep"}


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def collect(repo):
    repo = repo.resolve()
    tools = probe_tools()
    git_available = tools.get("git", {}).get("available", False)

    git_info = collect_git(repo, tools)
    is_repo = git_info.get("available", False)
    presence = collect_presence(repo)

    signals = {
        "schema_version": 1,
        "tool": "debut/collect_signals.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo": {
            "path": str(repo),
            "name": repo.name,
            "is_git_repo": is_repo,
            "exists": repo.exists(),
        },
        "tools": tools,
        "git": git_info,
        "visibility": collect_visibility(repo, tools),
        "file_presence": presence,
        "tracked_cruft": collect_tracked_cruft(repo, git_available),
        "commit_smells": collect_commit_smells(repo, git_available),
        "tsconfig": collect_tsconfig(repo, presence.get("tsconfig", {}).get("path")),
        "package_json": collect_package_json(repo, presence.get("package_json", {}).get("path")),
        "tags": collect_tags(repo, git_available),
        "test_files": collect_test_files(repo),
    }
    signals["mode_hint"] = detect_mode_hint(git_info)
    return signals


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="debut SAFE read-only pre-scan -> JSON signals.",
    )
    parser.add_argument("--repo", default=".", help="path to repo (default: cwd)")
    parser.add_argument("--out", default=None, help="path to write JSON (also printed to stdout)")
    args = parser.parse_args(argv)

    repo = Path(args.repo).expanduser()

    if not repo.exists():
        # Still emit valid JSON; never crash.
        payload = {
            "schema_version": 1,
            "tool": "debut/collect_signals.py",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "repo": {"path": str(repo), "name": repo.name, "exists": False, "is_git_repo": False},
            "error": "repo path does not exist",
        }
    else:
        try:
            payload = collect(repo)
        except Exception as exc:  # noqa: BLE001 - last-resort guard; always emit JSON
            payload = {
                "schema_version": 1,
                "tool": "debut/collect_signals.py",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "repo": {"path": str(repo), "name": repo.name},
                "error": f"unexpected collector failure: {exc}",
            }

    text = json.dumps(payload, indent=2, sort_keys=False)

    if args.out:
        out_path = Path(args.out).expanduser()
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(text + "\n", encoding="utf-8")
        except OSError as exc:
            sys.stderr.write(f"warn: could not write --out ({out_path}): {exc}\n")

    sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
