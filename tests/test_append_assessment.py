"""Tests for plugins/curriculum/skills/curriculum/scripts/append_assessment.py.

Exercises the pure validate() schema checker plus the stdin->JSONL append flow
in main() against a hermetic temp curriculum tree.
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

aa = load_script("append_assessment")


def _valid_row() -> dict:
    return {
        "timestamp": "2026-01-01T00:00:00Z",
        "module": "01-intro",
        "question_id": "q1",
        "question": "What is a closure?",
        "response": "A function plus its captured environment.",
        "assessment": {
            "understanding_level": 4,
            "rubric": {
                "conceptual_accuracy": 4,
                "vocabulary_fluency": 3,
                "ability_to_apply": 4,
                "confidence_calibration": "appropriately_uncertain",
            },
            "strengths": ["clear definition"],
            "gaps": [],
            "misconceptions": [],
            "notes": "solid",
        },
        "adaptation": {
            "revisit_before_next_module": [],
            "accelerate": [],
            "emphasize_in_next_module": [],
            "followup_question": None,
        },
    }


class ValidateTest(unittest.TestCase):
    def test_valid_row_has_no_errors(self) -> None:
        self.assertEqual(aa.validate(_valid_row()), [])

    def test_non_dict_row(self) -> None:
        self.assertEqual(aa.validate(["not", "a", "dict"]), ["row_is_not_object"])

    def test_missing_top_level_keys(self) -> None:
        row = _valid_row()
        del row["module"]
        del row["question"]
        errors = aa.validate(row)
        self.assertTrue(any("missing_top_level_keys" in e for e in errors))

    def test_understanding_level_out_of_range(self) -> None:
        row = _valid_row()
        row["assessment"]["understanding_level"] = 9
        self.assertIn("understanding_level_not_int_0_to_5", aa.validate(row))

    def test_bad_confidence_calibration(self) -> None:
        row = _valid_row()
        row["assessment"]["rubric"]["confidence_calibration"] = "very_sure"
        errors = aa.validate(row)
        self.assertTrue(any("confidence_calibration_not_in" in e for e in errors))

    def test_strengths_not_list_of_strings(self) -> None:
        row = _valid_row()
        row["assessment"]["strengths"] = [1, 2, 3]
        self.assertIn("strengths_not_list_of_strings", aa.validate(row))

    def test_rubric_scalar_not_int(self) -> None:
        row = _valid_row()
        row["assessment"]["rubric"]["ability_to_apply"] = "high"
        self.assertIn("rubric.ability_to_apply_not_int_0_to_5", aa.validate(row))


class MainTest(unittest.TestCase):
    def _run(self, cdir: Path, stdin_text: str, *, auto_ts: bool = False) -> dict:
        buf = io.StringIO()
        argv = ["append_assessment.py", "--curriculum-dir", str(cdir)]
        if auto_ts:
            argv.append("--auto-timestamp")
        old_argv, old_stdin = sys.argv, sys.stdin
        sys.argv = argv
        sys.stdin = io.StringIO(stdin_text)
        try:
            with redirect_stdout(buf):
                self._code = aa.main()
        finally:
            sys.argv, sys.stdin = old_argv, old_stdin
        return json.loads(buf.getvalue().strip())

    def _scaffold(self, base: Path) -> Path:
        cdir = base / "curriculum"
        (cdir / "assessments").mkdir(parents=True)
        return cdir

    def test_happy_path_appends_line(self) -> None:
        with TemporaryDirectory() as d:
            cdir = self._scaffold(Path(d))
            result = self._run(cdir, json.dumps(_valid_row()))
            self.assertEqual(self._code, 0)
            self.assertTrue(result["success"])
            self.assertEqual(result["understanding_level"], 4)
            jsonl = cdir / "assessments" / "responses.jsonl"
            lines = jsonl.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0])["module"], "01-intro")

    def test_auto_timestamp_fills_missing(self) -> None:
        with TemporaryDirectory() as d:
            cdir = self._scaffold(Path(d))
            row = _valid_row()
            del row["timestamp"]
            result = self._run(cdir, json.dumps(row), auto_ts=True)
            self.assertEqual(self._code, 0)
            self.assertTrue(result["success"])
            line = (cdir / "assessments" / "responses.jsonl").read_text(encoding="utf-8").strip()
            self.assertIn("timestamp", json.loads(line))

    def test_missing_assessments_dir(self) -> None:
        with TemporaryDirectory() as d:
            cdir = Path(d) / "curriculum"  # not scaffolded
            result = self._run(cdir, json.dumps(_valid_row()))
            self.assertEqual(self._code, 2)
            self.assertEqual(result["error"], "assessments_dir_missing")

    def test_empty_stdin(self) -> None:
        with TemporaryDirectory() as d:
            cdir = self._scaffold(Path(d))
            result = self._run(cdir, "   ")
            self.assertEqual(self._code, 2)
            self.assertEqual(result["error"], "empty_stdin")

    def test_invalid_json(self) -> None:
        with TemporaryDirectory() as d:
            cdir = self._scaffold(Path(d))
            result = self._run(cdir, "{not json")
            self.assertEqual(self._code, 2)
            self.assertEqual(result["error"], "invalid_json")

    def test_validation_failure_blocks_append(self) -> None:
        with TemporaryDirectory() as d:
            cdir = self._scaffold(Path(d))
            row = _valid_row()
            row["assessment"]["understanding_level"] = 99
            result = self._run(cdir, json.dumps(row))
            self.assertEqual(self._code, 3)
            self.assertEqual(result["error"], "validation_failed")
            # nothing should have been written
            jsonl = cdir / "assessments" / "responses.jsonl"
            self.assertFalse(jsonl.exists() and jsonl.read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    unittest.main()
