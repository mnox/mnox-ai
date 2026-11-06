"""Tests for plugins/ai-setup/skills/ai-setup/scripts/inventory_config.py."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from tests._loader import load_script

inv = load_script("inventory_config")

SECRET = "sk-live-do-not-leak-0123456789"

GLOBAL_INSTRUCTIONS = """\
# Me

- prefer small diffs

<!-- config-chunks:start -->
@~/.claude/chunks/bundle.md
<!-- config-chunks:end -->
"""

SKILL = """\
---
name: {name}
description: Reviews {name} things. Use when asked to review {name}.
---

# {name}
"""

SCOPED_RULE = """\
---
paths:
  - "src/**/*.tsx"
---

Use function components.
"""


def write(root: Path, relative: str, content: str = "") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def build_home(home: Path, repo: Path) -> None:
    write(home, ".claude/CLAUDE.md", GLOBAL_INSTRUCTIONS)
    write(home, ".claude/skills/review-kit/SKILL.md", SKILL.format(name="review-kit"))
    write(home, ".claude/agents/reviewer.md", "---\nname: reviewer\n---\n")
    settings = {
        "env": {"API_TOKEN": SECRET},
        "permissions": {"allow": ["Bash(npm run test:*)"], "deny": ["Read(./.env)", "Bash(rm:*)"]},
        "hooks": {"PostToolUse": []},
        "enabledPlugins": {"typescript-lsp@official": True, "old@official": False},
        "extraKnownMarketplaces": {"team-tools": {"source": {"repo": "acme/tools"}}},
    }
    write(home, ".claude/settings.json", json.dumps(settings))
    write(home, ".claude/plugins/known_marketplaces.json", json.dumps({"official": {}}))
    user_mcp = {
        "mcpServers": {"sentry": {"url": "https://x", "headers": {"Authorization": SECRET}}},
        "projects": {str(repo): {"mcpServers": {"local-db": {"env": {"PASSWORD": SECRET}}}}},
    }
    write(home, ".claude.json", json.dumps(user_mcp))
    codex = f'model = "x"\n\n[mcp_servers.linear]\ncommand = "run"\nenv = {{ KEY = "{SECRET}" }}\n'
    write(home, ".codex/config.toml", codex)


def build_repo(repo: Path) -> None:
    write(repo, "AGENTS.md", "# Repo\n\nRun `pnpm test`.\n")
    write(repo, "CLAUDE.md", "@AGENTS.md\n")
    write(repo, ".claude/rules/components.md", SCOPED_RULE)
    write(repo, ".claude/rules/always.md", "Never edit generated files.\nAsk before migrations.\n")
    write(repo, ".claude/skills/review-kit/SKILL.md", SKILL.format(name="review-kit"))
    write(repo, ".mcp.json", json.dumps({"mcpServers": {"figma": {"env": {"TOKEN": SECRET}}}}))
    write(repo, "apps/web/AGENTS.md", "Web app notes.\n")
    write(repo, "node_modules/pkg/AGENTS.md", "vendored\n")


class InventoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name).resolve()
        self.home = base / "home"
        self.repo = base / "repo"
        self.home.mkdir()
        self.repo.mkdir()
        build_home(self.home, self.repo)
        build_repo(self.repo)
        self.report = inv.inventory(self.home, self.repo)

    def test_values_are_never_emitted(self) -> None:
        rendered = json.dumps(self.report)
        self.assertNotIn(SECRET, rendered)
        self.assertNotIn("acme/tools", rendered)

    def test_instruction_files_report_blocks_imports_and_nesting(self) -> None:
        files = {row["path"]: row for row in self.report["instruction_files"]}
        self.assertEqual(files["~/.claude/CLAUDE.md"]["managed_blocks"], ["config-chunks"])
        self.assertEqual(files["~/.claude/CLAUDE.md"]["imports"], ["~/.claude/chunks/bundle.md"])
        self.assertEqual(files["CLAUDE.md"]["imports"], ["AGENTS.md"])
        self.assertFalse(files["AGENTS.md"]["nested"])
        self.assertTrue(files["apps/web/AGENTS.md"]["nested"])
        self.assertNotIn("node_modules/pkg/AGENTS.md", files)

    def test_rules_distinguish_path_scoped_from_always_loaded(self) -> None:
        rules = {row["path"]: row["path_scoped"] for row in self.report["rules"]}
        self.assertEqual(
            rules, {".claude/rules/always.md": False, ".claude/rules/components.md": True}
        )

    def test_always_loaded_lines_exclude_nested_and_scoped_files(self) -> None:
        self.assertEqual(
            self.report["always_loaded_lines"],
            {"global": len(GLOBAL_INSTRUCTIONS.splitlines()), "repo": 3 + 1 + 2},
        )

    def test_settings_report_names_and_counts(self) -> None:
        settings = {row["path"]: row for row in self.report["settings"]}
        claude = settings["~/.claude/settings.json"]
        self.assertEqual(claude["permission_rules"], {"allow": 1, "ask": 0, "deny": 2})
        self.assertEqual(claude["hook_events"], ["PostToolUse"])
        self.assertEqual(claude["enabled_plugins"], ["typescript-lsp@official"])
        self.assertIn("env", claude["keys"])
        self.assertIn("model", settings["~/.codex/config.toml"]["keys"])

    def test_mcp_reports_server_names_per_scope(self) -> None:
        mcp = {row["path"]: row for row in self.report["mcp"]}
        self.assertEqual(mcp["~/.claude.json"]["servers"], ["sentry"])
        self.assertEqual(mcp["~/.claude.json"]["local_servers"], ["local-db"])
        self.assertEqual(mcp[".mcp.json"]["servers"], ["figma"])
        self.assertEqual(mcp["~/.codex/config.toml"]["servers"], ["linear"])

    def test_plugins_and_hosts_are_summarized(self) -> None:
        self.assertEqual(self.report["plugins"]["enabled"], ["typescript-lsp@official"])
        self.assertEqual(self.report["plugins"]["marketplaces"], ["official", "team-tools"])
        hosts = {row["host"]: row for row in self.report["hosts"]}
        self.assertTrue(hosts["claude-code"]["home_dir"])
        self.assertTrue(hosts["codex"]["home_dir"])
        self.assertFalse(hosts["cursor"]["home_dir"])
        self.assertGreater(hosts["claude-code"]["repo_entries"], 0)

    def test_skill_shadowing_is_flagged(self) -> None:
        self.assertEqual(
            self.report["duplicate_skill_names"],
            [
                {
                    "name": "review-kit",
                    "paths": [
                        ".claude/skills/review-kit/SKILL.md",
                        "~/.claude/skills/review-kit/SKILL.md",
                    ],
                }
            ],
        )
        skill = self.report["skills"][0]
        self.assertTrue(skill["name_matches_dir"])
        self.assertGreater(skill["description_chars"], 20)

    def test_agents_are_listed_by_name(self) -> None:
        self.assertEqual([row["name"] for row in self.report["agents"]], ["reviewer"])


class InventoryEdgeCaseTest(unittest.TestCase):
    def test_global_only_when_no_repo_is_given(self) -> None:
        with TemporaryDirectory() as tmp:
            home = Path(tmp).resolve()
            write(home, ".claude/CLAUDE.md", "hello\n")
            report = inv.inventory(home, None)
        self.assertIsNone(report["repo"])
        self.assertEqual([row["scope"] for row in report["instruction_files"]], ["global"])

    def test_repo_equal_to_home_is_not_scanned_twice(self) -> None:
        with TemporaryDirectory() as tmp:
            home = Path(tmp).resolve()
            write(home, "AGENTS.md", "hi\n")
            report = inv.inventory(home, home)
        self.assertIsNone(report["repo"])
        self.assertEqual(report["instruction_files"], [])
        self.assertTrue(any("home directory" in note for note in report["notes"]))

    def test_folded_description_is_measured(self) -> None:
        skill = "---\nname: big\ndescription: >\n  Line one of it.\n  Line two of it.\n---\n"
        with TemporaryDirectory() as tmp:
            home = Path(tmp).resolve()
            write(home, ".claude/skills/big/SKILL.md", skill)
            report = inv.inventory(home, None)
        self.assertEqual(
            report["skills"][0]["description_chars"], len("Line one of it. Line two of it.")
        )

    def test_main_rejects_a_missing_directory(self) -> None:
        buffer = io.StringIO()
        with TemporaryDirectory() as tmp, redirect_stdout(buffer):
            code = inv.main(["--home", tmp, "--repo", str(Path(tmp) / "missing")])
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(buffer.getvalue())["success"])


if __name__ == "__main__":
    unittest.main()
