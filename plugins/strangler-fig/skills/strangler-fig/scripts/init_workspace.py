#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "cyclopts>=3.9.0",
# ]
# ///
"""Initialize the workspace for a /strangler-fig run.

Creates the artifact directory (specs, harness, parity report) and a clean, empty
greenfield build directory. The greenfield directory deliberately contains NO legacy
code — that is the structural context firewall.

Both directories are created under a base output directory (default: a `.strangler-fig`
folder in the current working directory). Override with --out-dir. The greenfield
directory is created as a sibling of the legacy repo so it never overlaps it.

Usage:
    uv run scripts/init_workspace.py <repo_path> <scope_slug> [--out-dir DIR] [--no-greenfield]
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from cyclopts import App

app = App()


@app.default
def main(
    repo_path: Path,
    scope_slug: str,
    out_dir: Path = Path(".strangler-fig"),
    greenfield: bool = True,
) -> None:
    """Create the artifact and greenfield directories for a strangler-fig run.

    Args:
        repo_path: Path to the legacy repo containing the scoped code.
        scope_slug: Short kebab-case identifier for this run (e.g. "order-pricing").
        out_dir: Base directory for run artifacts and the greenfield build. Defaults to
            a `.strangler-fig` directory under the current working directory.
        greenfield: Create the clean greenfield build directory (--no-greenfield to skip,
            e.g. for distill mode).
    """
    repo_path = repo_path.expanduser().resolve()
    out_dir = out_dir.expanduser().resolve()
    result: dict = {"scope_slug": scope_slug}

    if not repo_path.is_dir():
        print(json.dumps({"success": False, "error": f"Repo not found: {repo_path}"}))
        return

    artifact_dir = out_dir / "runs" / scope_slug
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "characterization-harness").mkdir(exist_ok=True)
        result["artifact_dir"] = str(artifact_dir)
    except OSError as e:
        print(json.dumps({"success": False, "error": f"Artifact dir failed: {e}"}))
        return

    if greenfield:
        greenfield_dir = out_dir / "greenfield" / f"{repo_path.name}-{scope_slug}"
        if greenfield_dir.exists() and any(greenfield_dir.iterdir()):
            print(
                json.dumps(
                    {
                        "success": False,
                        "error": f"Greenfield dir exists and is not empty: {greenfield_dir}. "
                        "The firewall requires a clean directory — remove it or pick a new slug.",
                    }
                )
            )
            return
        try:
            greenfield_dir.mkdir(parents=True, exist_ok=True)
            git = subprocess.run(
                ["git", "init", str(greenfield_dir)],
                capture_output=True,
                text=True,
            )
            result["greenfield_dir"] = str(greenfield_dir)
            result["git_init"] = "ok" if git.returncode == 0 else git.stderr.strip()
            result["firewall_note"] = (
                "Greenfield dir contains NO legacy code. Do not copy legacy source into it. "
                "Spawn the builder agent with this as its working directory."
            )
        except OSError as e:
            print(json.dumps({"success": False, "error": f"Greenfield dir failed: {e}"}))
            return

    result["success"] = True
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    app()
