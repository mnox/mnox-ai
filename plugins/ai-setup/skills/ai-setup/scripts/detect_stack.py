#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Detect a repository's stack from its manifests and emit it as JSON.

Reads dependency manifests, lockfiles, task runners, and marker files under a
repository (bounded depth, vendored directories skipped) and reports the
technologies in use with their versions, the commands the repo declares, the
conventional commands for detected tools, pinned runtimes, monorepo layout, and
role-family hints.

Read-only: nothing in the repository is executed or modified. Commands marked
"declared" come from a manifest; commands marked "inferred" are only the
conventional invocation for a detected tool and must be run successfully once
before they are written into any instruction file.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import posixpath
import re
import sys
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

Json = Mapping[str, "Json"] | Sequence["Json"] | str | int | float | bool | None
T = TypeVar("T")

SCHEMA = "ai-setup.stack.v1"
MAX_SOURCES = 5
MAX_COMMAND_DIRS = 12
IGNORED_DIRS = frozenset(
    {
        "node_modules",
        "dist",
        "build",
        "out",
        "target",
        "vendor",
        "venv",
        "__pycache__",
        "coverage",
        "deps",
        "_build",
        "Pods",
        "obj",
        "site-packages",
    }
)
VISIBLE_DOT_DIRS = frozenset({".github", ".circleci", ".storybook"})
CATEGORY_ORDER = (
    "language",
    "framework",
    "api",
    "state",
    "data-fetching",
    "ui",
    "styling",
    "orm",
    "build",
    "test",
    "e2e",
    "lint",
    "format",
    "typecheck",
    "data",
    "ml-ai",
    "infra",
    "ci",
    "docs",
    "library",
)


@dataclass(frozen=True)
class Signal:
    name: str
    category: str
    families: tuple[str, ...] = ()


@dataclass(frozen=True)
class Finding:
    name: str
    category: str
    version: str | None
    source: str
    families: tuple[str, ...]


@dataclass(frozen=True)
class Command:
    intent: str
    command: str
    source: str
    confidence: str
    cwd: str


@dataclass(frozen=True)
class Report:
    findings: tuple[Finding, ...]
    commands: tuple[Command, ...]
    managers: tuple[tuple[str, str], ...]
    manifest_dir: str | None


Parser = Callable[[Path, Path], list[Finding]]
CommandReader = Callable[[Path, Path], list[Command]]


def sig(name: str, category: str, *families: str) -> Signal:
    return Signal(name, category, families)


