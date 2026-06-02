"""Tests for plugins/curriculum/skills/curriculum/scripts/compute_progress.py.

Covers the pure summarization/derivation helpers plus the end-to-end main()
flow against a hermetic temp curriculum tree.
"""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from tests._loader import load_script

cp = load_script("compute_progress")


def _row(module: str, level, *, strengths=None, revisit=None, ts="2026-01-01T00:00:00Z") -> dict:
    return {
        "timestamp": ts,
        "module": module,
        "question_id": "q1",
        "question": "?",
        "response": "ans",
        "assessment": {
            "understanding_level": level,
            "strengths": strengths or [],
            "gaps": [],
            "misconceptions": [],
            "notes": "",
        },
        "adaptation": {"revisit_before_next_module": revisit or []},
    }


class DeriveStatusTest(unittest.TestCase):
    def test_not_started_when_no_rows(self) -> None:
        self.assertEqual(cp.derive_status(0, None), "not started")

    def test_passed_at_threshold(self) -> None:
        self.assertEqual(cp.derive_status(2, cp.PASS_THRESHOLD), "passed")

    def test_in_progress_below_threshold(self) -> None:
        self.assertEqual(cp.derive_status(2, 2.0), "in progress")

    def test_in_progress_when_avg_none(self) -> None:
        self.assertEqual(cp.derive_status(3, None), "in progress")


class LoadRowsTest(unittest.TestCase):
    def test_missing_file_returns_empty(self) -> None:
        self.assertEqual(cp.load_rows(Path("/nonexistent/responses.jsonl")), [])

    def test_skips_blank_and_malformed_lines(self) -> None:
        with TemporaryDirectory() as d:
            p = Path(d) / "responses.jsonl"
            p.write_text('{"a": 1}\n\n   \nNOT JSON\n{"b": 2}\n', encoding="utf-8")
            rows = cp.load_rows(p)
        self.assertEqual(rows, [{"a": 1}, {"b": 2}])


class SummarizeModulesTest(unittest.TestCase):
    def test_orders_disk_modules_first_then_jsonl_only(self) -> None:
        rows = [
            _row("01-intro", 4),
            _row("01-intro", 2),
            _row("zz-synthesis", 5),
        ]
        out = dict(cp.summarize_modules(rows, disk_modules=["01-intro", "02-empty"]))
        # disk order preserved, then jsonl-only module appended
        self.assertEqual(
            [m for m, _ in cp.summarize_modules(rows, ["01-intro", "02-empty"])],
            ["01-intro", "02-empty", "zz-synthesis"],
        )
        self.assertEqual(out["01-intro"]["count"], 2)
        self.assertEqual(out["01-intro"]["avg_level"], 3.0)  # (4+2)/2
        self.assertEqual(out["01-intro"]["status"], "passed")
        self.assertEqual(out["02-empty"]["count"], 0)
        self.assertIsNone(out["02-empty"]["avg_level"])
        self.assertEqual(out["02-empty"]["status"], "not started")
        self.assertEqual(out["zz-synthesis"]["avg_level"], 5.0)

    def test_non_int_levels_ignored_in_average(self) -> None:
        rows = [_row("m", 4), _row("m", "bad")]
        out = dict(cp.summarize_modules(rows, ["m"]))
        self.assertEqual(out["m"]["count"], 2)
        self.assertEqual(out["m"]["avg_level"], 4.0)


class GapsAndStrengthsTest(unittest.TestCase):
    def test_open_gaps_exclude_resolved_strengths(self) -> None:
        rows = [
            _row("m", 2, revisit=["Closures"]),
            _row("m", 2, revisit=["closures", "Recursion"]),
            # high-level row whose strength resolves the "closures" gap
            _row("m", 4, strengths=["Closures"]),
        ]
        gaps = dict(cp.collect_gaps(rows))
        self.assertNotIn("closures", gaps)
        self.assertEqual(gaps["recursion"], 1)

    def test_strengths_only_when_recurring_twice(self) -> None:
        rows = [
            _row("m", 4, strengths=["Big-O"]),
            _row("m", 4, strengths=["big-o", "tail calls"]),
        ]
        strengths = dict(cp.collect_strengths(rows))
        self.assertEqual(strengths["big-o"], 2)
        self.assertNotIn("tail calls", strengths)


class RenderTest(unittest.TestCase):
    def test_empty_render_has_placeholders(self) -> None:
        text = cp.render([], [], [])
        self.assertIn("(no modules recorded yet)", text)
        self.assertIn("(no open gaps recorded)", text)
        self.assertIn("# Progress Tracker", text)

    def test_render_includes_module_row(self) -> None:
        module_rows = [
            ("01-intro", {"avg_level": 3.5, "last_activity": "ts", "status": "passed", "count": 4})
        ]
        text = cp.render(module_rows, [("a gap", 2)], [("a strength", 3)])
        self.assertIn("| 01-intro | passed | ts | 3.50 | 4 |", text)
        self.assertIn("- (2x) a gap", text)
        self.assertIn("- (3x) a strength", text)


class MainTest(unittest.TestCase):
    def _scaffold(self, base: Path) -> Path:
        cdir = base / "curriculum"
        (cdir / "modules").mkdir(parents=True)
        (cdir / "assessments").mkdir(parents=True)
        (cdir / "modules" / "01-intro.md").write_text("# intro", encoding="utf-8")
        (cdir / "modules" / "02-next.md").write_text("# next", encoding="utf-8")
        return cdir

    def _run_main(self, cdir: Path) -> dict:
        buf = io.StringIO()
        argv = ["compute_progress.py", "--curriculum-dir", str(cdir)]
        import sys

        old = sys.argv
        sys.argv = argv
        try:
            with redirect_stdout(buf):
                code = cp.main()
        finally:
            sys.argv = old
        self._code = code
        return json.loads(buf.getvalue().strip())

    def test_happy_path_writes_progress_and_summary(self) -> None:
        with TemporaryDirectory() as d:
            cdir = self._scaffold(Path(d))
            jsonl = cdir / "assessments" / "responses.jsonl"
            jsonl.write_text(
                json.dumps(_row("01-intro", 4)) + "\n" + json.dumps(_row("01-intro", 5)) + "\n",
                encoding="utf-8",
            )
            result = self._run_main(cdir)
            self.assertEqual(self._code, 0)
            self.assertTrue(result["success"])
            self.assertEqual(result["row_count"], 2)
            self.assertEqual(result["module_count"], 2)
            self.assertIn("01-intro", result["passed_modules"])
            progress = (cdir / "assessments" / "progress.md").read_text(encoding="utf-8")
            self.assertIn("01-intro", progress)
            self.assertIn("passed", progress)

    def test_unscaffolded_returns_error(self) -> None:
        with TemporaryDirectory() as d:
            cdir = Path(d) / "curriculum"  # nothing created
            result = self._run_main(cdir)
            self.assertEqual(self._code, 2)
            self.assertFalse(result["success"])
            self.assertEqual(result["error"], "curriculum_not_scaffolded")


if __name__ == "__main__":
    unittest.main()
