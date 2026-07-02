#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Package a Claude Code skill directory into a distributable zip archive.

Excludes junk (.DS_Store, __pycache__, .git). Uses stdlib zipfile.

Emits structured JSON to stdout:
    {"success": true, "archive": "...", "file_count": N, "bytes": N}
Exits non-zero on failure. Forward-slash paths only.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

EXCLUDED_NAMES = {".DS_Store", "__pycache__", ".git"}


def emit(payload: dict) -> None:
    print(json.dumps(payload))


def is_excluded(file_path: Path, skill_root: Path) -> bool:
    """True if any path segment (relative to the skill root) is junk."""
    rel = file_path.relative_to(skill_root)
    return any(part in EXCLUDED_NAMES for part in rel.parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skill-dir",
        required=True,
        help="Path to the skill directory to package.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output zip path (defaults to <skill-name>.zip in the cwd).",
    )
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir).expanduser().resolve()

    if not skill_dir.exists():
        emit({"success": False, "error": "skill_dir_not_found", "skill_dir": skill_dir.as_posix()})
        return 1
    if not skill_dir.is_dir():
        emit({"success": False, "error": "skill_dir_not_a_directory", "skill_dir": skill_dir.as_posix()})
        return 1
    if not (skill_dir / "SKILL.md").exists():
        emit({"success": False, "error": "skill_md_missing", "skill_dir": skill_dir.as_posix()})
        return 1

    if args.output:
        archive = Path(args.output).expanduser().resolve()
        archive.parent.mkdir(parents=True, exist_ok=True)
    else:
        archive = Path.cwd() / f"{skill_dir.name}.zip"

    file_count = 0
    try:
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in sorted(skill_dir.rglob("*")):
                if not file_path.is_file():
                    continue
                if is_excluded(file_path, skill_dir):
                    continue
                arcname = file_path.relative_to(skill_dir.parent).as_posix()
                zf.write(file_path, arcname)
                file_count += 1
    except OSError as exc:
        emit({"success": False, "error": "archive_write_failed", "message": str(exc)})
        return 1

    emit(
        {
            "success": True,
            "archive": archive.as_posix(),
            "file_count": file_count,
            "bytes": archive.stat().st_size,
        }
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