JS_PACKAGES: dict[str, Signal] = {
    "typescript": sig("typescript", "language"),
    "react": sig("react", "framework", "frontend"),
    "next": sig("nextjs", "framework", "frontend"),
    "vue": sig("vue", "framework", "frontend"),
    "nuxt": sig("nuxt", "framework", "frontend"),
    "svelte": sig("svelte", "framework", "frontend"),
    "@sveltejs/kit": sig("sveltekit", "framework", "frontend"),
    "@angular/core": sig("angular", "framework", "frontend"),
    "solid-js": sig("solid", "framework", "frontend"),
    "astro": sig("astro", "framework", "frontend"),
    "@remix-run/react": sig("remix", "framework", "frontend"),
    "react-router": sig("react-router", "framework", "frontend"),
    "react-native": sig("react-native", "framework", "mobile"),
    "expo": sig("expo", "framework", "mobile"),
    "electron": sig("electron", "framework", "frontend"),
    "express": sig("express", "framework", "backend"),
    "fastify": sig("fastify", "framework", "backend"),
    "@nestjs/core": sig("nestjs", "framework", "backend"),
    "hono": sig("hono", "framework", "backend"),
    "koa": sig("koa", "framework", "backend"),
    "@trpc/server": sig("trpc", "api", "backend"),
    "graphql": sig("graphql", "api"),
    "@apollo/client": sig("apollo-client", "data-fetching", "frontend"),
    "@tanstack/react-query": sig("tanstack-query", "data-fetching", "frontend"),
    "swr": sig("swr", "data-fetching", "frontend"),
    "@reduxjs/toolkit": sig("redux-toolkit", "state", "frontend"),
    "redux": sig("redux", "state", "frontend"),
    "zustand": sig("zustand", "state", "frontend"),
    "jotai": sig("jotai", "state", "frontend"),
    "mobx": sig("mobx", "state", "frontend"),
    "tailwindcss": sig("tailwindcss", "styling", "frontend"),
    "styled-components": sig("styled-components", "styling", "frontend"),
    "@emotion/react": sig("emotion", "styling", "frontend"),
    "sass": sig("sass", "styling", "frontend"),
    "@mui/material": sig("mui", "ui", "frontend"),
    "@chakra-ui/react": sig("chakra-ui", "ui", "frontend"),
    "antd": sig("antd", "ui", "frontend"),
    "vite": sig("vite", "build", "frontend"),
    "webpack": sig("webpack", "build", "frontend"),
    "@rspack/core": sig("rspack", "build", "frontend"),
    "esbuild": sig("esbuild", "build"),
    "rollup": sig("rollup", "build"),
    "turbo": sig("turborepo", "build"),
    "vitest": sig("vitest", "test"),
    "jest": sig("jest", "test"),
    "mocha": sig("mocha", "test"),
    "@testing-library/react": sig("testing-library", "test", "frontend"),
    "@playwright/test": sig("playwright", "e2e"),
    "cypress": sig("cypress", "e2e"),
    "storybook": sig("storybook", "docs", "frontend"),
    "eslint": sig("eslint", "lint"),
    "@biomejs/biome": sig("biome", "lint"),
    "oxlint": sig("oxlint", "lint"),
    "prettier": sig("prettier", "format"),
    "prisma": sig("prisma", "orm", "backend"),
    "@prisma/client": sig("prisma", "orm", "backend"),
    "drizzle-orm": sig("drizzle", "orm", "backend"),
    "typeorm": sig("typeorm", "orm", "backend"),
    "sequelize": sig("sequelize", "orm", "backend"),
    "mongoose": sig("mongoose", "orm", "backend"),
    "@anthropic-ai/sdk": sig("anthropic-sdk", "ml-ai", "ml-ai"),
    "openai": sig("openai-sdk", "ml-ai", "ml-ai"),
    "ai": sig("vercel-ai-sdk", "ml-ai", "ml-ai"),
    "langchain": sig("langchain", "ml-ai", "ml-ai"),
    "@modelcontextprotocol/sdk": sig("mcp-sdk", "ml-ai", "ml-ai"),
}

PHP_PACKAGES: dict[str, Signal] = {
    "laravel/framework": sig("laravel", "framework", "backend"),
    "symfony/framework-bundle": sig("symfony", "framework", "backend"),
    "phpunit/phpunit": sig("phpunit", "test"),
    "pestphp/pest": sig("pest", "test"),
    "phpstan/phpstan": sig("phpstan", "typecheck"),
    "laravel/pint": sig("pint", "format"),
}

PY_PACKAGES: dict[str, Signal] = {
    "django": sig("django", "framework", "backend"),
    "djangorestframework": sig("django-rest-framework", "api", "backend"),
    "fastapi": sig("fastapi", "framework", "backend"),
    "flask": sig("flask", "framework", "backend"),
    "starlette": sig("starlette", "framework", "backend"),
    "sqlalchemy": sig("sqlalchemy", "orm", "backend"),
    "alembic": sig("alembic", "orm", "backend"),
    "pydantic": sig("pydantic", "library"),
    "celery": sig("celery", "library", "backend"),
    "pytest": sig("pytest", "test"),
    "ruff": sig("ruff", "lint"),
    "mypy": sig("mypy", "typecheck"),
    "pyright": sig("pyright", "typecheck"),
    "black": sig("black", "format"),
    "pandas": sig("pandas", "data", "data"),
    "polars": sig("polars", "data", "data"),
    "pyspark": sig("pyspark", "data", "data"),
    "apache-airflow": sig("airflow", "data", "data"),
    "dagster": sig("dagster", "data", "data"),
    "dbt-core": sig("dbt", "data", "data"),
    "scikit-learn": sig("scikit-learn", "ml-ai", "ml-ai"),
    "torch": sig("pytorch", "ml-ai", "ml-ai"),
    "tensorflow": sig("tensorflow", "ml-ai", "ml-ai"),
    "transformers": sig("transformers", "ml-ai", "ml-ai"),
    "langchain": sig("langchain", "ml-ai", "ml-ai"),
    "anthropic": sig("anthropic-sdk", "ml-ai", "ml-ai"),
    "openai": sig("openai-sdk", "ml-ai", "ml-ai"),
    "streamlit": sig("streamlit", "framework", "data"),
}

