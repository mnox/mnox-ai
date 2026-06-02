"""Tests for plugins/strangler-fig/skills/strangler-fig/scripts/init_workspace.py.

The script depends on the third-party ``cyclopts`` package (not installed in the
test env) and is normally run via ``uv run``. To test its real logic hermetically
we inject a minimal stub ``cyclopts`` module into sys.modules BEFORE loading the
script. The stub's ``App`` + ``@app.default`` decorator simply return the wrapped
function unchanged, so we can call ``main(...)`` directly with plain args.

git is invoked for the greenfield dir; git is available in the environment and we
run it against a real temp dir, so the test stays hermetic (no network, temp only).
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = (
    REPO_ROOT
    / "plugins"
    / "strangler-fig"
    / "skills"
    / "strangler-fig"
    / "scripts"
    / "init_workspace.py"
)


def _install_cyclopts_stub() -> None:
    if "cyclopts" in sys.modules and getattr(sys.modules["cyclopts"], "_mnoxai_stub", False):
        return
    stub = ModuleType("cyclopts")
    stub._mnoxai_stub = True  # marker so we don't clobber a real install

    class App:
        def default(self, func):
            return func  # identity: leaves main() directly callable

        def __call__(self, *args, **kwargs):  # pragma: no cover - CLI entry, unused in tests
            return None

    stub.App = App
    sys.modules["cyclopts"] = stub


def _load_init_workspace() -> ModuleType:
    _install_cyclopts_stub()
    spec = importlib.util.spec_from_file_location("_mnoxai_init_workspace", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["_mnoxai_init_workspace"] = module
    spec.loader.exec_module(module)
    return module


iw = _load_init_workspace()


def _run_main(**kwargs) -> dict:
    buf = StringIO()
    with redirect_stdout(buf):
        iw.main(**kwargs)
    return json.loads(buf.getvalue().strip())


@unittest.skipIf(shutil.which("git") is None, "git not available")
class InitWorkspaceTest(unittest.TestCase):
    def test_happy_path_creates_artifact_and_greenfield(self) -> None:
        with TemporaryDirectory() as d:
            base = Path(d)
            repo = base / "legacy-repo"
            repo.mkdir()
            out = base / ".strangler-fig"
            result = _run_main(repo_path=repo, scope_slug="order-pricing", out_dir=out)

            self.assertTrue(result["success"])
            # script resolves out_dir, so compare against the resolved path
            resolved_out = out.resolve()
            artifact = resolved_out / "runs" / "order-pricing"
            self.assertTrue(artifact.is_dir())
            self.assertTrue((artifact / "characterization-harness").is_dir())
            greenfield = resolved_out / "greenfield" / "legacy-repo-order-pricing"
            self.assertTrue(greenfield.is_dir())
            self.assertEqual(result["greenfield_dir"], str(greenfield))
            self.assertEqual(result["git_init"], "ok")
            self.assertTrue((greenfield / ".git").is_dir())
            self.assertIn("firewall_note", result)

    def test_no_greenfield_skips_build_dir(self) -> None:
        with TemporaryDirectory() as d:
            base = Path(d)
            repo = base / "legacy-repo"
            repo.mkdir()
            out = base / ".strangler-fig"
            result = _run_main(
                repo_path=repo, scope_slug="distill", out_dir=out, greenfield=False
            )
            self.assertTrue(result["success"])
            self.assertNotIn("greenfield_dir", result)
            self.assertFalse((out / "greenfield").exists())
            self.assertTrue((out / "runs" / "distill").is_dir())

    def test_missing_repo_errors(self) -> None:
        with TemporaryDirectory() as d:
            base = Path(d)
            out = base / ".strangler-fig"
            result = _run_main(
                repo_path=base / "does-not-exist", scope_slug="x", out_dir=out
            )
            self.assertFalse(result["success"])
            self.assertIn("Repo not found", result["error"])

    def test_nonempty_greenfield_aborts_firewall(self) -> None:
        with TemporaryDirectory() as d:
            base = Path(d)
            repo = base / "legacy-repo"
            repo.mkdir()
            out = base / ".strangler-fig"
            greenfield = out / "greenfield" / "legacy-repo-dup"
            greenfield.mkdir(parents=True)
            (greenfield / "leftover.txt").write_text("x", encoding="utf-8")
            result = _run_main(repo_path=repo, scope_slug="dup", out_dir=out)
            self.assertFalse(result["success"])
            self.assertIn("not empty", result["error"])


if __name__ == "__main__":
    unittest.main()
