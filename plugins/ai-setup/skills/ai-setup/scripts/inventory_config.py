#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Inventory the agent configuration that already exists, as JSON.

Scans the user's home directory and, optionally, a repository for agent
instruction files, rules, skills, subagent definitions, commands, settings,
and MCP configuration across the hosts it knows (Claude Code, Codex, Cursor,
and the shared AGENTS.md / .agents conventions).

Reports names, paths, sizes, key names, and counts only. Values are never
emitted, so tokens held in settings or MCP configuration cannot leak into the
conversation. Read-only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

Json = Mapping[str, "Json"] | Sequence["Json"] | str | int | float | bool | None

SCHEMA = "ai-setup.inventory.v1"
NESTED_DEPTH = 3
IGNORED_DIRS = frozenset(
    {"node_modules", "dist", "build", "out", "target", "vendor", "venv", "__pycache__", "deps"}
)
MARKER_RE = re.compile(r"<!--\s*([A-Za-z0-9_.-]+):start\s*-->")
IMPORT_RE = re.compile(r"(?<![\w`@/])@((?:~/|\.{1,2}/)?[\w.-]+(?:/[\w.-]+)*\.(?:md|mdc|txt))\b")
TOML_KEY_RE = re.compile(r"(?m)^([A-Za-z_][\w-]*)[ \t]*=")
TOML_MCP_RE = re.compile(r"(?m)^\[mcp_servers\.([^\].]+)")
PERMISSION_RULES = ("allow", "ask", "deny")
HOST_HOMES = (("claude-code", ".claude"), ("codex", ".codex"), ("cursor", ".cursor"))
KIND_KEYS = {
    "instructions": "instruction_files",
    "rules": "rules",
    "skills": "skills",
    "agents": "agents",
    "commands": "commands",
    "settings": "settings",
    "mcp": "mcp",
}


@dataclass(frozen=True)
class Location:
    host: str
    scope: str
    kind: str
    pattern: str


@dataclass(frozen=True)
class Context:
    home: Path
    repo: Path | None


@dataclass(frozen=True)
class Record:
    location: Location
    display: str
    details: Mapping[str, Json]


Describer = Callable[[Path, Context], Mapping[str, Json]]


def loc(host: str, scope: str, kind: str, *patterns: str) -> tuple[Location, ...]:
    return tuple(Location(host, scope, kind, pattern) for pattern in patterns)


LOCATIONS: tuple[Location, ...] = (
    *loc("claude-code", "global", "instructions", ".claude/CLAUDE.md"),
    *loc("claude-code", "global", "rules", ".claude/rules/**/*.md"),
    *loc("claude-code", "global", "skills", ".claude/skills/*/SKILL.md"),
    *loc("claude-code", "global", "agents", ".claude/agents/**/*.md"),
    *loc("claude-code", "global", "commands", ".claude/commands/**/*.md"),
    *loc("claude-code", "global", "settings", ".claude/settings.json"),
    *loc("claude-code", "global", "settings", ".claude/settings.local.json"),
    *loc("claude-code", "global", "mcp", ".claude.json"),
    *loc("claude-code", "repo", "instructions", "CLAUDE.md", ".claude/CLAUDE.md"),
    *loc("claude-code", "repo", "instructions", "CLAUDE.local.md"),
    *loc("claude-code", "repo", "rules", ".claude/rules/**/*.md"),
    *loc("claude-code", "repo", "skills", ".claude/skills/*/SKILL.md"),
    *loc("claude-code", "repo", "agents", ".claude/agents/**/*.md"),
    *loc("claude-code", "repo", "commands", ".claude/commands/**/*.md"),
    *loc("claude-code", "repo", "settings", ".claude/settings.json"),
    *loc("claude-code", "repo", "settings", ".claude/settings.local.json"),
    *loc("claude-code", "repo", "mcp", ".mcp.json"),
    *loc("codex", "global", "instructions", ".codex/AGENTS.md"),
    *loc("codex", "global", "skills", ".codex/skills/*/SKILL.md"),
    *loc("codex", "global", "settings", ".codex/config.toml"),
    *loc("codex", "global", "mcp", ".codex/config.toml"),
    *loc("cursor", "global", "skills", ".cursor/skills/*/SKILL.md"),
    *loc("cursor", "global", "settings", ".cursor/permissions.json"),
    *loc("cursor", "global", "mcp", ".cursor/mcp.json"),
    *loc("cursor", "repo", "instructions", ".cursorrules"),
    *loc("cursor", "repo", "rules", ".cursor/rules/**/*.mdc"),
    *loc("cursor", "repo", "skills", ".cursor/skills/*/SKILL.md"),
    *loc("cursor", "repo", "mcp", ".cursor/mcp.json"),
    *loc("shared", "global", "skills", ".agents/skills/*/SKILL.md"),
    *loc("shared", "repo", "instructions", "AGENTS.md", "GEMINI.md"),
    *loc("shared", "repo", "instructions", ".github/copilot-instructions.md"),
    *loc("shared", "repo", "skills", ".agents/skills/*/SKILL.md", ".github/skills/*/SKILL.md"),
)

