"""Tests for plugins/system-design/skills/system-design/scripts/render_map.py."""

from __future__ import annotations

import copy
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from tests._loader import load_script

rm = load_script("render_map")

EXAMPLE = rm.SKILL_DIR / "templates" / "design-map.example.json"


def example() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def small() -> dict:
    return {
        "title": "Tiny",
        "columns": 3,
        "rows": ["People", "Services", "Stores"],
        "categories": [{"key": "S", "name": "Scope", "blurb": "b"}],
        "questions": {"S1": {"q": "In scope?", "decides": "Whether B exists."}},
        "nodes": [
            {"id": "user", "row": 1, "label": "User", "kind": "open", "what": "w", "qs": ["S1"]},
            {"id": "a", "row": 2, "col": 1, "label": "A", "kind": "plain", "what": "w"},
            {"id": "b", "row": 2, "col": 2, "label": "B", "kind": "plain", "what": "w"},
            {"id": "c", "row": 2, "col": 3, "label": "C", "kind": "plain", "what": "w"},
            {"id": "db", "row": 3, "col": 1, "label": "DB", "kind": "plain", "what": "w"},
        ],
        "edges": [
            {"from": "user", "to": "a", "route": "elbow"},
            {"from": "a", "to": "b", "route": "h"},
            {"from": "b", "to": "c", "route": "h"},
            {"from": "a", "to": "db", "route": "down"},
        ],
    }


def run_main(*argv: str) -> tuple[int, dict]:
    buf = io.StringIO()
    old = sys.argv
    sys.argv = ["render_map.py", *argv]
    try:
        with redirect_stdout(buf):
            code = rm.main()
    finally:
        sys.argv = old
    return code, json.loads(buf.getvalue().strip())


class ValidateTest(unittest.TestCase):
    def test_shipped_example_has_no_errors(self) -> None:
        errors, _ = rm.validate(example())
        self.assertEqual(errors, [])

    def test_small_map_is_clean(self) -> None:
        self.assertEqual(rm.validate(small()), ([], []))

    def test_missing_top_level_keys(self) -> None:
        errors, _ = rm.validate({"title": "x"})
        self.assertIn("missing top-level key: nodes", errors)

    def test_duplicate_node_id(self) -> None:
        data = small()
        data["nodes"].append(copy.deepcopy(data["nodes"][1]) | {"col": 3, "row": 3})
        errors, _ = rm.validate(data)
        self.assertIn("duplicate node id: a", errors)

    def test_two_boxes_in_one_cell(self) -> None:
        data = small()
        data["nodes"][2]["col"] = 1
        errors, _ = rm.validate(data)
        self.assertIn("row 2: more than one box in column 1", errors)

    def test_unknown_question_reference(self) -> None:
        data = small()
        data["nodes"][0]["qs"] = ["S9"]
        errors, _ = rm.validate(data)
        self.assertIn("user: unknown question S9", errors)

    def test_question_without_category(self) -> None:
        data = small()
        data["questions"]["Z1"] = {"q": "q", "decides": "d"}
        errors, _ = rm.validate(data)
        self.assertIn("question Z1: no category with key Z", errors)

    def test_fork_needs_two_options(self) -> None:
        data = small()
        data["nodes"][1] |= {
            "kind": "fork",
            "fork": {"q": "?", "options": [{"name": "x", "when": "y"}]},
        }
        errors, _ = rm.validate(data)
        self.assertIn("a: a fork needs a question and at least two options", errors)

    def test_horizontal_edge_through_a_box_is_rejected(self) -> None:
        data = small()
        data["edges"].append({"from": "a", "to": "c", "route": "h"})
        errors, _ = rm.validate(data)
        self.assertIn("edge a -> c: h would run through another box", errors)

    def test_elbow_cannot_skip_a_row(self) -> None:
        data = small()
        data["edges"].append({"from": "user", "to": "db", "route": "elbow"})
        errors, _ = rm.validate(data)
        self.assertTrue(any(e.startswith("edge user -> db: elbow only reaches") for e in errors))

    def test_down_through_a_box_is_rejected(self) -> None:
        data = small()
        data["rows"].append("Outside")
        data["nodes"].append(
            {"id": "ext", "row": 4, "col": 1, "label": "Ext", "kind": "plain", "what": "w"}
        )
        data["edges"].append({"from": "a", "to": "ext", "route": "down"})
        errors, _ = rm.validate(data)
        self.assertIn("edge a -> ext: down would run through another box", errors)

    def test_riser_needs_via(self) -> None:
        data = small()
        data["edges"].append({"from": "b", "to": "db", "route": "riser"})
        errors, _ = rm.validate(data)
        self.assertTrue(any(e.startswith("edge b -> db: riser needs a via") for e in errors))

    def test_warnings_for_orphans(self) -> None:
        data = small()
        data["questions"]["S2"] = {"q": "q", "decides": "d"}
        data["nodes"].append(
            {"id": "lonely", "row": 3, "col": 3, "label": "L", "kind": "open", "what": "w"}
        )
        errors, warnings = rm.validate(data)
        self.assertEqual(errors, [])
        self.assertIn("question S2 is not attached to any box", warnings)
        self.assertIn("box lonely has no edges", warnings)
        self.assertIn("box lonely is marked open but carries no questions", warnings)


