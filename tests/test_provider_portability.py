from __future__ import annotations

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def skill_files() -> list[Path]:
    return sorted((REPO_ROOT / "plugins").glob("*/skills/*/SKILL.md"))


class ProviderPortabilityTest(unittest.TestCase):
    def test_all_skills_have_standard_frontmatter(self) -> None:
        for path in skill_files():
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"), path)
            end = text.find("\n---", 4)
            self.assertGreater(end, 0, path)
            frontmatter = text[4:end]
            self.assertRegex(frontmatter, r"(?m)^name:\s*\S+", path)
            self.assertRegex(frontmatter, r"(?m)^description:\s*.+", path)

    def test_portable_skills_avoid_claude_install_variables(self) -> None:
        banned = ("${CLAUDE_PLUGIN_ROOT}", "${CLAUDE_SKILL_DIR}")
        offenders: list[str] = []
        for path in skill_files():
            text = path.read_text(encoding="utf-8")
            for token in banned:
                if token in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)} contains {token}")
        self.assertEqual(offenders, [])

    def test_claude_marketplace_versions_match_plugin_manifests(self) -> None:
        marketplace = json.loads((REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        mismatches: list[str] = []
        for entry in marketplace["plugins"]:
            manifest_path = REPO_ROOT / entry["source"] / ".claude-plugin" / "plugin.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if entry["version"] != manifest["version"]:
                mismatches.append(f"{entry['name']}: marketplace={entry['version']} manifest={manifest['version']}")
        self.assertEqual(mismatches, [])

    def test_root_agent_instructions_exist(self) -> None:
        text = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("Provider", text)
        self.assertIn("Portability", text)


if __name__ == "__main__":
    unittest.main()