NESTED: dict[str, Location] = {
    "AGENTS.md": Location("shared", "repo", "instructions", "**/AGENTS.md"),
    "CLAUDE.md": Location("claude-code", "repo", "instructions", "**/CLAUDE.md"),
}


def as_dict(value: Json) -> Mapping[str, Json]:
    return value if isinstance(value, Mapping) else {}


def as_list(value: Json) -> Sequence[Json]:
    return value if isinstance(value, list) else []


def as_str(value: Json) -> str:
    return value if isinstance(value, str) else ""


def as_int(value: Json) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def read_json(path: Path) -> Mapping[str, Json]:
    try:
        loaded: Json = json.loads(read_text(path))
    except ValueError:
        return {}
    return as_dict(loaded)


def frontmatter(text: str) -> str:
    match = re.match(r"---\r?\n(.*?)\r?\n---", text, re.DOTALL)
    return match.group(1) if match else ""


def field(block: str, name: str) -> str:
    match = re.search(rf"(?m)^{name}:[ \t]*(.*(?:\n[ \t]+.*)*)", block)
    raw = match.group(1) if match else ""
    folded = " ".join(part.strip() for part in raw.lstrip(">|+- \t").splitlines())
    return folded.strip().strip("\"'")


def normalize(path: str) -> str:
    return path.replace("\\", "/").rstrip("/").lower()


def describe_instructions(path: Path, context: Context) -> Mapping[str, Json]:
    text = read_text(path)
    return {
        "lines": len(text.splitlines()),
        "bytes": len(text.encode("utf-8")),
        "managed_blocks": sorted(set(MARKER_RE.findall(text))),
        "imports": sorted(set(IMPORT_RE.findall(text))),
        "nested": False,
    }


def describe_rule(path: Path, context: Context) -> Mapping[str, Json]:
    text = read_text(path)
    return {
        "lines": len(text.splitlines()),
        "path_scoped": bool(re.search(r"(?m)^(?:paths|globs)[ \t]*:", frontmatter(text))),
    }


def describe_skill(path: Path, context: Context) -> Mapping[str, Json]:
    text = read_text(path)
    block = frontmatter(text)
    name = field(block, "name")
    return {
        "name": name or path.parent.name,
        "dir": path.parent.name,
        "name_matches_dir": name == path.parent.name,
        "description_chars": len(field(block, "description")),
        "lines": len(text.splitlines()),
    }


def describe_named(path: Path, context: Context) -> Mapping[str, Json]:
    return {"name": path.stem}


def describe_settings(path: Path, context: Context) -> Mapping[str, Json]:
    if path.suffix == ".toml":
        return {"keys": sorted(set(TOML_KEY_RE.findall(read_text(path))))}
    data = read_json(path)
    permissions = as_dict(data.get("permissions"))
    return {
        "keys": sorted(data),
        "permission_rules": {
            rule: len(as_list(permissions.get(rule))) for rule in PERMISSION_RULES
        },
        "default_mode": as_str(permissions.get("defaultMode")),
        "hook_events": sorted(as_dict(data.get("hooks"))),
        "enabled_plugins": sorted(
            name for name, enabled in as_dict(data.get("enabledPlugins")).items() if enabled
        ),
        "marketplaces": sorted(as_dict(data.get("extraKnownMarketplaces"))),
    }


def describe_mcp(path: Path, context: Context) -> Mapping[str, Json]:
    if path.suffix == ".toml":
        names = {name.strip("\"'") for name in TOML_MCP_RE.findall(read_text(path))}
        return {"servers": sorted(names), "local_servers": []}
    data = read_json(path)
    target = normalize(context.repo.as_posix()) if context.repo else ""
    local = {
        server
        for key, project in as_dict(data.get("projects")).items()
        if target and normalize(key) == target
        for server in as_dict(as_dict(project).get("mcpServers"))
    }
    return {"servers": sorted(as_dict(data.get("mcpServers"))), "local_servers": sorted(local)}


DESCRIBERS: dict[str, Describer] = {
    "instructions": describe_instructions,
    "rules": describe_rule,
    "skills": describe_skill,
    "agents": describe_named,
    "commands": describe_named,
    "settings": describe_settings,
    "mcp": describe_mcp,
}


def display(base: Path, scope: str, path: Path) -> str:
    relative = path.relative_to(base).as_posix()
    return f"~/{relative}" if scope == "global" else relative


