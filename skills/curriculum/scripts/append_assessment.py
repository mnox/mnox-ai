#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Append a validated assessment row to a curriculum's JSONL log.

Reads a single JSON object from stdin and appends it as one line to
``<curriculum_dir>/assessments/responses.jsonl``. Validates required fields
and types per the schema documented in the curriculum's ``curriculum-meta.md``.

Emits a structured JSON result on stdout. Non-zero exit codes indicate
validation or IO failures; the agent should fix the JSON and retry rather
than bypass validation.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_TOP_LEVEL_KEYS = {
    "timestamp",
    "module",
    "question_id",
    "question",
    "response",
    "assessment",
    "adaptation",
}

REQUIRED_ASSESSMENT_KEYS = {
    "understanding_level",
    "rubric",
    "strengths",
    "gaps",
    "misconceptions",
    "notes",
}

REQUIRED_RUBRIC_KEYS = {
    "conceptual_accuracy",
    "vocabulary_fluency",
    "ability_to_apply",
    "confidence_calibration",
}

REQUIRED_ADAPTATION_KEYS = {
    "revisit_before_next_module",
    "accelerate",
    "emphasize_in_next_module",
    "followup_question",
}

VALID_CONFIDENCE_VALUES = {
    "appropriately_uncertain",
    "overconfident",
    "underconfident",
}


def emit(payload: dict) -> None:
    print(json.dumps(payload))


def validate(row: Any) -> list[str]:
    errors: list[str] = []

    if not isinstance(row, dict):
        return ["row_is_not_object"]

    missing = REQUIRED_TOP_LEVEL_KEYS - set(row.keys())
    if missing:
        errors.append(f"missing_top_level_keys: {sorted(missing)}")

    if "timestamp" in row and not isinstance(row["timestamp"], str):
        errors.append("timestamp_not_string")
    if "module" in row and not isinstance(row["module"], str):
        errors.append("module_not_string")
    if "question_id" in row and not isinstance(row["question_id"], str):
        errors.append("question_id_not_string")
    if "question" in row and not isinstance(row["question"], str):
        errors.append("question_not_string")
    if "response" in row and not isinstance(row["response"], str):
        errors.append("response_not_string")

    assessment = row.get("assessment")
    if not isinstance(assessment, dict):
        errors.append("assessment_not_object")
    else:
        a_missing = REQUIRED_ASSESSMENT_KEYS - set(assessment.keys())
        if a_missing:
            errors.append(f"missing_assessment_keys: {sorted(a_missing)}")

        level = assessment.get("understanding_level")
        if not isinstance(level, int) or not (0 <= level <= 5):
            errors.append("understanding_level_not_int_0_to_5")

        for list_key in ("strengths", "gaps", "misconceptions"):
            val = assessment.get(list_key)
            if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
                errors.append(f"{list_key}_not_list_of_strings")

        if "notes" in assessment and not isinstance(assessment["notes"], str):
            errors.append("notes_not_string")

        rubric = assessment.get("rubric")
        if not isinstance(rubric, dict):
            errors.append("rubric_not_object")
        else:
            r_missing = REQUIRED_RUBRIC_KEYS - set(rubric.keys())
            if r_missing:
                errors.append(f"missing_rubric_keys: {sorted(r_missing)}")
            for scalar_key in ("conceptual_accuracy", "vocabulary_fluency", "ability_to_apply"):
                v = rubric.get(scalar_key)
                if not isinstance(v, int) or not (0 <= v <= 5):
                    errors.append(f"rubric.{scalar_key}_not_int_0_to_5")
            conf = rubric.get("confidence_calibration")
            if conf not in VALID_CONFIDENCE_VALUES:
                errors.append(
                    f"rubric.confidence_calibration_not_in {sorted(VALID_CONFIDENCE_VALUES)}"
                )

    adaptation = row.get("adaptation")
    if not isinstance(adaptation, dict):
        errors.append("adaptation_not_object")
    else:
        ad_missing = REQUIRED_ADAPTATION_KEYS - set(adaptation.keys())
        if ad_missing:
            errors.append(f"missing_adaptation_keys: {sorted(ad_missing)}")
        for list_key in ("revisit_before_next_module", "accelerate", "emphasize_in_next_module"):
            val = adaptation.get(list_key)
            if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
                errors.append(f"adaptation.{list_key}_not_list_of_strings")
        followup = adaptation.get("followup_question")
        if followup is not None and not isinstance(followup, str):
            errors.append("adaptation.followup_question_not_string_or_null")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--curriculum-dir",
        required=True,
        help="Absolute path to the curriculum directory.",
    )
    parser.add_argument(
        "--auto-timestamp",
        action="store_true",
        help="Set timestamp to the current UTC time if missing.",
    )
    args = parser.parse_args()

    curriculum_dir = Path(args.curriculum_dir).expanduser().resolve()
    jsonl_path = curriculum_dir / "assessments" / "responses.jsonl"

    if not jsonl_path.parent.is_dir():
        emit(
            {
                "success": False,
                "error": "assessments_dir_missing",
                "path": str(jsonl_path.parent),
                "hint": "Scaffold the curriculum first via scaffold.py.",
            }
        )
        return 2

    raw = sys.stdin.read().strip()
    if not raw:
        emit({"success": False, "error": "empty_stdin"})
        return 2

    try:
        row = json.loads(raw)
    except json.JSONDecodeError as exc:
        emit({"success": False, "error": "invalid_json", "detail": str(exc)})
        return 2

    if args.auto_timestamp and isinstance(row, dict) and not row.get("timestamp"):
        row["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    errors = validate(row)
    if errors:
        emit({"success": False, "error": "validation_failed", "details": errors})
        return 3

    line = json.dumps(row, ensure_ascii=False)
    if "\n" in line:
        emit({"success": False, "error": "row_contains_newline_after_serialize"})
        return 3

    with jsonl_path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

    emit(
        {
            "success": True,
            "appended_to": str(jsonl_path),
            "module": row.get("module"),
            "question_id": row.get("question_id"),
            "understanding_level": row["assessment"]["understanding_level"],
        }
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