GO_MODULES: dict[str, Signal] = {
    "github.com/gin-gonic/gin": sig("gin", "framework", "backend"),
    "github.com/labstack/echo": sig("echo", "framework", "backend"),
    "github.com/gofiber/fiber": sig("fiber", "framework", "backend"),
    "github.com/go-chi/chi": sig("chi", "framework", "backend"),
    "google.golang.org/grpc": sig("grpc", "api", "backend"),
    "gorm.io/gorm": sig("gorm", "orm", "backend"),
    "github.com/jackc/pgx": sig("pgx", "orm", "backend"),
    "github.com/stretchr/testify": sig("testify", "test"),
    "github.com/spf13/cobra": sig("cobra", "library"),
    "sigs.k8s.io/controller-runtime": sig("controller-runtime", "framework", "platform"),
    "k8s.io/client-go": sig("client-go", "library", "platform"),
}

RUST_CRATES: dict[str, Signal] = {
    "tokio": sig("tokio", "library"),
    "axum": sig("axum", "framework", "backend"),
    "actix-web": sig("actix-web", "framework", "backend"),
    "rocket": sig("rocket", "framework", "backend"),
    "tonic": sig("tonic", "api", "backend"),
    "sqlx": sig("sqlx", "orm", "backend"),
    "diesel": sig("diesel", "orm", "backend"),
    "clap": sig("clap", "library"),
    "leptos": sig("leptos", "framework", "frontend"),
    "yew": sig("yew", "framework", "frontend"),
    "tauri": sig("tauri", "framework", "frontend"),
}

RUBY_GEMS: dict[str, Signal] = {
    "rails": sig("rails", "framework", "backend"),
    "sinatra": sig("sinatra", "framework", "backend"),
    "sidekiq": sig("sidekiq", "library", "backend"),
    "rspec": sig("rspec", "test"),
    "rspec-rails": sig("rspec", "test"),
    "rubocop": sig("rubocop", "lint"),
    "turbo-rails": sig("hotwire", "framework", "frontend"),
}

ELIXIR_DEPS: dict[str, Signal] = {
    "phoenix": sig("phoenix", "framework", "backend"),
    "phoenix_live_view": sig("phoenix-liveview", "framework", "frontend"),
    "ecto": sig("ecto", "orm", "backend"),
    "ecto_sql": sig("ecto", "orm", "backend"),
    "oban": sig("oban", "library", "backend"),
    "absinthe": sig("absinthe", "api", "backend"),
    "credo": sig("credo", "lint"),
    "dialyxir": sig("dialyzer", "typecheck"),
}

JVM_MARKERS: dict[str, Signal] = {
    "spring-boot": sig("spring-boot", "framework", "backend"),
    "io.quarkus": sig("quarkus", "framework", "backend"),
    "io.micronaut": sig("micronaut", "framework", "backend"),
    "io.ktor": sig("ktor", "framework", "backend"),
    "org.jetbrains.kotlin": sig("kotlin", "language"),
    "com.android.application": sig("android", "framework", "mobile"),
    "com.android.library": sig("android", "framework", "mobile"),
    "junit": sig("junit", "test"),
}

DOTNET_MARKERS: dict[str, Signal] = {
    "Microsoft.NET.Sdk.Web": sig("aspnet-core", "framework", "backend"),
    "Microsoft.AspNetCore": sig("aspnet-core", "framework", "backend"),
    "Microsoft.EntityFrameworkCore": sig("ef-core", "orm", "backend"),
    "xunit": sig("xunit", "test"),
    "NUnit": sig("nunit", "test"),
}

DART_PACKAGES: dict[str, Signal] = {
    "flutter": sig("flutter", "framework", "mobile"),
    "flutter_riverpod": sig("riverpod", "state", "mobile"),
    "flutter_bloc": sig("bloc", "state", "mobile"),
}

