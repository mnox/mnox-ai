#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Statically verify the artifacts an ai-setup manifest says were applied.

For every manifest item whose status is "applied" or "verified", runs its
declared checks (path exists, JSON parses, a skill is well-formed, a string or
marker is present, a line budget holds) and reports pass / fail / warn per
check. It also confirms every core capability slot is filled by an applied
item or explicitly waived, and that no two skills share a name.

Checks of type "command" are never executed here: they are reported as pending
for the agent to run under the host's own permission prompts. Exits 1 if any
check fails, 2 if the manifest cannot be read.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

Json = Mapping[str, "Json"] | Sequence["Json"] | str | int | float | bool | None

SCHEMA = "ai-setup.manifest.v1"
ACTIVE = frozenset({"applied", "verified"})
STATUSES = frozenset({"planned", "applied", "verified", "failed", "skipped", "needs-human"})
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_SKILL_LINES = 500
MAX_NAME = 64
MAX_DESCRIPTION = 1024


@dataclass(frozen=True)
class Result:
    item: str
    check: str
    status: str
    message: str


@dataclass(frozen=True)
class Roots:
    root: Path
    home: Path


Check = Callable[[str, Path, Json], list[Result]]


def as_dict(value: Json) -> Mapping[str, Json]:
    return value if isinstance(value, Mapping) else {}


def as_list(value: Json) -> Sequence[Json]:
    return value if isinstance(value, list) else []


def as_str(value: Json) -> str:
    return value if isinstance(value, str) else ""


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None


def resolve(raw: str, roots: Roots) -> Path:
    if raw == "~" or raw.startswith("~/"):
        return roots.home / raw[2:]
    path = Path(raw)
    return path if path.is_absolute() else roots.root / path


def verdict(
    item: str, check: str, ok: bool, passed: str, failed: str, miss: str = "fail"
) -> Result:
    return Result(item, check, "pass" if ok else miss, passed if ok else failed)


def frontmatter(text: str) -> str:
    match = re.match(r"---\r?\n(.*?)\r?\n---", text, re.DOTALL)
    return match.group(1) if match else ""


def field(block: str, name: str) -> str:
    match = re.search(rf"(?m)^{name}:[ \t]*(.*(?:\n[ \t]+.*)*)", block)
    raw = match.group(1) if match else ""
    folded = " ".join(part.strip() for part in raw.lstrip(">|+- \t").splitlines())
    return folded.strip().strip("\"'")


def check_exists(item: str, path: Path, value: Json) -> list[Result]:
    shown = path.as_posix()
    return [verdict(item, "exists", path.exists(), f"{shown} exists", f"missing: {shown}")]


def check_json(item: str, path: Path, value: Json) -> list[Result]:
    text = read_text(path)
    shown = path.as_posix()
    if text is None:
        return [Result(item, "json", "fail", f"missing: {shown}")]
    try:
        json.loads(text)
    except ValueError as exc:
        return [Result(item, "json", "fail", f"{shown} is not valid JSON: {exc}")]
    return [Result(item, "json", "pass", f"{shown} parses")]


def check_contains(item: str, path: Path, value: Json) -> list[Result]:
    text = read_text(path)
    needle = as_str(value)
    shown = path.as_posix()
    if text is None:
        return [Result(item, "contains", "fail", f"missing: {shown}")]
    return [
        verdict(
            item,
            "contains",
            bool(needle) and needle in text,
            f"{shown} contains {needle!r}",
            f"{shown} does not contain {needle!r}",
        )
    ]


def check_max_lines(item: str, path: Path, value: Json) -> list[Result]:
    text = read_text(path)
    shown = path.as_posix()
    budget = value if isinstance(value, int) and not isinstance(value, bool) else 0
    if text is None:
        return [Result(item, "max_lines", "fail", f"missing: {shown}")]
    lines = len(text.splitlines())
    return [
        verdict(
            item,
            "max_lines",
            lines <= budget,
            f"{shown} is {lines} lines (budget {budget})",
            f"{shown} is {lines} lines, over its {budget}-line budget",
            "warn",
        )
    ]


def check_skill(item: str, path: Path, value: Json) -> list[Result]:
    skill_md = path / "SKILL.md"
    text = read_text(skill_md)
    shown = path.as_posix()
    if text is None:
        return [Result(item, "skill", "fail", f"no SKILL.md in {shown}")]
    block = frontmatter(text)
    name = field(block, "name")
    description = field(block, "description")
    lines = len(text.splitlines())
    return [
        verdict(
            item,
            "skill",
            bool(block),
            f"{shown}: frontmatter present",
            f"{shown}: no frontmatter",
        ),
        verdict(
            item,
            "skill",
            bool(NAME_RE.match(name)) and len(name) <= MAX_NAME,
            f"{shown}: name {name!r} is valid",
            f"{shown}: name {name!r} is not kebab-case within {MAX_NAME} chars",
        ),
        verdict(
            item,
            "skill",
            name == path.name,
            f"{shown}: name matches its directory",
            f"{shown}: name {name!r} does not match directory {path.name!r}",
        ),
        verdict(
            item,
            "skill",
            0 < len(description) <= MAX_DESCRIPTION,
            f"{shown}: description is {len(description)} chars",
            f"{shown}: description is {len(description)} chars (need 1-{MAX_DESCRIPTION})",
        ),
        verdict(
            item,
            "skill",
            lines <= MAX_SKILL_LINES,
            f"{shown}: SKILL.md is {lines} lines",
            f"{shown}: SKILL.md is {lines} lines (move detail into references/)",
            "warn",
        ),
    ]


