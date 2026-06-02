"""Tests for plugins/curriculum/skills/curriculum/scripts/scaffold.py.

scaffold.py copies template assets from the skill's own assets/ dir. To stay
hermetic we monkeypatch the module's ASSETS_DIR to a temp fixture rather than
depending on the real repo assets.
"""

from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from tests._loader import load_script

sc = load_script("scaffold")


class ScaffoldMainTest(unittest.TestCase):
    def _make_assets(self, base: Path) -> Path:
        assets = base / "assets"
        (assets / "assessments").mkdir(parents=True)
        (assets / "curriculum-meta.md").write_text("META", encoding="utf-8")
        (assets / "assessments" / "misconceptions.md").write_text("MISCON", encoding="utf-8")
        return assets

    def _run(self, output_dir: Path) -> dict:
        buf = io.StringIO()
        argv = ["scaffold.py", "--output-dir", str(output_dir)]
        old = sys.argv
        sys.argv = argv
        try:
            with redirect_stdout(buf):
                self._code = sc.main()
        finally:
            sys.argv = old
        return json.loads(buf.getvalue().strip())

    def test_happy_path_creates_full_tree(self) -> None:
        with TemporaryDirectory() as d:
            base = Path(d)
            sc.ASSETS_DIR = self._make_assets(base)
            out = base / "curriculum"
            result = self._run(out)
            self.assertEqual(self._code, 0)
            self.assertTrue(result["success"])
            self.assertTrue((out / "modules").is_dir())
            self.assertTrue((out / "assessments").is_dir())
            self.assertEqual((out / "curriculum-meta.md").read_text(encoding="utf-8"), "META")
            self.assertEqual(
                (out / "assessments" / "misconceptions.md").read_text(encoding="utf-8"),
                "MISCON",
            )
            jsonl_text = (out / "assessments" / "responses.jsonl").read_text(encoding="utf-8")
            self.assertEqual(jsonl_text, "")
            progress = (out / "assessments" / "progress.md").read_text(encoding="utf-8")
            self.assertIn("# Progress Tracker", progress)
            self.assertIn("Initialized on", progress)

    def test_nonempty_output_dir_aborts(self) -> None:
        with TemporaryDirectory() as d:
            base = Path(d)
            sc.ASSETS_DIR = self._make_assets(base)
            out = base / "curriculum"
            out.mkdir()
            (out / "stuff.txt").write_text("existing", encoding="utf-8")
            result = self._run(out)
            self.assertEqual(self._code, 2)
            self.assertEqual(result["error"], "output_dir_exists_nonempty")
            # must not have clobbered the existing file
            self.assertTrue((out / "stuff.txt").exists())

    def test_missing_asset_errors(self) -> None:
        with TemporaryDirectory() as d:
            base = Path(d)
            # point ASSETS_DIR at an empty dir -> missing template files
            empty_assets = base / "empty-assets"
            empty_assets.mkdir()
            sc.ASSETS_DIR = empty_assets
            out = base / "curriculum"
            result = self._run(out)
            self.assertEqual(self._code, 3)
            self.assertEqual(result["error"], "missing_asset")


if __name__ == "__main__":
    unittest.main()