MARKERS: tuple[tuple[str, Signal], ...] = (
    ("tsconfig.json", sig("typescript", "language")),
    ("next.config.*", sig("nextjs", "framework", "frontend")),
    ("vite.config.*", sig("vite", "build", "frontend")),
    ("tailwind.config.*", sig("tailwindcss", "styling", "frontend")),
    ("playwright.config.*", sig("playwright", "e2e")),
    ("cypress.config.*", sig("cypress", "e2e")),
    ("eslint.config.*", sig("eslint", "lint")),
    (".eslintrc*", sig("eslint", "lint")),
    ("biome.json*", sig("biome", "lint")),
    (".prettierrc*", sig("prettier", "format")),
    ("prettier.config.*", sig("prettier", "format")),
    ("ruff.toml", sig("ruff", "lint")),
    ("mypy.ini", sig("mypy", "typecheck")),
    ("pytest.ini", sig("pytest", "test")),
    (".golangci.y*ml", sig("golangci-lint", "lint")),
    ("gradlew", sig("gradle-wrapper", "build")),
    ("mvnw", sig("maven-wrapper", "build")),
    ("Package.swift", sig("swift-package", "language")),
    ("*.xcodeproj", sig("xcode", "build", "mobile")),
    ("*.xcworkspace", sig("xcode", "build", "mobile")),
    ("AndroidManifest.xml", sig("android", "framework", "mobile")),
    ("*.sln", sig("dotnet", "language")),
    ("*.tf", sig("terraform", "infra", "platform")),
    ("Chart.yaml", sig("helm", "infra", "platform")),
    ("kustomization.y*ml", sig("kustomize", "infra", "platform")),
    ("Pulumi.yaml", sig("pulumi", "infra", "platform")),
    ("cdk.json", sig("aws-cdk", "infra", "platform")),
    ("serverless.y*ml", sig("serverless-framework", "infra", "platform")),
    ("ansible.cfg", sig("ansible", "infra", "platform")),
    ("Dockerfile*", sig("docker", "infra")),
    ("docker-compose*.y*ml", sig("docker-compose", "infra")),
    ("compose.y*ml", sig("docker-compose", "infra")),
    ("dbt_project.yml", sig("dbt", "data", "data")),
    (".gitlab-ci.yml", sig("gitlab-ci", "ci")),
    ("Jenkinsfile", sig("jenkins", "ci")),
)

INFERRED: dict[str, tuple[tuple[str, str], ...]] = {
    "pytest": (("test", "{py}pytest"),),
    "ruff": (("lint", "{py}ruff check ."), ("format", "{py}ruff format .")),
    "mypy": (("typecheck", "{py}mypy ."),),
    "pyright": (("typecheck", "{py}pyright"),),
    "black": (("format", "{py}black ."),),
    "go": (("test", "go test ./..."), ("build", "go build ./..."), ("lint", "go vet ./...")),
    "golangci-lint": (("lint", "golangci-lint run"),),
    "rust": (
        ("test", "cargo test"),
        ("build", "cargo build"),
        ("lint", "cargo clippy"),
        ("format", "cargo fmt"),
    ),
    "elixir": (("test", "mix test"), ("format", "mix format")),
    "credo": (("lint", "mix credo"),),
    "dialyzer": (("typecheck", "mix dialyzer"),),
    "rspec": (("test", "bundle exec rspec"),),
    "rubocop": (("lint", "bundle exec rubocop"),),
    "phpunit": (("test", "vendor/bin/phpunit"),),
    "pest": (("test", "vendor/bin/pest"),),
    "phpstan": (("typecheck", "vendor/bin/phpstan analyse"),),
    "pint": (("format", "vendor/bin/pint"),),
    "terraform": (("format", "terraform fmt -check -recursive"), ("lint", "terraform validate")),
    "dotnet": (("build", "dotnet build"), ("test", "dotnet test")),
    "flutter": (("test", "flutter test"), ("lint", "flutter analyze")),
    "swift-package": (("build", "swift build"), ("test", "swift test")),
    "gradle-wrapper": (("build", "./gradlew build"), ("test", "./gradlew test")),
    "maven-wrapper": (("build", "./mvnw -q package"), ("test", "./mvnw -q test")),
}

SCRIPT_INTENTS: dict[str, tuple[str, ...]] = {
    "dev": ("dev", "start", "serve"),
    "build": ("build",),
    "test": ("test", "test:unit", "unit"),
    "e2e": ("e2e", "test:e2e"),
    "lint": ("lint", "eslint"),
    "typecheck": ("typecheck", "type-check", "check-types", "types", "tsc"),
    "format": ("format", "fmt", "prettier"),
}

