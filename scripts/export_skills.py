#!/usr/bin/env python3
"""Export canonical mnox-ai skills into a standard Agent Skills directory."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = REPO_ROOT / "plugins"
MANIFEST_NAME = "skills-manifest.json"


@dataclass(frozen=True)
class Skill:
    name: str
    path: Path
    plugin: str


def discover_skills() -> list[Skill]:
    skills: list[Skill] = []
    for plugin_dir in sorted(PLUGINS_DIR.iterdir()):
        skills_dir = plugin_dir / "skills"
        if not skills_dir.is_dir():
            continue
        for skill_dir in sorted(skills_dir.iterdir()):
            if (skill_dir / "SKILL.md").is_file():
                skills.append(Skill(name=skill_dir.name, path=skill_dir, plugin=plugin_dir.name))
    return skills


def select_skills(all_skills: list[Skill], requested: list[str]) -> list[Skill]:
    if not requested:
        return all_skills
    by_name = {skill.name: skill for skill in all_skills}
    missing = sorted(set(requested) - set(by_name))
    if missing:
        raise SystemExit(f"Unknown skill(s): {', '.join(missing)}")
    return [by_name[name] for name in requested]


def copy_skill(skill: Skill, target: Path, overwrite: bool) -> None:
    if target.exists():
        if not overwrite:
            raise SystemExit(f"Refusing to overwrite existing skill directory: {target}")
        if target.is_symlink() or target.is_file():
            target.unlink()
        else:
            shutil.rmtree(target)
    shutil.copytree(skill.path, target)


def symlink_skill(skill: Skill, target: Path, overwrite: bool) -> None:
    if target.exists() or target.is_symlink():
        if not overwrite:
            raise SystemExit(f"Refusing to overwrite existing skill path: {target}")
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()
    target.symlink_to(skill.path)


def write_manifest(output_dir: Path, skills: list[Skill], mode: str) -> None:
    manifest = {
        "schema": "mnox-ai.skills-export.v1",
        "mode": mode,
        "source": str(REPO_ROOT),
        "skills": [
            {
                "name": skill.name,
                "plugin": skill.plugin,
                "source": str(skill.path.relative_to(REPO_ROOT)),
                "target": skill.name,
            }
            for skill in skills
        ],
    }
    (output_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="Destination skills directory.")
    parser.add_argument(
        "--skill",
        action="append",
        default=[],
        help="Skill name to export. Repeat to export a subset. Defaults to all skills.",
    )
    parser.add_argument("--mode", choices=("copy", "symlink"), default="copy")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing exported skill directories.")
    parser.add_argument("--list", action="store_true", help="List discovered skills as JSON and exit.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    all_skills = discover_skills()
    skills = select_skills(all_skills, args.skill)

    if args.list:
        print(
            json.dumps(
                [
                    {
                        "name": skill.name,
                        "plugin": skill.plugin,
                        "path": str(skill.path.relative_to(REPO_ROOT)),
                    }
                    for skill in skills
                ],
                indent=2,
            )
        )
        return 0

    if args.output_dir is None:
        raise SystemExit("--output-dir is required unless --list is used")

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    for skill in skills:
        target = output_dir / skill.name
        if args.mode == "copy":
            copy_skill(skill, target, args.overwrite)
        else:
            symlink_skill(skill, target, args.overwrite)

    write_manifest(output_dir, skills, args.mode)
    print(json.dumps({"success": True, "output_dir": str(output_dir), "skills": [s.name for s in skills]}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        print(f"export_skills.py: {exc}", file=sys.stderr)
        raise SystemExit(1)