class RenderTest(unittest.TestCase):
    def test_render_fills_both_placeholders(self) -> None:
        page = rm.render(small(), rm.TEMPLATE.read_text(encoding="utf-8"))
        self.assertNotIn("__DATA__", page)
        self.assertNotIn("__TITLE__", page)
        self.assertIn("<title>Tiny</title>", page)

    def test_render_cannot_close_the_script_tag(self) -> None:
        data = small()
        data["nodes"][0]["what"] = "</script><script>alert(1)</script>"
        page = rm.render(data, "<script>const DATA = __DATA__;</script>")
        self.assertEqual(page.count("</script>"), 1)

    def test_title_is_escaped(self) -> None:
        data = small() | {"title": "A <b> & C"}
        page = rm.render(data, "<title>__TITLE__</title>__DATA__")
        self.assertIn("<title>A &lt;b&gt; &amp; C</title>", page)


class MainTest(unittest.TestCase):
    def test_writes_page_and_reports(self) -> None:
        with TemporaryDirectory() as d:
            out = Path(d) / "nested" / "map.html"
            code, payload = run_main("--data", str(EXAMPLE), "--output", str(out))
            self.assertEqual(code, 0)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["nodes"], len(example()["nodes"]))
            self.assertIn("design map", out.read_text(encoding="utf-8"))

    def test_check_writes_nothing(self) -> None:
        code, payload = run_main("--data", str(EXAMPLE), "--check")
        self.assertEqual(code, 0)
        self.assertTrue(payload["checked"])

    def test_invalid_data_exits_non_zero(self) -> None:
        with TemporaryDirectory() as d:
            bad = Path(d) / "bad.json"
            bad.write_text(
                json.dumps(
                    small() | {"nodes": []} | {"edges": [{"from": "x", "to": "y", "route": "h"}]}
                ),
                encoding="utf-8",
            )
            code, payload = run_main("--data", str(bad), "--output", str(Path(d) / "o.html"))
            self.assertEqual(code, 1)
            self.assertFalse(payload["ok"])
            self.assertFalse((Path(d) / "o.html").exists())

    def test_unreadable_data_file(self) -> None:
        code, payload = run_main("--data", "does-not-exist.json", "--check")
        self.assertEqual(code, 1)
        self.assertFalse(payload["ok"])

    def test_output_required_without_check(self) -> None:
        code, payload = run_main("--data", str(EXAMPLE))
        self.assertEqual(code, 1)
        self.assertIn("--output is required unless --check is given", payload["errors"])


if __name__ == "__main__":
    unittest.main()