TASK_INTENTS: dict[str, tuple[str, ...]] = {
    "dev": ("dev", "run", "serve"),
    "build": ("build",),
    "test": ("test",),
    "lint": ("lint",),
    "typecheck": ("typecheck", "types"),
    "format": ("fmt", "format"),
}

JS_DEP_KEYS = ("dependencies", "devDependencies", "peerDependencies")
JS_LOCKFILES = (
    ("pnpm-lock.yaml", "pnpm"),
    ("yarn.lock", "yarn"),
    ("bun.lock", "bun"),
    ("bun.lockb", "bun"),
    ("package-lock.json", "npm"),
)
PY_RUNNERS = (
    ("uv.lock", "uv"),
    ("poetry.lock", "poetry"),
    ("pdm.lock", "pdm"),
    ("Pipfile", "pipenv"),
)
RUNTIME_FILES = (
    (".nvmrc", "node"),
    (".node-version", "node"),
    (".python-version", "python"),
    (".ruby-version", "ruby"),
    (".go-version", "go"),
)
TOOL_VERSION_NAMES = {"nodejs": "node", "golang": "go"}
WORKSPACE_MARKERS = (
    ("pnpm-workspace.yaml", "pnpm-workspaces"),
    ("turbo.json", "turborepo"),
    ("nx.json", "nx"),
    ("lerna.json", "lerna"),
    ("rush.json", "rush"),
    ("go.work", "go-workspaces"),
)

MAKE_TARGET = r"(?m)^([A-Za-z0-9_.-]+)[ \t]*:(?!=)"
JUST_RECIPE = r"(?m)^([A-Za-z0-9_-]+)(?:[ \t]+[^:\n]*)?:(?!=)"
PY_PATTERN = (
    r"(?im)(?<![\w-]){name}(?![\w-])(?:\[[^\]\n]*\])?[ \t]*(?:=[ \t]*)?[\"']?[ \t]*"
    r"(?:[=~<>!^]{{1,2}})?[ \t]*(?P<v>\d[\w.]*)?"
)
GO_PATTERN = r"(?m)^\s*(?:require\s+)?{name}(?:/v\d+)?\s+v(?P<v>[\w.+-]+)"
CARGO_PATTERN = r"(?m)^\s*{name}\s*=\s*(?:(?:\"|\{{[^}}\n]*?version\s*=\s*\")(?P<v>[^\"]+))?"
GEM_PATTERN = r"(?m)^\s*gem\s+[\"']{name}[\"'](?:\s*,\s*[\"'](?P<v>[^\"']+)[\"'])?"
MIX_PATTERN = r"\{{:{name}\s*,\s*(?:\"(?P<v>[^\"]+)\")?"
PRESENCE_PATTERN = r"{name}"
YAML_KEY_PATTERN = r"(?m)^\s*{name}\s*:"


def as_dict(value: Json) -> Mapping[str, Json]:
    return value if isinstance(value, Mapping) else {}


def as_str(value: Json) -> str:
    return value if isinstance(value, str) else ""


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def read_json(path: Path) -> Mapping[str, Json]:
    try:
        loaded: Json = json.loads(read_text(path))
    except ValueError:
        return {}
    return as_dict(loaded)


def rel(repo: Path, path: Path) -> str:
    return path.relative_to(repo).as_posix()


def parse_major(version: str | None) -> int | None:
    match = re.match(r"\d+", (version or "").lstrip("^~>=<v "))
    return int(match.group()) if match else None


def spec_findings(
    specs: Mapping[str, str], table: Mapping[str, Signal], source: str
) -> list[Finding]:
    return [
        Finding(table[name].name, table[name].category, spec or None, source, table[name].families)
        for name, spec in specs.items()
        if name in table
    ]


def dependency_specs(data: Mapping[str, Json], keys: Iterable[str]) -> dict[str, str]:
    return {name: as_str(spec) for key in keys for name, spec in as_dict(data.get(key)).items()}


def package_json(repo: Path, path: Path) -> list[Finding]:
    source = rel(repo, path)
    specs = dependency_specs(read_json(path), JS_DEP_KEYS)
    findings = spec_findings(specs, JS_PACKAGES, source)
    typed = "typescript" in specs or (path.parent / "tsconfig.json").is_file()
    return findings if typed else [Finding("javascript", "language", None, source, ()), *findings]