def check_command(item: str, path: Path, value: Json) -> list[Result]:
    return [Result(item, "command", "pending", f"agent must run: {as_str(value)}")]


CHECKS: dict[str, Check] = {
    "exists": check_exists,
    "json": check_json,
    "contains": check_contains,
    "max_lines": check_max_lines,
    "skill": check_skill,
    "command": check_command,
}


def run_check(item: str, check: Mapping[str, Json], roots: Roots) -> list[Result]:
    kind = as_str(check.get("type"))
    runner = CHECKS.get(kind)
    if runner is None:
        return [Result(item, kind or "unknown", "fail", f"unknown check type {kind!r}")]
    return runner(item, resolve(as_str(check.get("path")), roots), check.get("value"))


def item_results(item: Mapping[str, Json], roots: Roots) -> list[Result]:
    name = as_str(item.get("id")) or "<no id>"
    status = as_str(item.get("status"))
    checks = [as_dict(check) for check in as_list(item.get("checks"))]
    if status not in STATUSES:
        return [Result(name, "status", "fail", f"unknown status {status!r}")]
    if status == "failed":
        return [Result(name, "status", "fail", as_str(item.get("note")) or "item failed to apply")]
    if status == "needs-human":
        step = as_str(item.get("human_step")) or "human step not described"
        return [Result(name, "status", "pending", f"needs the engineer: {step}")]
    if status not in ACTIVE:
        return []
    if not checks:
        return [Result(name, "checks", "warn", "applied with no checks declared: unproven")]
    return [result for check in checks for result in run_check(name, check, roots)]


def slot_results(manifest: Mapping[str, Json]) -> list[Result]:
    statuses = {
        as_str(item.get("id")): as_str(item.get("status"))
        for item in map(as_dict, as_list(manifest.get("items")))
    }

    def judge(slot: Mapping[str, Json]) -> Result:
        name = f"slot:{as_str(slot.get('id'))}"
        raw = slot.get("filled_by")
        fillers = [as_str(raw)] if isinstance(raw, str) else [as_str(x) for x in as_list(raw)]
        states = {statuses.get(filler, "missing") for filler in fillers}
        waived = as_str(slot.get("waived"))
        if states & ACTIVE:
            return Result(name, "slot", "pass", f"filled by {', '.join(fillers)}")
        if "needs-human" in states:
            return Result(name, "slot", "pending", f"waiting on a human step: {', '.join(fillers)}")
        if waived:
            return Result(name, "slot", "warn", f"waived: {waived}")
        return Result(name, "slot", "fail", "core slot is neither filled nor waived")

    return [
        judge(slot)
        for slot in map(as_dict, as_list(manifest.get("slots")))
        if as_str(slot.get("priority")) == "core"
    ]


def duplicate_skill_results(manifest: Mapping[str, Json], roots: Roots) -> list[Result]:
    names = Counter(
        resolve(as_str(check.get("path")), roots).name
        for item in map(as_dict, as_list(manifest.get("items")))
        if as_str(item.get("status")) in ACTIVE
        for check in map(as_dict, as_list(item.get("checks")))
        if as_str(check.get("type")) == "skill"
    )
    return [
        Result("manifest", "unique_skills", "fail", f"{count} skills are named {name!r}")
        for name, count in sorted(names.items())
        if count > 1
    ]


def structure_results(manifest: Mapping[str, Json]) -> list[Result]:
    ids = Counter(as_str(item.get("id")) for item in map(as_dict, as_list(manifest.get("items"))))
    schema = as_str(manifest.get("schema"))
    return [
        verdict(
            "manifest",
            "schema",
            schema == SCHEMA,
            f"schema is {SCHEMA}",
            f"schema is {schema!r}, expected {SCHEMA!r}",
        ),
        *(
            Result("manifest", "unique_ids", "fail", f"item id {name!r} appears {count} times")
            for name, count in sorted(ids.items())
            if count > 1 or not name
        ),
    ]


def verify(manifest: Mapping[str, Json], roots: Roots) -> list[Result]:
    return [
        *structure_results(manifest),
        *(
            result
            for item in map(as_dict, as_list(manifest.get("items")))
            for result in item_results(item, roots)
        ),
        *slot_results(manifest),
        *duplicate_skill_results(manifest, roots),
    ]


def report(manifest_path: Path, results: Sequence[Result]) -> dict[str, Json]:
    counts = Counter(result.status for result in results)
    return {
        "success": counts["fail"] == 0,
        "manifest": manifest_path.as_posix(),
        "summary": {status: counts[status] for status in ("pass", "fail", "warn", "pending")},
        "results": [
            {"item": r.item, "check": r.check, "status": r.status, "message": r.message}
            for r in results
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--manifest", required=True, help="Path to the setup manifest JSON.")
    parser.add_argument("--root", help="Base for relative paths (default: profile.repo or cwd).")
    parser.add_argument("--home", help="Directory that ~ expands to (default: the user's home).")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest).expanduser().resolve()
    text = read_text(manifest_path)
    try:
        loaded: Json = json.loads(text) if text is not None else None
    except ValueError:
        loaded = None
    if not isinstance(loaded, Mapping):
        shown = manifest_path.as_posix()
        print(json.dumps({"success": False, "error": f"unreadable manifest: {shown}"}))
        return 2

    declared_root = as_str(as_dict(loaded.get("profile")).get("repo"))
    roots = Roots(
        root=Path(args.root or declared_root or ".").expanduser().resolve(),
        home=Path(args.home).expanduser().resolve() if args.home else Path.home(),
    )
    outcome = report(manifest_path, verify(loaded, roots))
    print(json.dumps(outcome, indent=2))
    return 0 if outcome["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
