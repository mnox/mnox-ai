# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-06-01

### Changed
- **Restructured into a multi-plugin marketplace.** Each skill is now its own
  independently-installable plugin under `plugins/<name>/` — install one skill,
  several, or the whole set. Replaces the single bundled `mnox-ai` plugin
  (`source: "./"`).

### Added
- `all-skills` meta-plugin — installs every skill at once via plugin `dependencies`.
- GitHub Actions CI: ruff lint, manifest JSON validation, script compilation, and unit tests.
- Unit-test suite (`tests/`) covering the bundled helper scripts.
- `CODE_OF_CONDUCT.md`, issue templates, and a pull-request template.
- Pinned `ruff.toml` lint configuration.

## [0.3.0] - 2026-05-28

First tagged public release.

### Added
- `schema-review` — review database schemas and in-code data structures.
- `compliance-review` — audit a target against SOC 2, HIPAA, or PCI-DSS.
- `util-review` — review skills, hooks, CLAUDE.md, and workflow configs.
- `debut` — pre-public open-source readiness audit.
- `SECURITY.md`, `CONTRIBUTING.md`, and `.gitignore`.

### Changed
- Genericized an example slug in `schema-review` for public release.

## [0.2.0] - 2026-05-28

### Added
- `strangler-fig` — clean-room legacy reimplementation skill.
- MIT `LICENSE` and a catalog `README`.

### Changed
- Collapsed the multi-plugin marketplace into a single bundled `mnox-ai` plugin.
- Synced `aio` with the May-2026 research refresh.

## [0.1.0] - 2026-05-12

### Added
- Initial scaffolding: the `mnox-ai` plugin marketplace with the `aio` and `curriculum` skills.

[Unreleased]: https://github.com/mnox/mnox-ai/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/mnox/mnox-ai/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/mnox/mnox-ai/releases/tag/v0.3.0