def composer_json(repo: Path, path: Path) -> list[Finding]:
    source = rel(repo, path)
    specs = dependency_specs(read_json(path), ("require", "require-dev"))
    return [
        Finding("php", "language", specs.get("php") or None, source, ()),
        *spec_findings(specs, PHP_PACKAGES, source),
    ]


def text_scan(table: Mapping[str, Signal], pattern: str, language: str | None) -> Parser:
    def parse(repo: Path, path: Path) -> list[Finding]:
        text = read_text(path)
        source = rel(repo, path)
        hits = [
            (signal, match)
            for name, signal in table.items()
            if (match := re.search(pattern.format(name=re.escape(name)), text))
        ]
        base = [Finding(language, "language", None, source, ())] if language else []
        return base + [
            Finding(s.name, s.category, m.groupdict().get("v"), source, s.families)
            for s, m in hits
        ]

    return parse


def go_mod(repo: Path, path: Path) -> list[Finding]:
    directive = re.search(r"(?m)^go\s+(?P<v>[\d.]+)", read_text(path))
    version = directive.group("v") if directive else None
    modules = text_scan(GO_MODULES, GO_PATTERN, None)(repo, path)
    return [Finding("go", "language", version, rel(repo, path), ()), *modules]


def jvm_build(repo: Path, path: Path) -> list[Finding]:
    tool = "maven" if path.name == "pom.xml" else "gradle"
    scanned = text_scan(JVM_MARKERS, PRESENCE_PATTERN, "jvm")(repo, path)
    return [Finding(tool, "build", None, rel(repo, path), ()), *scanned]


PARSERS: tuple[tuple[str, Parser], ...] = (
    ("package.json", package_json),
    ("composer.json", composer_json),
    ("pyproject.toml", text_scan(PY_PACKAGES, PY_PATTERN, "python")),
    ("requirements*.txt", text_scan(PY_PACKAGES, PY_PATTERN, "python")),
    ("Pipfile", text_scan(PY_PACKAGES, PY_PATTERN, "python")),
    ("setup.cfg", text_scan(PY_PACKAGES, PY_PATTERN, "python")),
    ("setup.py", text_scan(PY_PACKAGES, PY_PATTERN, "python")),
    ("go.mod", go_mod),
    ("Cargo.toml", text_scan(RUST_CRATES, CARGO_PATTERN, "rust")),
    ("Gemfile", text_scan(RUBY_GEMS, GEM_PATTERN, "ruby")),
    ("mix.exs", text_scan(ELIXIR_DEPS, MIX_PATTERN, "elixir")),
    ("pom.xml", jvm_build),
    ("build.gradle*", jvm_build),
    ("*.csproj", text_scan(DOTNET_MARKERS, PRESENCE_PATTERN, "dotnet")),
    ("pubspec.yaml", text_scan(DART_PACKAGES, YAML_KEY_PATTERN, "dart")),
)


def js_package_manager(repo: Path, directory: Path, manifest: Mapping[str, Json]) -> str:
    pinned = as_str(manifest.get("packageManager")).split("@")[0]
    folders = [directory, *(p for p in directory.parents if repo in (p, *p.parents))]
    locked = (
        manager
        for folder in folders
        for lockfile, manager in JS_LOCKFILES
        if (folder / lockfile).is_file()
    )
    return pinned or next(locked, "npm")


def package_scripts(repo: Path, path: Path) -> list[Command]:
    manifest = read_json(path)
    scripts = {name: as_str(body) for name, body in as_dict(manifest.get("scripts")).items()}
    manager = js_package_manager(repo, path.parent, manifest)
    chosen = {
        intent: next(
            (n for n in names if n in scripts and "no test specified" not in scripts[n]), None
        )
        for intent, names in SCRIPT_INTENTS.items()
    }
    source = rel(repo, path)
    cwd = rel(repo, path.parent)
    return [
        Command(intent, f"{manager} run {name}", f"{source}#scripts.{name}", "declared", cwd)
        for intent, name in chosen.items()
        if name
    ]


def task_targets(runner: str, pattern: str) -> CommandReader:
    def read(repo: Path, path: Path) -> list[Command]:
        targets = set(re.findall(pattern, read_text(path)))
        chosen = {
            intent: next((n for n in names if n in targets), None)
            for intent, names in TASK_INTENTS.items()
        }
        source = rel(repo, path)
        cwd = rel(repo, path.parent)
        return [
            Command(intent, f"{runner} {name}", f"{source}#{name}", "declared", cwd)
            for intent, name in chosen.items()
            if name
        ]

    return read


