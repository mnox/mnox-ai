#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Validate a design-map data file and render it to a single hoverable HTML page.

The data file is JSON in the shape of ``templates/design-map.example.json``.
Validation enforces the layout rules that keep the diagram readable: no two
boxes in one grid cell, every edge routed through a gutter, every question
reference resolvable. Prints one JSON object on stdout and exits non-zero when
the data has errors.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "templates" / "design-map.html"

REQUIRED = ("title", "rows", "categories", "questions", "nodes")
KINDS = {"fork", "constraint", "open", "plain"}
TAGS = {"plg"}
ROUTES = {"elbow", "down", "drop", "h", "margin", "riser"}
ADJACENT_ROW_ROUTES = {"elbow", "drop"}
DEFAULT_COLUMNS = 6


def cells(node: dict) -> set[int]:
    return set(range(node["col"], node["col"] + node.get("span", 1))) if node.get("col") else set()


def category_of(question_id: str) -> str:
    return re.sub(r"\d+$", "", question_id)


def node_errors(data: dict) -> Iterator[str]:
    nodes = data["nodes"]
    columns = data.get("columns", DEFAULT_COLUMNS)
    row_count = len(data["rows"])
    questions = data["questions"]
    counts = Counter(node.get("id") for node in nodes)
    yield from (f"duplicate node id: {node_id}" for node_id, n in counts.items() if n > 1)
    for node in nodes:
        name = node.get("id", "<missing id>")
        if not node.get("id") or not node.get("label") or not node.get("what"):
            yield f"{name}: id, label and what are required"
        if node.get("kind") not in KINDS:
            yield f"{name}: kind must be one of {sorted(KINDS)}"
        if not 1 <= node.get("row", 0) <= row_count:
            yield f"{name}: row must be between 1 and {row_count}"
        if node.get("col") and max(cells(node)) > columns:
            yield f"{name}: col and span run past column {columns}"
        yield from (f"{name}: unknown tag {tag}" for tag in node.get("tags", []) if tag not in TAGS)
        yield from (
            f"{name}: unknown question {q}" for q in node.get("qs", []) if q not in questions
        )
        if node.get("kind") == "fork" and len(node.get("fork", {}).get("options", [])) < 2:
            yield f"{name}: a fork needs a question and at least two options"
    for row in range(1, row_count + 1):
        in_row = [node for node in nodes if node.get("row") == row]
        placed = [node for node in in_row if node.get("col")]
        if placed and len(placed) != len(in_row):
            yield f"row {row}: either every box has a col or none does"
        taken = Counter(cell for node in placed for cell in cells(node))
        yield from (
            f"row {row}: more than one box in column {cell}" for cell, n in taken.items() if n > 1
        )


def blocked_between(nodes: list[dict], a: dict, b: dict) -> bool:
    left, right = sorted((a, b), key=lambda node: node["col"])
    between = set(range(max(cells(left)) + 1, min(cells(right))))
    return any(
        node["row"] == a["row"] and node["id"] not in (a["id"], b["id"]) and cells(node) & between
        for node in nodes
        if node.get("col")
    )


