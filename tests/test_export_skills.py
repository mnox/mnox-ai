from __future__ import annotations

import importlib.util
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "export_skills.py"


def load_exporter():
    spec = importlib.util.spec_from_file_location("_mnoxai_export_skills", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


exporter = load_exporter()


class ExportSkillsTest(unittest.TestCase):
    def test_discovers_current_skills(self) -> None:
        skills = {skill.name for skill in exporter.discover_skills()}
        self.assertIn("schema-review", skills)
        self.assertIn("curriculum", skills)
        self.assertIn("foundry-run", skills)

    def test_copy_subset_writes_manifest(self) -> None:
        with TemporaryDirectory() as d:
            out = Path(d) / "skills"
            with redirect_stdout(io.StringIO()):
                code = exporter.main(["--output-dir", str(out), "--skill", "schema-review"])
            self.assertEqual(code, 0)
            self.assertTrue((out / "schema-review" / "SKILL.md").is_file())
            manifest = json.loads((out / "skills-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema"], "mnox-ai.skills-export.v1")
            self.assertEqual([s["name"] for s in manifest["skills"]], ["schema-review"])

    def test_existing_target_requires_overwrite(self) -> None:
        with TemporaryDirectory() as d:
            out = Path(d) / "skills"
            (out / "schema-review").mkdir(parents=True)
            with self.assertRaises(SystemExit):
                exporter.main(["--output-dir", str(out), "--skill", "schema-review"])


if __name__ == "__main__":
    unittest.main()