DECLARED: tuple[tuple[str, CommandReader], ...] = (
    ("package.json", package_scripts),
    ("[Mm]akefile", task_targets("make", MAKE_TARGET)),
    ("GNUmakefile", task_targets("make", MAKE_TARGET)),
    ("[Jj]ustfile", task_targets("just", JUST_RECIPE)),
)


def matching(names: Iterable[str], table: Iterable[tuple[str, T]]) -> list[tuple[str, T]]:
    entries = tuple(table)
    return [
        (name, value)
        for name in names
        for pattern, value in entries
        if fnmatch.fnmatchcase(name, pattern)
    ]


def python_runner(names: Iterable[str]) -> str:
    present = set(names)
    return next((runner for lockfile, runner in PY_RUNNERS if lockfile in present), "")


def inferred_commands(findings: Iterable[Finding], cwd: str, runner: str) -> list[Command]:
    prefix = f"{runner} run " if runner else ""
    return [
        Command(intent, template.format(py=prefix), f"inferred from {f.name}", "inferred", cwd)
        for f in findings
        for intent, template in INFERRED.get(f.name, ())
    ]


def analyze_dir(repo: Path, directory: Path, names: list[str]) -> Report:
    cwd = rel(repo, directory)
    parsed = [
        finding
        for name, parser in matching(names, PARSERS)
        for finding in parser(repo, directory / name)
    ]
    marked = [
        Finding(signal.name, signal.category, None, rel(repo, directory / name), signal.families)
        for name, signal in matching(names, MARKERS)
    ]
    workflows = (
        [Finding("github-actions", "ci", None, f"{cwd}/", ())]
        if cwd == ".github/workflows" and any(n.endswith((".yml", ".yaml")) for n in names)
        else []
    )
    findings = parsed + marked + workflows
    declared = [
        command
        for name, reader in matching(names, DECLARED)
        for command in reader(repo, directory / name)
    ]
    runner = python_runner(names)
    js_managers = [
        ("js", js_package_manager(repo, directory, read_json(directory / name)))
        for name in names
        if name == "package.json"
    ]
    py_managers = [("python", runner)] if runner else []
    return Report(
        tuple(findings),
        tuple(declared + inferred_commands(findings, cwd, runner)),
        tuple(js_managers + py_managers),
        cwd if parsed else None,
    )


def walk(repo: Path, max_depth: int) -> Iterator[tuple[Path, list[str]]]:
    for current, dirnames, filenames in os.walk(repo):
        directory = Path(current)
        depth = len(directory.relative_to(repo).parts)
        names = sorted(filenames) + sorted(dirnames)
        dirnames[:] = (
            sorted(
                d
                for d in dirnames
                if d not in IGNORED_DIRS and (not d.startswith(".") or d in VISIBLE_DOT_DIRS)
            )
            if depth < max_depth
            else []
        )
        yield directory, names


def dedupe_findings(findings: Iterable[Finding]) -> list[Finding]:
    ranked = sorted(findings, key=lambda f: f.version is not None)
    unique = {(f.name, posixpath.dirname(f.source)): f for f in ranked}
    return sorted(unique.values(), key=lambda f: (f.source, f.name))


def merge_commands(commands: Iterable[Command]) -> list[Command]:
    ranked = sorted(commands, key=lambda c: c.confidence == "declared")
    unique = {(c.intent, c.cwd): c for c in ranked}
    return sorted(unique.values(), key=lambda c: (c.cwd != ".", c.cwd, c.intent))


def category_rank(category: str) -> int:
    return CATEGORY_ORDER.index(category) if category in CATEGORY_ORDER else len(CATEGORY_ORDER)


def aggregate(findings: list[Finding]) -> list[Json]:
    groups = [
        [f for f in findings if f.name == name] for name in sorted({f.name for f in findings})
    ]
    ordered = sorted(groups, key=lambda g: (category_rank(g[0].category), g[0].name))
    return [
        {
            "name": group[0].name,
            "category": group[0].category,
            "versions": sorted({f.version for f in group if f.version}),
            "majors": sorted({m for f in group if (m := parse_major(f.version)) is not None}),
            "sources": sorted({f.source for f in group})[:MAX_SOURCES],
            "source_count": len({f.source for f in group}),
            "families": sorted({family for f in group for family in f.families}),
        }
        for group in ordered
    ]