def scan(base: Path, scope: str, context: Context) -> list[Record]:
    return [
        Record(location, display(base, scope, path), DESCRIBERS[location.kind](path, context))
        for location in LOCATIONS
        if location.scope == scope
        for path in sorted(base.glob(location.pattern))
        if path.is_file()
    ]


def walk(repo: Path, max_depth: int) -> Iterator[tuple[Path, list[str]]]:
    for current, dirnames, filenames in os.walk(repo):
        directory = Path(current)
        depth = len(directory.relative_to(repo).parts)
        dirnames[:] = (
            sorted(d for d in dirnames if d not in IGNORED_DIRS and not d.startswith("."))
            if depth < max_depth
            else []
        )
        yield directory, sorted(filenames)


def nested_instructions(repo: Path, context: Context) -> list[Record]:
    return [
        Record(
            NESTED[name],
            display(repo, "repo", directory / name),
            {**describe_instructions(directory / name, context), "nested": True},
        )
        for directory, names in walk(repo, NESTED_DEPTH)
        if directory != repo
        for name in names
        if name in NESTED
    ]


def render(record: Record) -> Mapping[str, Json]:
    return {
        "host": record.location.host,
        "scope": record.location.scope,
        "path": record.display,
        **record.details,
    }


def always_loaded_lines(records: Sequence[Record], scope: str) -> int:
    return sum(
        as_int(record.details.get("lines"))
        for record in records
        if record.location.scope == scope
        and (
            (record.location.kind == "instructions" and not record.details.get("nested"))
            or (record.location.kind == "rules" and not record.details.get("path_scoped"))
        )
    )


def duplicate_skills(records: Sequence[Record]) -> list[Json]:
    skills = [record for record in records if record.location.kind == "skills"]
    names = sorted({as_str(record.details.get("name")) for record in skills})
    paths = {
        name: sorted(r.display for r in skills if as_str(r.details.get("name")) == name)
        for name in names
    }
    return [{"name": name, "paths": found} for name, found in paths.items() if len(found) > 1]


def plugin_summary(home: Path, records: Sequence[Record]) -> Mapping[str, Json]:
    settings = [record.details for record in records if record.location.kind == "settings"]
    known = read_json(home / ".claude" / "plugins" / "known_marketplaces.json")
    declared = {
        as_str(name) for details in settings for name in as_list(details.get("marketplaces"))
    }
    return {
        "enabled": sorted(
            {
                as_str(name)
                for details in settings
                for name in as_list(details.get("enabled_plugins"))
            }
        ),
        "marketplaces": sorted(declared | set(known)),
    }


def host_summary(home: Path, records: Sequence[Record]) -> list[Json]:
    return [
        {
            "host": host,
            "home_dir": (home / folder).is_dir(),
            "global_entries": sum(
                1 for r in records if r.location.host == host and r.location.scope == "global"
            ),
            "repo_entries": sum(
                1 for r in records if r.location.host == host and r.location.scope == "repo"
            ),
        }
        for host, folder in HOST_HOMES
    ]


def inventory(home: Path, repo: Path | None) -> dict[str, Json]:
    scannable = repo if repo and repo != home else None
    context = Context(home, scannable)
    records = [
        *scan(home, "global", context),
        *(scan(scannable, "repo", context) if scannable else []),
        *(nested_instructions(scannable, context) if scannable else []),
    ]
    grouped = {
        key: [render(record) for record in records if record.location.kind == kind]
        for kind, key in KIND_KEYS.items()
    }
    notes = [
        *(["repo is the home directory: repo scan skipped"] if repo and not scannable else []),
        "line totals do not follow @imports: add imported files' lines when judging budgets",
    ]
    return {
        "schema": SCHEMA,
        "home": home.as_posix(),
        "repo": scannable.as_posix() if scannable else None,
        "hosts": host_summary(home, records),
        **grouped,
        "plugins": plugin_summary(home, records),
        "duplicate_skill_names": duplicate_skills(records),
        "always_loaded_lines": {
            "global": always_loaded_lines(records, "global"),
            "repo": always_loaded_lines(records, "repo"),
        },
        "notes": notes,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--repo", help="Repository root to include (omit for global only).")
    parser.add_argument("--home", help="Home directory to scan (default: the user's home).")
    parser.add_argument("--out", help="Also write the JSON report to this path.")
    args = parser.parse_args(argv)

    home = Path(args.home).expanduser().resolve() if args.home else Path.home().resolve()
    repo = Path(args.repo).expanduser().resolve() if args.repo else None
    missing = next((p for p in (home, repo) if p and not p.is_dir()), None)
    if missing:
        print(json.dumps({"success": False, "error": f"not a directory: {missing.as_posix()}"}))
        return 2

    rendered = json.dumps(inventory(home, repo), indent=2)
    if args.out:
        out = Path(args.out).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
