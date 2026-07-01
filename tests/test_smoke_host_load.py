from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "smoke_host_load", REPO_ROOT / "scripts" / "smoke_host_load.py"
)
smoke = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(smoke)


class SmokeHostLoadTest(unittest.TestCase):
    def test_automated_checks_pass_for_every_host(self) -> None:
        # A plain skill plus an engine-backed one, to exercise engine bundling.
        skills = ["schema-review", "ai-setup"]
        with tempfile.TemporaryDirectory() as tmp:
            reports = smoke.run_checks(list(smoke.HOST_SKILL_SUBPATH), skills, Path(tmp))
        self.assertEqual(len(reports), 3)
        for rep in reports:
            failed = [msg for ok, msg in rep.checks if not ok]
            self.assertTrue(rep.passed, f"{rep.host} failed: {failed}")

    def test_mcp_snippets_are_absolute_and_claude_var_free(self) -> None:
        snippet = smoke.codex_mcp_snippet(smoke.SERVER_SH)
        self.assertIn(str(smoke.SERVER_SH), snippet)
        self.assertNotIn("${CLAUDE_PLUGIN_ROOT}", snippet)
        self.assertTrue(smoke.SERVER_SH.is_absolute())


if __name__ == "__main__":
    unittest.main()
