"""Tests for plugins/debut/skills/debut/scripts/collect_signals.py.

This is the non-trivial script: a read-only pre-scan that probes tools, walks a
git repo, and parses JSON/JSONC config. Tests build a real tiny git repo in a
temp dir (git is available in-env, no network) and mock subprocess/tool lookups
where exercising the real binary would be non-hermetic (e.g. `gh`).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from tests._loader import load_script

cs = load_script("collect_signals")

GIT = shutil.which("git")


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=str(repo),
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")


def _commit(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "--no-gpg-sign", "-m", message, "--allow-empty")


# ---------------------------------------------------------------------------
# pure / no-subprocess helpers
# ---------------------------------------------------------------------------


class PureHelpersTest(unittest.TestCase):
    def test_to_int(self) -> None:
        self.assertEqual(cs._to_int(" 42 \n"), 42)
        self.assertIsNone(cs._to_int("nope"))
        self.assertIsNone(cs._to_int(None))

    def test_strip_jsonc_removes_comments_and_trailing_commas(self) -> None:
        raw = """
        {
            // line comment
            "a": 1, /* block */
            "b": [1, 2,],
        }
        """
        data = json.loads(cs._strip_jsonc(raw))
        self.assertEqual(data, {"a": 1, "b": [1, 2]})

    def test_first_existing(self) -> None:
        with TemporaryDirectory() as d:
            root = Path(d)
            (root / "README.md").write_text("x", encoding="utf-8")
            self.assertEqual(cs.first_existing(root, ["README.rst", "README.md"]), "README.md")
            self.assertIsNone(cs.first_existing(root, ["nope.txt"]))

    def test_probe_tools_shapes(self) -> None:
        def which(tool):
            return "/bin/" + tool if tool == "git" else None

        with mock.patch.object(cs.shutil, "which", side_effect=which):
            tools = cs.probe_tools()
        self.assertTrue(tools["git"]["available"])
        self.assertEqual(tools["git"]["path"], "/bin/git")
        self.assertFalse(tools["gitleaks"]["available"])

    def test_detect_mode_hint(self) -> None:
        self.assertEqual(cs.detect_mode_hint({"available": False})["suggested"], "readiness")
        self.assertEqual(
            cs.detect_mode_hint({"available": True, "unpushed_commits": 3})["suggested"],
            "pre-push",
        )
        self.assertEqual(
            cs.detect_mode_hint({"available": True, "unpushed_commits": 0})["suggested"],
            "readiness",
        )


class RunTest(unittest.TestCase):
    def test_run_success(self) -> None:
        res = cs.run(["git", "--version"]) if GIT else cs.run(["true"])
        self.assertTrue(res["ok"])
        self.assertEqual(res["code"], 0)

    def test_run_missing_binary(self) -> None:
        res = cs.run(["definitely-not-a-real-binary-xyz"])
        self.assertFalse(res["ok"])
        self.assertEqual(res["err"], "not-found")

    def test_run_timeout(self) -> None:
        with mock.patch.object(
            cs.subprocess, "run", side_effect=subprocess.TimeoutExpired(cmd="x", timeout=1)
        ):
            res = cs.run(["whatever"])
        self.assertFalse(res["ok"])
        self.assertEqual(res["err"], "timeout")

    def test_run_nonzero_code(self) -> None:
        # `false` reliably exits nonzero; verifies ok=False with a real return code.
        res = cs.run(["sh", "-c", "exit 3"])
        self.assertFalse(res["ok"])
        self.assertEqual(res["code"], 3)


# ---------------------------------------------------------------------------
# file-presence matrix (no git needed)
# ---------------------------------------------------------------------------


class PresenceTest(unittest.TestCase):
    def test_collect_presence_detects_files(self) -> None:
        with TemporaryDirectory() as d:
            root = Path(d)
            (root / "README.md").write_text("x", encoding="utf-8")
            (root / "LICENSE").write_text("MIT", encoding="utf-8")
            (root / "package.json").write_text("{}", encoding="utf-8")
            (root / "package-lock.json").write_text("{}", encoding="utf-8")
            (root / ".github" / "workflows").mkdir(parents=True)
            (root / ".github" / "workflows" / "ci.yml").write_text("on: push", encoding="utf-8")
            (root / ".github" / "ISSUE_TEMPLATE").mkdir(parents=True)
            (root / ".github" / "ISSUE_TEMPLATE" / "bug.md").write_text("b", encoding="utf-8")

            m = cs.collect_presence(root)
            self.assertTrue(m["readme"]["present"])
            self.assertEqual(m["readme"]["path"], "README.md")
            self.assertTrue(m["license"]["present"])
            self.assertTrue(m["package_json"]["present"])
            self.assertTrue(m["lockfiles"]["any"])
            self.assertIn("package-lock.json", m["lockfiles"]["present"])
            self.assertTrue(m["ci_workflows"]["present"])
            self.assertEqual(m["ci_workflows"]["files"], ["ci.yml"])
            self.assertTrue(m["issue_templates"]["dir_present"])
            self.assertEqual(m["issue_templates"]["templates"], ["bug.md"])

    def test_collect_presence_empty_dir(self) -> None:
        with TemporaryDirectory() as d:
            m = cs.collect_presence(Path(d))
            self.assertFalse(m["readme"]["present"])
            self.assertFalse(m["lockfiles"]["any"])
            self.assertFalse(m["ci_workflows"]["present"])
            self.assertFalse(m["issue_templates"]["dir_present"])


# ---------------------------------------------------------------------------
# tsconfig / package.json parsing
# ---------------------------------------------------------------------------


class TsconfigTest(unittest.TestCase):
    def test_no_tsconfig(self) -> None:
        with TemporaryDirectory() as d:
            self.assertFalse(cs.collect_tsconfig(Path(d), None)["available"])

    def test_parses_strict_jsonc(self) -> None:
        with TemporaryDirectory() as d:
            root = Path(d)
            (root / "tsconfig.json").write_text(
                '{\n  // strict project\n  "compilerOptions": { "strict": true, },\n}\n',
                encoding="utf-8",
            )
            res = cs.collect_tsconfig(root, "tsconfig.json")
            self.assertTrue(res["parsed"])
            self.assertTrue(res["strict"])

    def test_malformed_tsconfig(self) -> None:
        with TemporaryDirectory() as d:
            root = Path(d)
            (root / "tsconfig.json").write_text("{ this is : not json at all ", encoding="utf-8")
            res = cs.collect_tsconfig(root, "tsconfig.json")
            self.assertTrue(res["available"])
            self.assertFalse(res["parsed"])


class PackageJsonTest(unittest.TestCase):
    def test_no_package_json(self) -> None:
        with TemporaryDirectory() as d:
            self.assertFalse(cs.collect_package_json(Path(d), None)["available"])

    def test_summary_fields(self) -> None:
        with TemporaryDirectory() as d:
            root = Path(d)
            pkg = {
                "name": "demo",
                "version": "1.0.0",
                "license": "MIT",
                "scripts": {"test": "vitest", "lint": "eslint ."},
                "dependencies": {"left-pad": "1.0.0"},
                "devDependencies": {"vitest": "1.0.0"},
            }
            (root / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
            res = cs.collect_package_json(root, "package.json")
            self.assertTrue(res["parsed"])
            self.assertEqual(res["name"], "demo")
            self.assertTrue(res["has_test_script"])
            self.assertTrue(res["has_lint_script"])
            self.assertEqual(res["dependency_count"], 1)
            self.assertIn("vitest", res["test_runners_detected"])

    def test_malformed_package_json(self) -> None:
        with TemporaryDirectory() as d:
            root = Path(d)
            (root / "package.json").write_text("{ broken", encoding="utf-8")
            res = cs.collect_package_json(root, "package.json")
            self.assertTrue(res["available"])
            self.assertFalse(res["parsed"])


# ---------------------------------------------------------------------------
# test-file scan
# ---------------------------------------------------------------------------


class TestFileScanTest(unittest.TestCase):
    def test_counts_test_files_and_skips_node_modules(self) -> None:
        with TemporaryDirectory() as d:
            root = Path(d)
            (root / "src").mkdir()
            (root / "src" / "a.test.ts").write_text("t", encoding="utf-8")
            (root / "src" / "b.spec.jsx").write_text("t", encoding="utf-8")
            (root / "src" / "plain.ts").write_text("t", encoding="utf-8")
            (root / "node_modules" / "pkg").mkdir(parents=True)
            (root / "node_modules" / "pkg" / "ignored.test.js").write_text("t", encoding="utf-8")
            res = cs.collect_test_files(root)
            self.assertEqual(res["test_file_count"], 2)
            self.assertFalse(res["capped"])


# ---------------------------------------------------------------------------
# git-dependent collectors (real temp repo)
# ---------------------------------------------------------------------------


@unittest.skipIf(GIT is None, "git not available")
class GitCollectorsTest(unittest.TestCase):
    def test_is_git_repo_true_and_false(self) -> None:
        with TemporaryDirectory() as d:
            repo = Path(d) / "r"
            _init_repo(repo)
            self.assertTrue(cs.is_git_repo(repo.resolve()))
            non = Path(d) / "plain"
            non.mkdir()
            self.assertFalse(cs.is_git_repo(non.resolve()))

    def test_collect_git_reports_branch_and_commits(self) -> None:
        with TemporaryDirectory() as d:
            repo = Path(d) / "r"
            _init_repo(repo)
            (repo / "f.txt").write_text("hi", encoding="utf-8")
            _commit(repo, "initial commit")
            _commit(repo, "second commit")
            tools = {"git": {"available": True}}
            info = cs.collect_git(repo.resolve(), tools)
            self.assertTrue(info["available"])
            self.assertIsNotNone(info["head_sha"])
            self.assertTrue(info.get("no_upstream"))
            # no upstream -> all commits counted as unpushed
            self.assertEqual(info["unpushed_commits"], 2)

    def test_collect_git_when_git_unavailable(self) -> None:
        with TemporaryDirectory() as d:
            info = cs.collect_git(Path(d).resolve(), {"git": {"available": False}})
            self.assertFalse(info["available"])
            self.assertIn("not installed", info["reason"])

    def test_collect_git_non_repo(self) -> None:
        with TemporaryDirectory() as d:
            info = cs.collect_git(Path(d).resolve(), {"git": {"available": True}})
            self.assertFalse(info["available"])
            self.assertIn("not a git work tree", info["reason"])

    def test_tracked_cruft_flags_committed_secrets(self) -> None:
        with TemporaryDirectory() as d:
            repo = Path(d) / "r"
            _init_repo(repo)
            (repo / ".env").write_text("SECRET=1", encoding="utf-8")
            (repo / "key.pem").write_text("-----BEGIN-----", encoding="utf-8")
            (repo / "clean.py").write_text("print(1)", encoding="utf-8")
            _commit(repo, "add files")
            res = cs.collect_tracked_cruft(repo.resolve(), git_available=True)
            self.assertTrue(res["available"])
            self.assertIn(".env", res["files"])
            self.assertIn("key.pem", res["files"])
            self.assertNotIn("clean.py", res["files"])
            self.assertFalse(res["capped"])

    def test_tracked_cruft_git_unavailable(self) -> None:
        res = cs.collect_tracked_cruft(Path("/tmp").resolve(), git_available=False)
        self.assertFalse(res["available"])

    def test_commit_smells_detects_terms(self) -> None:
        with TemporaryDirectory() as d:
            repo = Path(d) / "r"
            _init_repo(repo)
            _commit(repo, "WIP do not merge")
            _commit(repo, "proper feature commit")
            _commit(repo, "fixup typo")
            res = cs.collect_commit_smells(repo.resolve(), git_available=True)
            self.assertTrue(res["available"])
            terms = {h["term"] for h in res["hits"]}
            self.assertIn("wip", terms)
            self.assertIn("fixup", terms)
            self.assertEqual(res["hit_count"], 2)

    def test_collect_tags_semver(self) -> None:
        with TemporaryDirectory() as d:
            repo = Path(d) / "r"
            _init_repo(repo)
            _commit(repo, "init")
            _git(repo, "tag", "v1.2.3")
            _git(repo, "tag", "nightly")
            res = cs.collect_tags(repo.resolve(), git_available=True)
            self.assertTrue(res["has_semver_tag"])
            self.assertIn("v1.2.3", res["semver_tags"])
            self.assertEqual(res["semver_tag_count"], 1)
            self.assertEqual(res["total_tags"], 2)


# ---------------------------------------------------------------------------
# visibility (gh) — mocked, never hits the network
# ---------------------------------------------------------------------------


class VisibilityTest(unittest.TestCase):
    def test_gh_unavailable(self) -> None:
        res = cs.collect_visibility(Path("."), {"gh": {"available": False}})
        self.assertFalse(res["available"])
        self.assertIn("gh not installed", res["reason"])

    def test_gh_success_parsed(self) -> None:
        payload = {
            "visibility": "PUBLIC",
            "isPrivate": False,
            "nameWithOwner": "mnox/repo",
            "description": "a thing",
            "homepageUrl": "https://example.com",
            "repositoryTopics": [{"name": "cli"}, {"name": "python"}],
            "licenseInfo": {"spdxId": "MIT", "name": "MIT License"},
        }
        with mock.patch.object(
            cs, "run", return_value={"ok": True, "code": 0, "out": json.dumps(payload), "err": ""}
        ):
            res = cs.collect_visibility(Path("."), {"gh": {"available": True}})
        self.assertTrue(res["available"])
        self.assertEqual(res["visibility"], "PUBLIC")
        self.assertTrue(res["description_set"])
        self.assertEqual(res["topics"], ["cli", "python"])
        self.assertEqual(res["license_spdx"], "MIT")

    def test_gh_non_json(self) -> None:
        with mock.patch.object(
            cs, "run", return_value={"ok": True, "code": 0, "out": "not json", "err": ""}
        ):
            res = cs.collect_visibility(Path("."), {"gh": {"available": True}})
        self.assertFalse(res["available"])
        self.assertIn("non-JSON", res["reason"])

    def test_gh_command_failed(self) -> None:
        with mock.patch.object(
            cs, "run", return_value={"ok": False, "code": 1, "out": "", "err": "boom"}
        ):
            res = cs.collect_visibility(Path("."), {"gh": {"available": True}})
        self.assertFalse(res["available"])
        self.assertIn("gh repo view failed", res["reason"])


# ---------------------------------------------------------------------------
# end-to-end collect() + main()
# ---------------------------------------------------------------------------


@unittest.skipIf(GIT is None, "git not available")
class CollectEndToEndTest(unittest.TestCase):
    def test_collect_full_signal_shape(self) -> None:
        with TemporaryDirectory() as d:
            repo = Path(d) / "r"
            _init_repo(repo)
            (repo / "README.md").write_text("# demo", encoding="utf-8")
            _commit(repo, "initial")
            # force gh "unavailable" so we never touch the network
            with mock.patch.object(
                cs.shutil,
                "which",
                side_effect=lambda t: "/usr/bin/git" if t == "git" else None,
            ):
                signals = cs.collect(repo)
            self.assertEqual(signals["schema_version"], 1)
            self.assertTrue(signals["repo"]["is_git_repo"])
            self.assertTrue(signals["git"]["available"])
            self.assertFalse(signals["visibility"]["available"])
            self.assertTrue(signals["file_presence"]["readme"]["present"])
            self.assertIn("mode_hint", signals)


class MainTest(unittest.TestCase):
    def test_main_missing_repo_emits_valid_json_exit0(self) -> None:
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cs.main(["--repo", "/path/that/does/not/exist"])
        self.assertEqual(code, 0)  # never crashes; always exits 0
        payload = json.loads(buf.getvalue().strip())
        self.assertFalse(payload["repo"]["exists"])
        self.assertEqual(payload["error"], "repo path does not exist")

    def test_main_writes_out_file(self) -> None:
        import io
        from contextlib import redirect_stdout

        with TemporaryDirectory() as d:
            root = Path(d)
            out = root / "nested" / "signals.json"
            buf = io.StringIO()
            with mock.patch.object(
                cs.shutil, "which", side_effect=lambda t: None
            ), redirect_stdout(buf):
                code = cs.main(["--repo", str(root), "--out", str(out)])
            self.assertEqual(code, 0)
            self.assertTrue(out.exists())
            on_disk = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(on_disk["schema_version"], 1)


if __name__ == "__main__":
    unittest.main()
