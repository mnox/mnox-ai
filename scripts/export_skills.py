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
ENGINE_MANIFEST = "engine.json"
ENGINES_SUBDIR = ".engines"


@dataclass(frozen=True)
class Skill:
    name: str
    path: Path
    plugin: str
    plugin_path: Path


def discover_skills() -> list[Skill]:
    skills: list[Skill] = []
    for plugin_dir in sorted(PLUGINS_DIR.iterdir()):
        skills_dir = plugin_dir / "skills"
        if not skills_dir.is_dir():
            continue
        for skill_dir in sorted(skills_dir.iterdir()):
            if (skill_dir / "SKILL.md").is_file():
                skills.append(
                    Skill(
                        name=skill_dir.name,
                        path=skill_dir,
                        plugin=plugin_dir.name,
                        plugin_path=plugin_dir,
                    )
                )
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


def bundle_engines(output_dir: Path, skills: list[Skill], overwrite: bool) -> list[dict]:
    """Co-locate each contributing plugin's engine assets next to the exported
    skills so they are self-contained on hosts that don't export CLAUDE_PLUGIN_ROOT.

    A plugin opts in by shipping an `engine.json` declaring the env var that names
    its home and the relative paths to copy. We copy those paths into
    `<output>/.engines/<plugin>/` and return one record per bundled engine.
    """
    engines: list[dict] = []
    seen: set[str] = set()
    for skill in skills:
        if skill.plugin in seen:
            continue
        manifest_path = skill.plugin_path / ENGINE_MANIFEST
        if not manifest_path.is_file():
            continue
        seen.add(skill.plugin)
        spec = json.loads(manifest_path.read_text(encoding="utf-8"))
        home_env = spec.get("home_env")
        rel_paths = spec.get("paths", [])
        if not home_env or not rel_paths:
            raise SystemExit(f"{manifest_path}: engine.json needs both 'home_env' and 'paths'")

        engine_home = output_dir / ENGINES_SUBDIR / skill.plugin
        if engine_home.exists():
            if not overwrite:
                raise SystemExit(f"Refusing to overwrite existing engine dir: {engine_home}")
            shutil.rmtree(engine_home)
        engine_home.mkdir(parents=True)
        for rel in rel_paths:
            src = skill.plugin_path / rel
            if not src.exists():
                continue
            dest = engine_home / rel
            if src.is_dir():
                shutil.copytree(src, dest)
            else:
                shutil.copy2(src, dest)
        engines.append(
            {
                "plugin": skill.plugin,
                "home_env": home_env,
                "home": f"{ENGINES_SUBDIR}/{skill.plugin}",
            }
        )
    return engines


def write_manifest(output_dir: Path, skills: list[Skill], mode: str, engines: list[dict]) -> None:
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
        "engines": engines,
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
    parser.add_argument(
        "--with-engine",
        action="store_true",
        help="Co-locate each contributing plugin's engine assets under "
        "<output>/.engines/<plugin>/ so engine-backed skills (e.g. config-chunks) "
        "are self-contained on non-Claude hosts.",
    )
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

    engines = bundle_engines(output_dir, skills, args.overwrite) if args.with_engine else []
    write_manifest(output_dir, skills, args.mode, engines)
    result = {
        "success": True,
        "output_dir": str(output_dir),
        "skills": [s.name for s in skills],
        "engines": engines,
    }
    print(json.dumps(result, indent=2))
    # Engine-backed skills need their home env var set on non-Claude hosts.
    for engine in engines:
        abs_home = output_dir / engine["home"]
        print(f"\n# {engine['plugin']} engine bundled — point the skills at it:", file=sys.stderr)
        print(f"export {engine['home_env']}={abs_home}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        print(f"export_skills.py: {exc}", file=sys.stderr)
        raise SystemExit(1)