def family_hints(findings: list[Finding]) -> list[Json]:
    pairs = {(family, f.name) for f in findings for family in f.families}
    evidence = {
        family: sorted(name for fam, name in pairs if fam == family)
        for family in {family for family, _ in pairs}
    }
    ranked = sorted(evidence, key=lambda family: (-len(evidence[family]), family))
    return [{"family": family, "evidence": evidence[family]} for family in ranked]


def runtimes(repo: Path) -> dict[str, str]:
    declared = re.findall(r"(?m)^([\w-]+)[ \t]+(\S+)", read_text(repo / ".tool-versions"))
    tool_versions = {TOOL_VERSION_NAMES.get(tool, tool): version for tool, version in declared}
    engines = as_str(as_dict(read_json(repo / "package.json").get("engines")).get("node"))
    pinned = {
        runtime: read_text(repo / filename).strip().lstrip("v")
        for filename, runtime in RUNTIME_FILES
        if (repo / filename).is_file()
    }
    merged = {**tool_versions, **({"node": engines} if engines else {}), **pinned}
    return {runtime: version for runtime, version in sorted(merged.items()) if version}


def monorepo(repo: Path, manifest_dirs: list[str]) -> dict[str, list[str]]:
    marked = [tool for filename, tool in WORKSPACE_MARKERS if (repo / filename).is_file()]
    js = ["js-workspaces"] if "workspaces" in read_json(repo / "package.json") else []
    cargo = ["cargo-workspace"] if "[workspace]" in read_text(repo / "Cargo.toml") else []
    return {
        "tools": marked + js + cargo,
        "manifest_dirs": [d for d in manifest_dirs if d != "."],
    }


def command_rows(commands: list[Command]) -> tuple[list[Json], int]:
    dirs = sorted({c.cwd for c in commands if c.cwd != "."})
    kept = {".", *dirs[:MAX_COMMAND_DIRS]}
    return (
        [
            {
                "intent": c.intent,
                "command": c.command,
                "cwd": c.cwd,
                "confidence": c.confidence,
                "source": c.source,
            }
            for c in commands
            if c.cwd in kept
        ],
        max(len(dirs) - MAX_COMMAND_DIRS, 0),
    )


def analyze(repo: Path, max_depth: int) -> dict[str, Json]:
    reports = [analyze_dir(repo, directory, names) for directory, names in walk(repo, max_depth)]
    findings = dedupe_findings(f for report in reports for f in report.findings)
    commands = merge_commands(c for report in reports for c in report.commands)
    rows, omitted_dirs = command_rows(commands)
    manifest_dirs = sorted(report.manifest_dir for report in reports if report.manifest_dir)
    managers = {pair for report in reports for pair in report.managers}
    notes = [
        *(["no dependency manifests found"] if not manifest_dirs else []),
        *(
            [f"commands for {omitted_dirs} more package directories omitted"]
            if omitted_dirs
            else []
        ),
        *(
            ["inferred commands are unverified: run each once before recording it"]
            if any(c.confidence == "inferred" for c in commands)
            else []
        ),
    ]
    return {
        "schema": SCHEMA,
        "repo": repo.as_posix(),
        "is_git": (repo / ".git").exists(),
        "max_depth": max_depth,
        "stack": aggregate(findings),
        "commands": rows,
        "package_managers": {
            ecosystem: sorted(manager for eco, manager in managers if eco == ecosystem)
            for ecosystem in sorted({eco for eco, _ in managers})
        },
        "runtimes": runtimes(repo),
        "monorepo": monorepo(repo, manifest_dirs),
        "families": family_hints(findings),
        "notes": notes,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--repo", default=".", help="Repository root to scan (default: cwd).")
    parser.add_argument("--max-depth", type=int, default=3, help="Directory depth to scan.")
    parser.add_argument("--out", help="Also write the JSON report to this path.")
    args = parser.parse_args(argv)

    repo = Path(args.repo).expanduser().resolve()
    if not repo.is_dir():
        print(json.dumps({"success": False, "error": f"not a directory: {repo.as_posix()}"}))
        return 2

    rendered = json.dumps(analyze(repo, args.max_depth), indent=2)
    if args.out:
        out = Path(args.out).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
