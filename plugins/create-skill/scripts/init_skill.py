#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Scaffold a new Claude Code skill directory.

Creates the skill directory plus a SKILL.md containing portable-core
frontmatter (name + description) and the required section skeleton:
Overview / Quick Reference / a main-content stub / Common Mistakes / Notes.

Refuses to clobber: if the target directory already exists and is non-empty,
emits a structured JSON error and exits non-zero (never overwrites).

Emits structured JSON to stdout. Forward-slash paths only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FORBIDDEN_TOKENS = ("claude", "anthropic")

SKILL_TEMPLATE = """---
name: {name}
description: {description}
---

# {title}

## Overview

[TODO: 1-2 sentences explaining what this skill enables and when to use it.]

## Quick Reference

[TODO: The fastest path to using this skill — a table, command list, or
decision tree the agent can scan in seconds.]

## {main_section}

[TODO: Replace this heading and body with the first main content section.
Add code samples, concrete examples, or step-by-step procedures as needed.]

## Common Mistakes

[TODO: List the failure modes and anti-patterns to avoid when applying this
skill.]

## Notes

[TODO: Edge cases, caveats, or links to bundled references/scripts/assets.]
"""


def emit(payload: dict) -> None:
    print(json.dumps(payload))


def title_case(name: str) -> str:
    return " ".join(word.capitalize() for word in name.split("-"))


def to_posix(p: Path) -> str:
    return p.as_posix()


def validate_name(name: str) -> str | None:
    if not name:
        return "name is empty"
    if len(name) > 64:
        return f"name too long ({len(name)} chars); maximum is 64"
    if not NAME_RE.match(name):
        return (
            f"name '{name}' must be kebab-case (lowercase letters, digits, "
            "single hyphens between segments)"
        )
    lowered = name.lower()
    for token in FORBIDDEN_TOKENS:
        if token in lowered:
            return f"name must not contain '{token}'"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--name",
        required=True,
        help="Kebab-case skill name (lowercase + hyphens, <=64 chars).",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory in which to create the skill directory.",
    )
    parser.add_argument(
        "--description",
        default=None,
        help="Optional skill description for the frontmatter.",
    )
    args = parser.parse_args()

    name = args.name.strip()
    name_error = validate_name(name)
    if name_error:
        emit({"success": False, "error": "invalid_name", "message": name_error})
        return 1

    output_dir = Path(args.output_dir).expanduser().resolve()
    skill_dir = output_dir / name

    if skill_dir.exists() and any(skill_dir.iterdir()):
        emit(
            {
                "success": False,
                "error": "output_dir_exists_nonempty",
                "skill_dir": to_posix(skill_dir),
                "hint": "Ask the user whether to overwrite, pick a different path, or abort.",
            }
        )
        return 2

    description = args.description or (
        "[TODO: Describe what the skill does and WHEN to use it — specific "
        "scenarios, file types, or tasks that trigger it.]"
    )

    skill_dir.mkdir(parents=True, exist_ok=True)

    skill_md = skill_dir / "SKILL.md"
    content = SKILL_TEMPLATE.format(
        name=name,
        description=description,
        title=title_case(name),
        main_section="Main Content",
    )
    skill_md.write_text(content)

    emit(
        {
            "success": True,
            "skill_dir": to_posix(skill_dir),
            "files_created": [to_posix(skill_md)],
        }
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
