#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Deterministic structural lint for a Claude Code skill.

Mechanical structure only — no design-quality judgment (that is a separate
review pass). Checks frontmatter, naming, required sections, line budget,
forward-slash paths, and forbidden files.

Frontmatter is parsed with a minimal stdlib regex parser (no PyYAML dep).

Emits structured JSON to stdout:
    {"success": bool, "errors": [...], "warnings": [...], "checks_run": N}
Each finding: {"id": "...", "severity": "error|warning", "message": "..."}
Exits 1 if any errors are present, 0 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FORBIDDEN_TOKENS = ("claude", "anthropic")
FORBIDDEN_FILES = ("README.md", "CHANGELOG.md")
MAX_LINES = 500


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse simple single-line YAML frontmatter via regex (no PyYAML)."""
    result: dict[str, str] = {}
    for line in text.strip().split("\n"):
        match = re.match(r'^([A-Za-z0-9_-]+):\s*"?(.*?)"?\s*$', line)
        if match:
            key, value = match.groups()
            result[key] = value.strip()
    return result


def validate(skill_dir: Path) -> tuple[list[dict], list[dict], int]:
    errors: list[dict] = []
    warnings: list[dict] = []
    checks = 0

    def err(check_id: str, message: str) -> None:
        errors.append({"id": check_id, "severity": "error", "message": message})

    def warn(check_id: str, message: str) -> None:
        warnings.append({"id": check_id, "severity": "warning", "message": message})

    # Resolve the SKILL.md target (dir or direct file).
    if skill_dir.is_file():
        skill_md = skill_dir
        skill_root = skill_dir.parent
    else:
        skill_md = skill_dir / "SKILL.md"
        skill_root = skill_dir

    checks += 1  # skill_md_exists
    if not skill_md.exists():
        err("skill_md_exists", f"SKILL.md not found at {skill_md.as_posix()}")
        return errors, warnings, checks

    content = skill_md.read_text()

    # Frontmatter presence + structure.
    checks += 1  # frontmatter_present
    if not content.startswith("---"):
        err("frontmatter_present", "No YAML frontmatter found (file must start with ---)")
        return errors, warnings, checks

    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    checks += 1  # frontmatter_parses
    if not match:
        err("frontmatter_parses", "Invalid frontmatter (missing closing ---)")
        return errors, warnings, checks

    frontmatter = parse_frontmatter(match.group(1))
    body = content[match.end():]

    # name checks.
    name = frontmatter.get("name", "").strip()
    checks += 1  # name_present
    if not name:
        err("name_present", "Missing required 'name' field in frontmatter")
    else:
        checks += 1  # name_kebab_case
        if not NAME_RE.match(name):
            err(
                "name_kebab_case",
                f"Name '{name}' must be kebab-case (lowercase, digits, single hyphens)",
            )
        checks += 1  # name_length
        if len(name) > 64:
            err("name_length", f"Name too long ({len(name)} chars); maximum is 64")
        checks += 1  # name_no_forbidden_token
        lowered = name.lower()
        hit = next((t for t in FORBIDDEN_TOKENS if t in lowered), None)
        if hit:
            err("name_no_forbidden_token", f"Name must not contain '{hit}'")

    # description checks.
    description = frontmatter.get("description", "").strip()
    checks += 1  # description_present
    if not description:
        err("description_present", "Missing required 'description' field in frontmatter")
    else:
        checks += 1  # description_length
        if len(description) > 1024:
            err(
                "description_length",
                f"Description too long ({len(description)} chars); maximum is 1024",
            )

    # Required sections.
    checks += 1  # section_overview
    if "## Overview" not in body:
        err("section_overview", "Missing required '## Overview' section")

    checks += 1  # section_quick_reference
    if "## Quick Reference" not in body:
        err("section_quick_reference", "Missing required '## Quick Reference' section")

    # At least one main-content H2 beyond the mandated ones.
    checks += 1  # section_main_content
    reserved = {
        "Overview",
        "Quick Reference",
        "Common Mistakes",
        "Notes",
    }
    h2_titles = [m.strip() for m in re.findall(r"^##\s+(.+?)\s*$", body, re.MULTILINE)]
    main_content = [h for h in h2_titles if h not in reserved]
    if not main_content:
        err(
            "section_main_content",
            "No main-content H2 section found (need at least one beyond the required headers)",
        )

    checks += 1  # section_common_mistakes
    if "## Common Mistakes" not in body:
        err("section_common_mistakes", "Missing required '## Common Mistakes' section")

    # Line budget (warning only).
    checks += 1  # line_budget
    line_count = content.count("\n") + 1
    if line_count > MAX_LINES:
        warn("line_budget", f"SKILL.md is {line_count} lines (recommended max {MAX_LINES})")

    # Forward-slash paths: flag Windows-style backslash path separators.
    checks += 1  # forward_slash_paths
    if re.search(r"\\[A-Za-z0-9_.\-]", content):
        warn(
            "forward_slash_paths",
            "Backslash path separators detected; use forward slashes for portability",
        )

    # Forbidden files inside the skill dir.
    checks += 1  # forbidden_files
    for forbidden in FORBIDDEN_FILES:
        if (skill_root / forbidden).exists():
            err("forbidden_files", f"Forbidden file present in skill dir: {forbidden}")

    return errors, warnings, checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skill-dir",
        required=True,
        help="Path to a skill directory or a SKILL.md file.",
    )
    args = parser.parse_args()

    target = Path(args.skill_dir).expanduser().resolve()
    if not target.exists():
        print(
            json.dumps(
                {
                    "success": False,
                    "errors": [
                        {
                            "id": "path_exists",
                            "severity": "error",
                            "message": f"Path not found: {target.as_posix()}",
                        }
                    ],
                    "warnings": [],
                    "checks_run": 1,
                }
            )
        )
        return 1

    errors, warnings, checks = validate(target)
    success = len(errors) == 0
    print(
        json.dumps(
            {
                "success": success,
                "errors": errors,
                "warnings": warnings,
                "checks_run": checks,
            }
        )
    )
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
