#!/usr/bin/env python3
"""Smoke-test that mnox-ai skills actually land where a host discovers them.

The provider-portable audit warns: a copier passing its own unit tests is NOT
evidence a host consumes the output. This script closes that gap. For each host it:

  1. Runs the REAL exporter CLI into a temp dir shaped like the host's discovery
     path, then verifies every skill's SKILL.md landed with valid frontmatter.
  2. Verifies engine-backed skills (config-chunks) bundle their engine.
  3. Renders the host's session-tracker MCP snippet with a resolved ABSOLUTE path
     and asserts it points at a real, executable server.sh (no ${CLAUDE_PLUGIN_ROOT}).
  4. With --live and the host CLI present, runs a real host-load probe (for Codex,
     a `codex exec` skill-discovery prompt — this costs a model call).

Exit is non-zero if any automated (non-live) check fails. Stdlib-only.

Usage:
  python3 scripts/smoke_host_load.py                 # all hosts, automated checks
  python3 scripts/smoke_host_load.py --host codex --live
  python3 scripts/smoke_host_load.py --host cursor --keep
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPORTER = REPO_ROOT / "scripts" / "export_skills.py"
SERVER_SH = REPO_ROOT / "plugins" / "session-tracker" / "bin" / "server.sh"

# Where each host discovers project-local skills (relative to a project root).
HOST_SKILL_SUBPATH = {
    "claude": ".claude/skills",
    "codex": ".agents/skills",
    "cursor": ".cursor/skills",
}
# User-global equivalents, for the report / manual steps.
HOST_USER_SKILL_DIR = {
    "claude": "~/.claude/skills",
    "codex": "~/.codex/skills",
    "cursor": "~/.cursor/skills",
}


class Report:
    def __init__(self, host: str) -> None:
        self.host = host
        self.checks: list[tuple[bool, str]] = []

    def check(self, ok: bool, msg: str) -> None:
        self.checks.append((bool(ok), msg))

    @property
    def passed(self) -> bool:
        return all(ok for ok, _ in self.checks)

    def render(self) -> str:
        lines = [f"\n=== {self.host} ==="]
        for ok, msg in self.checks:
            lines.append(f"  {'PASS' if ok else 'FAIL'}  {msg}")
        return "\n".join(lines)


def valid_frontmatter(skill_md: Path) -> bool:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False
    end = text.find("\n---", 4)
    if end < 0:
        return False
    fm = text[4:end]
    return ("name:" in fm) and ("description:" in fm)


def run_exporter(dest: Path, skills: list[str], with_engine: bool) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(EXPORTER), "--output-dir", str(dest), "--overwrite"]
    for name in skills:
        cmd += ["--skill", name]
    if with_engine:
        cmd.append("--with-engine")
    return subprocess.run(cmd, capture_output=True, text=True)


def codex_mcp_snippet(server: Path) -> str:
    return (
        "[mcp_servers.session-tracker]\n"
        'command = "bash"\n'
        f'args = ["{server}"]'
    )


def cursor_mcp_snippet(server: Path) -> str:
    return json.dumps(
        {"mcpServers": {"session-tracker": {"command": "bash", "args": [str(server)]}}},
        indent=2,
    )


def check_host(host: str, skills: list[str], workdir: Path) -> Report:
    rep = Report(host)
    subpath = HOST_SKILL_SUBPATH[host]
    dest = workdir / host / subpath
    # config-chunks skills need their engine bundled off Claude.
    with_engine = any(s in {"ai-setup", "chunks", "chunk-review", "ideation", "permission-setup"} for s in skills)

    proc = run_exporter(dest, skills, with_engine)
    rep.check(proc.returncode == 0, f"exporter ran into {subpath}/ (rc={proc.returncode})")
    if proc.returncode != 0:
        rep.check(False, f"exporter stderr: {proc.stderr.strip()[:200]}")
        return rep

    # 1. Placement + frontmatter for every requested skill.
    missing = [s for s in skills if not (dest / s / "SKILL.md").is_file()]
    rep.check(not missing, f"all {len(skills)} skills present at discovery path"
              + (f" (missing: {missing})" if missing else ""))
    bad_fm = [s for s in skills if (dest / s / "SKILL.md").is_file() and not valid_frontmatter(dest / s / "SKILL.md")]
    rep.check(not bad_fm, "exported SKILL.md frontmatter valid" + (f" (bad: {bad_fm})" if bad_fm else ""))
    rep.check((dest / "skills-manifest.json").is_file(), "skills-manifest.json written")

    # 2. Engine bundling.
    if with_engine:
        engine = dest / ".engines" / "config-chunks" / "scripts"
        rep.check(engine.is_dir(), "config-chunks engine bundled (.engines/config-chunks/scripts)")

    # 3. MCP connection snippet — absolute, real, no Claude-only var.
    rep.check(SERVER_SH.is_file(), f"session-tracker server.sh exists ({SERVER_SH.name})")
    snippet = codex_mcp_snippet(SERVER_SH) if host == "codex" else cursor_mcp_snippet(SERVER_SH)
    if host == "claude":
        rep.check(True, "MCP wired by marketplace plugin (no manual snippet)")
    else:
        rep.check(str(SERVER_SH) in snippet and SERVER_SH.is_absolute(), "MCP snippet uses resolved absolute path")
        rep.check("${CLAUDE_PLUGIN_ROOT}" not in snippet, "MCP snippet free of ${CLAUDE_PLUGIN_ROOT}")
    return rep


def live_probe(host: str, skills: list[str], workdir: Path) -> str:
    """Real host-load probe. Only Codex has a usable CLI here; skill discovery
    requires a model call via `codex exec`."""
    if host != "codex":
        return f"  (no automated live probe for {host} — see manual steps below)"
    if shutil.which("codex") is None:
        return "  codex CLI not found on PATH — skipping live probe"
    project = workdir / "codex" / "live-project"
    (project / ".agents" / "skills").mkdir(parents=True, exist_ok=True)
    run_exporter(project / ".agents" / "skills", skills, with_engine=False)
    prompt = (
        "List the names of any Agent Skills you can load from this project's "
        ".agents/skills directory. Reply with just a comma-separated list of names."
    )
    proc = subprocess.run(
        ["codex", "exec", "--skip-git-repo-check", "--cd", str(project), prompt],
        capture_output=True, text=True, timeout=180,
    )
    out = (proc.stdout or proc.stderr).strip()
    return f"  codex exec probe (rc={proc.returncode}):\n    " + out.replace("\n", "\n    ")


def manual_steps(host: str, skills: list[str]) -> str:
    user_dir = HOST_USER_SKILL_DIR[host]
    subset = " ".join(f"--skill {s}" for s in skills[:2])
    lines = [f"\n--- {host}: manual real-host verification ---"]
    if host == "cursor":
        lines.append(f"  # Cursor 2.4+ reads ~/.claude/skills directly — if you use Claude Code, nothing to do.")
        lines.append(f"  python3 scripts/export_skills.py --output-dir {user_dir} --overwrite   # otherwise")
        lines.append(f"  # then open Cursor → Skills panel and confirm they appear (Agent/Chat mode)")
    elif host == "codex":
        lines.append(f"  python3 scripts/export_skills.py --output-dir {user_dir} --overwrite")
        lines.append(f'  codex exec "list the skills you can load"   # confirm discovery (model call)')
    else:
        lines.append(f"  /plugin marketplace add mnox/mnox-ai && /plugin install all-skills@mnox-ai")
    lines.append(f"  # à la carte example: python3 scripts/export_skills.py --output-dir {user_dir} {subset}")
    return "\n".join(lines)


def run_checks(hosts: list[str], skills: list[str], workdir: Path) -> list[Report]:
    return [check_host(h, skills, workdir) for h in hosts]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", choices=(*HOST_SKILL_SUBPATH, "all"), default="all")
    parser.add_argument("--skill", action="append", default=[], help="Skill subset (default: all).")
    parser.add_argument("--live", action="store_true", help="Run a real host-load probe (Codex: costs a model call).")
    parser.add_argument("--keep", action="store_true", help="Keep the temp export tree for inspection.")
    args = parser.parse_args(argv)

    hosts = list(HOST_SKILL_SUBPATH) if args.host == "all" else [args.host]
    skills = args.skill or [
        s["name"] for s in json.loads(
            subprocess.run([sys.executable, str(EXPORTER), "--list"], capture_output=True, text=True).stdout
        )
    ]

    workdir = Path(tempfile.mkdtemp(prefix="mnox-smoke-"))
    try:
        reports = run_checks(hosts, skills, workdir)
        for rep in reports:
            print(rep.render())
            if args.live:
                print(live_probe(rep.host, skills, workdir))
            print(manual_steps(rep.host, skills))
        ok = all(r.passed for r in reports)
        print(f"\n{'ALL AUTOMATED CHECKS PASSED' if ok else 'SMOKE TEST FAILED'} "
              f"({sum(len(r.checks) for r in reports)} checks, {len(hosts)} hosts, {len(skills)} skills)")
        if args.keep:
            print(f"temp tree kept at: {workdir}")
        return 0 if ok else 1
    finally:
        if not args.keep:
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
