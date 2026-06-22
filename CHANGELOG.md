# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **`retrieval-review` plugin** — audits a retrieval / vector-index / RAG
  pipeline for quality across seven load-bearing axes (eval foundation, corpus &
  chunking, embedding geometry, index & ANN fidelity, retrieval composition, rank
  fusion, reranking) and produces a severity-ranked findings list led by the
  defects that make a relevant document structurally unretrievable. Numeric, not
  config-only: it computes recall@k, anisotropy, effective rank, and fusion-window
  coverage where the embeddings and a labeled query set are available. Grounded in
  BEIR/MTEB evaluation methodology, the anisotropy & alignment/uniformity geometry
  literature, ANN-index recall theory, and the rank-fusion (RRF) and cross-encoder
  reranking research. The audit twin of a future `/retrieval-draft`, mirroring the
  `/ontology-review` ↔ `/ontology-draft` pairing. Added to the `all-skills`
  meta-plugin.
- **`config-chunks` utility plugin** — a package manager for agent-instruction
  guidance. Contributing plugins publish versioned, scored guidance **chunks**;
  a reconciler dedups them by name (highest version wins), sorts by `order`,
  prunes stale ones, and assembles a single `~/.claude/chunks/bundle.md`. The
  bundle is wired into one or more host instruction files: `claude` (an `@import`
  line in `CLAUDE.md`) and/or `agents` (the bundle body **inlined** in
  `AGENTS.md`, which has no import mechanism). Targets are selected in
  `~/.claude/config/chunks.yaml` and default to auto-detect. Ships an `ai-setup`
  guided-onboarding wizard, a `permission-setup` skill (recommends conservative
  per-provider permissions and delegates the write — never mutates security
  config), an `ideation` problem-framing skill, a `chunks` management skill, a
  `chunk-review` scoring rubric, and a starter library of universal guidance
  chunks. The chunk format and bundle are provider-agnostic (Claude Code via
  `@import`; Codex/Cursor/etc. via the universal `AGENTS.md` substrate, with
  `set-agents-path` to pin the host's file); auto-refresh is Claude-native via a
  SessionStart hook, with a documented manual reconcile on other hosts.
- **`ontology-review` plugin** — audits a knowledge graph or ontology for
  structural health across seven axes (orthogonality, granularity, taxonomic
  hygiene, identity & rigidity, relationship semantics, competency questions,
  inference safety) and produces a severity-ranked findings list led by
  inference-corrupting issues. Grounded in OntoClean meta-properties, the OOPS!
  pitfall catalogue, Grüninger & Fox competency questions, and Gómez-Pérez
  consistency/completeness/conciseness dimensions. Added to the `all-skills`
  meta-plugin.
- **`session-tracker` utility plugin** — a local MCP server (TypeScript + Bun)
  that indexes and searches your Claude Code / Cursor / Codex agent sessions:
  list, search, label, inspect file-change history, and view token usage. Search
  is lexical (FTS5) by default — zero network calls, zero cost. Semantic search
  is opt-in via the `session_config_set` tool (OpenAI key or a fully-local
  embedder); the server prompts once to offer it and never re-asks. First
  standalone utility-class plugin in the marketplace; requires [Bun](https://bun.sh).

### Changed
- **`strangler-fig` 0.4.0 → 0.5.0** — adds a **leakage audit** (taint / provenance
  audit) to the clean-room rewrite. The skill now captures the legacy's structural
  fingerprints up front and, at each firewall crossing, verifies nothing structural
  leaked into the spec, harness, or final port — so no legacy implementation detail
  (algorithm shape, magic constant, naming idiom) becomes load-bearing in the
  "clean" design. New `leakage-auditor` sub-agent (a distiller-peer that sees the
  inventory and legacy path, never the builder's work) plus Phase 2.5 (screen
  spec + harness pre-crossing) and Phase 4.5 (screen greenfield for reconstructed
  legacy structure).

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
