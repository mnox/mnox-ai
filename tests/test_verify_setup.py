"""Tests for plugins/ai-setup/skills/ai-setup/scripts/verify_setup.py."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from tests._loader import load_script

vs = load_script("verify_setup")

SKILL = """\
---
name: {name}
description: Applies {name}. Use when writing or reviewing code in this stack.
---

# {name}
"""

MANAGED_BLOCK = """\
<!-- ai-setup:start -->
role
<!-- ai-setup:end -->
"""


def write(root: Path, relative: str, content: str = "") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def write_skill(root: Path, directory: str, name: str) -> Path:
    return write(root, f"{directory}/{name}/SKILL.md", SKILL.format(name=name))


def check(kind: str, path: str = "", value: object = None) -> dict:
    return {"type": kind, "path": path, **({} if value is None else {"value": value})}


def item(item_id: str, status: str = "applied", **extra: object) -> dict:
    return {"id": item_id, "layer": "skill", "status": status, **extra}


def manifest(items: list[dict], slots: list[dict] | None = None) -> dict:
    return {"schema": vs.SCHEMA, "profile": {}, "slots": slots or [], "items": items}


class VerifyTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name).resolve()
        self.root = base / "repo"
        self.home = base / "home"
        self.root.mkdir()
        self.home.mkdir()
        self.roots = vs.Roots(self.root, self.home)

    def statuses(self, document: dict) -> dict[tuple[str, str], list[str]]:
        results = vs.verify(document, self.roots)
        keys = sorted({(r.item, r.check) for r in results})
        return {key: [r.status for r in results if (r.item, r.check) == key] for key in keys}

    def test_well_formed_setup_passes(self) -> None:
        write_skill(self.root, ".claude/skills", "react-practices")
        write(self.root, ".claude/settings.json", json.dumps({"permissions": {}}))
        write(self.home, ".claude/CLAUDE.md", MANAGED_BLOCK)
        document = manifest(
            [
                item("skill-react", checks=[check("skill", ".claude/skills/react-practices")]),
                item("settings", checks=[check("json", ".claude/settings.json")]),
                item(
                    "global",
                    status="verified",
                    checks=[
                        check("exists", "~/.claude/CLAUDE.md"),
                        check("contains", "~/.claude/CLAUDE.md", "ai-setup:start"),
                        check("max_lines", "~/.claude/CLAUDE.md", 60),
                    ],
                ),
            ],
            slots=[{"id": "framework-practice", "priority": "core", "filled_by": "skill-react"}],
        )
        results = vs.verify(document, self.roots)
        self.assertEqual({r.status for r in results}, {"pass"})
        self.assertTrue(vs.report(self.root / "m.json", results)["success"])

    def test_skill_name_must_match_its_directory(self) -> None:
        write(self.root, "skills/react-practices/SKILL.md", SKILL.format(name="react"))
        document = manifest([item("s", checks=[check("skill", "skills/react-practices")])])
        self.assertIn("fail", self.statuses(document)[("s", "skill")])

    def test_missing_and_malformed_artifacts_fail(self) -> None:
        write(self.root, "broken.json", "{ nope")
        document = manifest(
            [
                item("gone", checks=[check("exists", "nowhere.md")]),
                item("bad-json", checks=[check("json", "broken.json")]),
                item("no-skill", checks=[check("skill", "skills/absent")]),
                item("no-marker", checks=[check("contains", "broken.json", "x:start")]),
                item("odd", checks=[check("telepathy", "broken.json")]),
            ]
        )
        statuses = self.statuses(document)
        self.assertEqual(statuses[("gone", "exists")], ["fail"])
        self.assertEqual(statuses[("bad-json", "json")], ["fail"])
        self.assertEqual(statuses[("no-skill", "skill")], ["fail"])
        self.assertEqual(statuses[("no-marker", "contains")], ["fail"])
        self.assertEqual(statuses[("odd", "telepathy")], ["fail"])

    def test_line_budget_overrun_warns_without_failing(self) -> None:
        write(self.root, "AGENTS.md", "line\n" * 12)
        document = manifest([item("repo", checks=[check("max_lines", "AGENTS.md", 10)])])
        results = vs.verify(document, self.roots)
        self.assertEqual([r.status for r in results if r.item == "repo"], ["warn"])
        self.assertTrue(vs.report(self.root / "m.json", results)["success"])

    def test_commands_and_human_steps_are_pending_not_run(self) -> None:
        sentinel = self.root / "ran.txt"
        document = manifest(
            [
                item("cmd", checks=[check("command", value=f"touch {sentinel}")]),
                item("oauth", status="needs-human", human_step="authorize the Figma server"),
            ]
        )
        statuses = self.statuses(document)
        self.assertEqual(statuses[("cmd", "command")], ["pending"])
        self.assertEqual(statuses[("oauth", "status")], ["pending"])
        self.assertFalse(sentinel.exists())

    def test_item_status_rules(self) -> None:
        document = manifest(
            [
                item("failed", status="failed", note="plugin install exited 1"),
                item("unproven"),
                item("planned", status="planned", checks=[check("exists", "nope")]),
                item("skipped", status="skipped"),
                item("weird", status="done"),
            ]
        )
        statuses = self.statuses(document)
        self.assertEqual(statuses[("failed", "status")], ["fail"])
        self.assertEqual(statuses[("unproven", "checks")], ["warn"])
        self.assertEqual(statuses[("weird", "status")], ["fail"])
        self.assertNotIn(("planned", "exists"), statuses)
        self.assertFalse(any(key[0] == "skipped" for key in statuses))

    def test_core_slots_must_be_filled_or_waived(self) -> None:
        write(self.root, "a.md", "x")
        document = manifest(
            [
                item("ok", checks=[check("exists", "a.md")]),
                item("later", status="needs-human", human_step="log in"),
                item("planned-only", status="planned"),
            ],
            slots=[
                {"id": "filled", "priority": "core", "filled_by": ["planned-only", "ok"]},
                {"id": "waiting", "priority": "core", "filled_by": "later"},
                {"id": "waived", "priority": "core", "filled_by": None, "waived": "no design tool"},
                {"id": "empty", "priority": "core", "filled_by": "planned-only"},
                {"id": "dangling", "priority": "core", "filled_by": "no-such-item"},
                {"id": "optional", "priority": "useful", "filled_by": None},
            ],
        )
        statuses = self.statuses(document)
        self.assertEqual(statuses[("slot:filled", "slot")], ["pass"])
        self.assertEqual(statuses[("slot:waiting", "slot")], ["pending"])
        self.assertEqual(statuses[("slot:waived", "slot")], ["warn"])
        self.assertEqual(statuses[("slot:empty", "slot")], ["fail"])
        self.assertEqual(statuses[("slot:dangling", "slot")], ["fail"])
        self.assertNotIn(("slot:optional", "slot"), statuses)

    def test_duplicate_skill_names_and_ids_fail(self) -> None:
        write_skill(self.root, ".claude/skills", "ts-practices")
        write_skill(self.home, ".claude/skills", "ts-practices")
        document = manifest(
            [
                item("dup", checks=[check("skill", ".claude/skills/ts-practices")]),
                item("dup", checks=[check("skill", "~/.claude/skills/ts-practices")]),
            ]
        )
        statuses = self.statuses(document)
        self.assertEqual(statuses[("manifest", "unique_skills")], ["fail"])
        self.assertEqual(statuses[("manifest", "unique_ids")], ["fail"])

    def test_wrong_schema_fails(self) -> None:
        document = {**manifest([]), "schema": "something-else"}
        self.assertEqual(self.statuses(document)[("manifest", "schema")], ["fail"])


class MainTest(unittest.TestCase):
    def run_main(self, args: list[str]) -> tuple[int, dict]:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = vs.main(args)
        return code, json.loads(buffer.getvalue())

    def test_exit_codes_and_root_from_profile(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            repo = base / "repo"
            write(repo, "AGENTS.md", "hi\n")
            good = manifest([item("repo", checks=[check("exists", "AGENTS.md")])])
            good["profile"] = {"repo": repo.as_posix()}
            bad = manifest([item("repo", checks=[check("exists", "MISSING.md")])])
            bad["profile"] = {"repo": repo.as_posix()}
            good_path = write(base, "state/good.json", json.dumps(good))
            bad_path = write(base, "state/bad.json", json.dumps(bad))
            junk_path = write(base, "state/junk.json", "[1, 2")

            code, outcome = self.run_main(["--manifest", str(good_path), "--home", str(base)])
            self.assertEqual((code, outcome["success"]), (0, True))
            self.assertEqual(outcome["summary"]["pass"], 2)

            code, outcome = self.run_main(["--manifest", str(bad_path), "--home", str(base)])
            self.assertEqual((code, outcome["success"]), (1, False))
            self.assertEqual(outcome["summary"]["fail"], 1)

            code, outcome = self.run_main(["--manifest", str(junk_path)])
            self.assertEqual((code, outcome["success"]), (2, False))

            code, outcome = self.run_main(["--manifest", str(base / "state" / "absent.json")])
            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
