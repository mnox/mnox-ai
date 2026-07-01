from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Claude-only install vars. Matched as ${VAR} or ${VAR:-fallback}; the :- form is a
# portable fallback (the skill still resolves on other hosts) and is allowed.
CLAUDE_INSTALL_VARS = ("CLAUDE_PLUGIN_ROOT", "CLAUDE_SKILL_DIR")
_INSTALL_VAR_RE = re.compile(
    r"\$\{(" + "|".join(CLAUDE_INSTALL_VARS) + r")(:-[^}]*)?\}"
)


def skill_files() -> list[Path]:
    return sorted((REPO_ROOT / "plugins").glob("*/skills/*/SKILL.md"))


def frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return ""
    end = text.find("\n---", 4)
    return text[4:end] if end > 0 else ""


def is_claude_only(text: str) -> bool:
    """A skill that declares `host: claude-code` in frontmatter is a Claude adapter
    by design (e.g. bash-gate-add manages a Claude PreToolUse hook) and is exempt
    from the portable-substrate invariant."""
    return bool(re.search(r"(?m)^\s*host:\s*claude-code\b", frontmatter(text)))


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
        """Portable skills must not *hard-resolve* bundled files through a Claude-only
        install var. Allowed: the `${VAR:-fallback}` form (degrades on other hosts),
        and any use inside a skill declared `host: claude-code`. Denylist prose that
        names the var should reference it as a bare token (`CLAUDE_PLUGIN_ROOT`), not
        the `${...}` install form."""
        offenders: list[str] = []
        for path in skill_files():
            text = path.read_text(encoding="utf-8")
            if is_claude_only(text):
                continue
            for match in _INSTALL_VAR_RE.finditer(text):
                var, fallback = match.group(1), match.group(2)
                if fallback:  # ${VAR:-...} — portable fallback, resolves off Claude
                    continue
                offenders.append(f"{path.relative_to(REPO_ROOT)} hard-resolves ${{{var}}}")
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
