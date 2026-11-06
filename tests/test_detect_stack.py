"""Tests for plugins/ai-setup/skills/ai-setup/scripts/detect_stack.py."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from tests._loader import load_script

ds = load_script("detect_stack")

REACT_PACKAGE = {
    "name": "web",
    "scripts": {
        "dev": "next dev",
        "build": "next build",
        "test": "vitest run",
        "lint": "eslint .",
        "typecheck": "tsc --noEmit",
    },
    "dependencies": {"react": "^19.1.0", "react-dom": "^19.1.0", "next": "15.3.0"},
    "devDependencies": {
        "typescript": "^5.7.3",
        "vitest": "^3.0.0",
        "@playwright/test": "^1.50.0",
        "eslint": "^9.0.0",
        "tailwindcss": "^4.0.0",
    },
}

FASTAPI_PYPROJECT = """\
[project]
name = "api"
dependencies = [
    "fastapi>=0.115",
    "sqlalchemy==2.0.36",
]

[dependency-groups]
dev = ["pytest>=8.3", "pytest-cov"]

[tool.ruff]
line-length = 100
"""


def write(root: Path, relative: str, content: str = "") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def by_name(report: dict) -> dict:
    return {row["name"]: row for row in report["stack"]}


def by_intent(report: dict, cwd: str = ".") -> dict:
    return {row["intent"]: row for row in report["commands"] if row["cwd"] == cwd}


class JavaScriptRepoTest(unittest.TestCase):
    def test_react_next_repo_is_detected_with_versions_and_declared_commands(self) -> None:
        with TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write(repo, "package.json", json.dumps(REACT_PACKAGE))
            write(repo, "pnpm-lock.yaml")
            write(repo, "tsconfig.json", "{}")
            write(repo, ".nvmrc", "v22\n")
            report = ds.analyze(repo, 3)

        stack = by_name(report)
        self.assertEqual(stack["react"]["majors"], [19])
        self.assertEqual(stack["nextjs"]["versions"], ["15.3.0"])
        self.assertEqual(stack["typescript"]["category"], "language")
        self.assertNotIn("javascript", stack)
        self.assertEqual(stack["playwright"]["category"], "e2e")

        commands = by_intent(report)
        self.assertEqual(commands["test"]["command"], "pnpm run test")
        self.assertEqual(commands["test"]["confidence"], "declared")
        self.assertEqual(commands["typecheck"]["source"], "package.json#scripts.typecheck")

        self.assertEqual(report["package_managers"], {"js": ["pnpm"]})
        self.assertEqual(report["runtimes"], {"node": "22"})
        self.assertEqual(report["families"][0]["family"], "frontend")
        self.assertIn("react", report["families"][0]["evidence"])

    def test_package_manager_field_beats_lockfile(self) -> None:
        with TemporaryDirectory() as tmp:
            repo = Path(tmp)
            manifest = {"packageManager": "yarn@4.5.0", "scripts": {"build": "tsc"}}
            write(repo, "package.json", json.dumps(manifest))
            write(repo, "package-lock.json", "{}")
            report = ds.analyze(repo, 3)
        self.assertEqual(by_intent(report)["build"]["command"], "yarn run build")

    def test_placeholder_test_script_is_not_a_test_command(self) -> None:
        with TemporaryDirectory() as tmp:
            repo = Path(tmp)
            scripts = {"test": 'echo "Error: no test specified" && exit 1'}
            write(repo, "package.json", json.dumps({"scripts": scripts}))
            report = ds.analyze(repo, 3)
        self.assertNotIn("test", by_intent(report))
        self.assertIn("javascript", by_name(report))

    def test_monorepo_reports_each_package_and_skips_vendored_dirs(self) -> None:
        with TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write(repo, "package.json", json.dumps({"workspaces": ["apps/*"]}))
            write(repo, "pnpm-lock.yaml")
            web = {"dependencies": {"react": "^18.3.1"}, "scripts": {"test": "vitest"}}
            api = {"dependencies": {"express": "^5.0.0"}, "scripts": {"test": "jest"}}
            write(repo, "apps/web/package.json", json.dumps(web))
            write(repo, "apps/api/package.json", json.dumps(api))
            write(repo, "node_modules/vue/package.json", json.dumps({"dependencies": {"vue": "3"}}))
            report = ds.analyze(repo, 3)

        stack = by_name(report)
        self.assertNotIn("vue", stack)
        self.assertEqual(stack["react"]["sources"], ["apps/web/package.json"])
        self.assertEqual(report["monorepo"]["tools"], ["js-workspaces"])
        self.assertEqual(report["monorepo"]["manifest_dirs"], ["apps/api", "apps/web"])
        self.assertEqual(by_intent(report, "apps/web")["test"]["command"], "pnpm run test")
        self.assertEqual({hint["family"] for hint in report["families"]}, {"frontend", "backend"})


class PythonRepoTest(unittest.TestCase):
    def test_tools_yield_inferred_commands_with_the_lockfile_runner(self) -> None:
        with TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write(repo, "pyproject.toml", FASTAPI_PYPROJECT)
            write(repo, "uv.lock")
            report = ds.analyze(repo, 3)

        stack = by_name(report)
        self.assertEqual(stack["fastapi"]["versions"], ["0.115"])
        self.assertEqual(stack["sqlalchemy"]["majors"], [2])
        self.assertEqual(stack["pytest"]["majors"], [8])
        self.assertIn("ruff", stack)

        commands = by_intent(report)
        self.assertEqual(commands["test"]["command"], "uv run pytest")
        self.assertEqual(commands["test"]["confidence"], "inferred")
        self.assertEqual(commands["lint"]["command"], "uv run ruff check .")
        self.assertTrue(any("unverified" in note for note in report["notes"]))
        self.assertEqual(report["package_managers"], {"python": ["uv"]})

    def test_similar_package_names_do_not_match(self) -> None:
        with TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write(repo, "requirements.txt", "pytest-cov==5.0\ndjangorestframework==3.15\n")
            stack = by_name(ds.analyze(repo, 3))
        self.assertNotIn("pytest", stack)
        self.assertNotIn("django", stack)
        self.assertIn("django-rest-framework", stack)

    def test_declared_task_target_beats_inferred_command(self) -> None:
        with TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write(repo, "pyproject.toml", FASTAPI_PYPROJECT)
            write(repo, "Makefile", "test:\n\tpytest -q\n\nlint:\n\truff check .\n")
            commands = by_intent(ds.analyze(repo, 3))
        self.assertEqual(commands["test"]["command"], "make test")
        self.assertEqual(commands["test"]["confidence"], "declared")
        self.assertEqual(commands["format"]["confidence"], "inferred")


class OtherEcosystemsTest(unittest.TestCase):
    def test_go_module_reports_language_version_and_modules(self) -> None:
        with TemporaryDirectory() as tmp:
            repo = Path(tmp)
            go_mod = "module example.com/svc\n\ngo 1.23\n\nrequire (\n"
            go_mod += "\tgithub.com/gin-gonic/gin v1.10.0\n\tgithub.com/jackc/pgx/v5 v5.7.1\n)\n"
            write(repo, "go.mod", go_mod)
            report = ds.analyze(repo, 3)
        stack = by_name(report)
        self.assertEqual(stack["go"]["versions"], ["1.23"])
        self.assertEqual(stack["gin"]["majors"], [1])
        self.assertEqual(stack["pgx"]["majors"], [5])
        self.assertEqual(by_intent(report)["test"]["command"], "go test ./...")

    def test_cargo_and_mix_version_forms(self) -> None:
        with TemporaryDirectory() as tmp:
            repo = Path(tmp)
            cargo = '[dependencies]\naxum = "0.8"\n'
            cargo += 'sqlx = { version = "0.8.2", features = ["postgres"] }\n'
            cargo += "tokio = { workspace = true }\n"
            write(repo, "svc/Cargo.toml", cargo)
            mix = 'defp deps do\n  [{:phoenix, "~> 1.7.0"}, {:credo, "~> 1.7"}]\nend\n'
            write(repo, "app/mix.exs", mix)
            report = ds.analyze(repo, 3)
        stack = by_name(report)
        self.assertEqual(stack["axum"]["versions"], ["0.8"])
        self.assertEqual(stack["sqlx"]["versions"], ["0.8.2"])
        self.assertEqual(stack["tokio"]["versions"], [])
        self.assertEqual(stack["phoenix"]["majors"], [1])
        self.assertEqual(by_intent(report, "app")["lint"]["command"], "mix credo")

    def test_marker_files_and_workflows_are_detected(self) -> None:
        with TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write(repo, "infra/main.tf")
            write(repo, "Dockerfile")
            write(repo, ".github/workflows/ci.yml")
            report = ds.analyze(repo, 3)
        stack = by_name(report)
        self.assertEqual(stack["terraform"]["families"], ["platform"])
        self.assertIn("docker", stack)
        self.assertIn("github-actions", stack)
        self.assertEqual(by_intent(report, "infra")["lint"]["command"], "terraform validate")


class EdgeCaseTest(unittest.TestCase):
    def test_empty_directory_reports_no_manifests(self) -> None:
        with TemporaryDirectory() as tmp:
            report = ds.analyze(Path(tmp), 3)
        self.assertEqual(report["stack"], [])
        self.assertEqual(report["commands"], [])
        self.assertIn("no dependency manifests found", report["notes"])

    def test_malformed_manifest_does_not_raise(self) -> None:
        with TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write(repo, "package.json", "{ not json")
            report = ds.analyze(repo, 3)
        self.assertEqual([row["name"] for row in report["stack"]], ["javascript"])

    def test_depth_limit_stops_the_walk(self) -> None:
        with TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write(repo, "a/b/c/d/package.json", json.dumps({"dependencies": {"react": "19"}}))
            self.assertEqual(ds.analyze(repo, 3)["stack"], [])
            self.assertIn("react", by_name(ds.analyze(repo, 4)))

    def test_parse_major(self) -> None:
        cases = {"^19.1.0": 19, "~> 1.7.0": 1, ">=18 <20": 18, "v22": 22, "workspace:*": None}
        for version, expected in cases.items():
            self.assertEqual(ds.parse_major(version), expected, version)
        self.assertIsNone(ds.parse_major(None))

    def test_main_rejects_a_missing_repo(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = ds.main(["--repo", "/definitely/not/a/real/path"])
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(buffer.getvalue())["success"])

    def test_main_writes_the_report_to_out(self) -> None:
        with TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            write(repo, "go.mod", "module x\n\ngo 1.22\n")
            out = Path(tmp) / "state" / "stack.json"
            with redirect_stdout(io.StringIO()):
                code = ds.main(["--repo", str(repo), "--out", str(out)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["schema"], ds.SCHEMA)


if __name__ == "__main__":
    unittest.main()