def edge_errors(data: dict) -> Iterator[str]:
    nodes = data["nodes"]
    by_id = {node.get("id"): node for node in nodes}
    for edge in data.get("edges", []):
        name = f"edge {edge.get('from')} -> {edge.get('to')}"
        a, b = by_id.get(edge.get("from")), by_id.get(edge.get("to"))
        route = edge.get("route")
        if a is None or b is None:
            yield f"{name}: both ends must be node ids"
            continue
        if route not in ROUTES:
            yield f"{name}: route must be one of {sorted(ROUTES)}"
            continue
        if route in ADJACENT_ROW_ROUTES and b["row"] != a["row"] + 1:
            yield f"{name}: {route} only reaches the row directly below; use riser or margin"
        if route == "down" and not (b["row"] > a["row"] and cells(a) and cells(a) <= cells(b)):
            yield f"{name}: down needs the source to sit above the target, inside its columns"
        elif route == "down" and any(
            a["row"] < node.get("row", 0) < b["row"] and cells(node) & cells(a) for node in nodes
        ):
            yield f"{name}: down would run through another box"
        if route == "drop" and not (cells(b) and cells(b) <= cells(a)):
            yield f"{name}: drop needs the target to sit under the source's columns"
        if route == "h" and (a["row"] != b["row"] or not a.get("col") or not b.get("col")):
            yield f"{name}: h connects two placed boxes in the same row"
        elif route == "h" and blocked_between(nodes, a, b):
            yield f"{name}: h would run through another box"
        if route == "margin" and (a.get("col") != 1 or b["row"] <= a["row"]):
            yield f"{name}: margin starts in column 1 and ends in a lower row"
        if route == "riser" and (edge.get("via") not in by_id or b["row"] <= a["row"]):
            yield f"{name}: riser needs a via node id and a target in a lower row"


def reference_errors(data: dict) -> Iterator[str]:
    questions = data["questions"]
    keys = {category.get("key") for category in data["categories"]}
    yield from (
        f"question {q}: no category with key {category_of(q)}"
        for q in questions
        if category_of(q) not in keys
    )
    yield from (
        f"question {q}: q and decides are required"
        for q, body in questions.items()
        if not body.get("q") or not body.get("decides")
    )
    yield from (f"first: unknown question {q}" for q in data.get("first", []) if q not in questions)
    columns = data.get("columns", DEFAULT_COLUMNS)
    yield from (
        f"group {group.get('label')}: col and row range are out of bounds"
        for group in data.get("groups", [])
        if not (
            1 <= group.get("col", 0) <= columns
            and 1 <= group.get("fromRow", 0) <= group.get("toRow", 0) <= len(data["rows"])
        )
    )


def validate(data: dict) -> tuple[list[str], list[str]]:
    missing = [key for key in REQUIRED if key not in data]
    if missing:
        return [f"missing top-level key: {key}" for key in missing], []
    errors = [*node_errors(data), *edge_errors(data), *reference_errors(data)]
    used = {q for node in data["nodes"] for q in node.get("qs", [])}
    linked = {end for edge in data.get("edges", []) for end in (edge.get("from"), edge.get("to"))}
    warnings = [
        *(f"question {q} is not attached to any box" for q in data["questions"] if q not in used),
        *(
            f"box {node['id']} has no edges"
            for node in data["nodes"]
            if node.get("id") not in linked
        ),
        *(
            f"box {node['id']} is marked open but carries no questions"
            for node in data["nodes"]
            if node.get("kind") == "open" and not node.get("qs")
        ),
    ]
    return errors, warnings


def render(data: dict, template: str) -> str:
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return template.replace("__TITLE__", html.escape(data["title"])).replace("__DATA__", payload)


def emit(payload: dict) -> None:
    print(json.dumps(payload))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="Path to the design-map JSON file.")
    parser.add_argument("--output", help="Path of the HTML file to write.")
    parser.add_argument("--check", action="store_true", help="Validate only; write nothing.")
    args = parser.parse_args()

    try:
        data = json.loads(Path(args.data).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        emit({"ok": False, "errors": [f"could not read data file: {exc}"]})
        return 1

    errors, warnings = validate(data)
    if errors:
        emit({"ok": False, "errors": errors, "warnings": warnings})
        return 1
    if args.check:
        emit({"ok": True, "checked": True, "warnings": warnings})
        return 0
    if not args.output:
        emit({"ok": False, "errors": ["--output is required unless --check is given"]})
        return 1

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(data, TEMPLATE.read_text(encoding="utf-8")), encoding="utf-8")
    emit(
        {
            "ok": True,
            "output": str(output.resolve()),
            "nodes": len(data["nodes"]),
            "edges": len(data.get("edges", [])),
            "questions": len(data["questions"]),
            "warnings": warnings,
        }
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
