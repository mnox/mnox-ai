# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **`apply` plugin** (0.1.0) — browser-driven job application copilot. Locates
  matching postings (LinkedIn, aggregators, company careers pages), scores fit
  0–100, tailors the resume / cover letter / screening answers to each
  individual posting, drives the application form via whatever browser-control
  surface the host provides, and tracks the pipeline in a local JSONL tracker.
  Truth-locked (tailoring changes emphasis, never facts), hard per-application
  submit gate, credentials/CAPTCHAs always handed to the human. Ships a
  tailoring guide, a per-ATS browser playbook (LinkedIn Easy Apply, Greenhouse,
  Lever, Workday, Ashby, iCIMS), and profile / cover-letter templates.
- **`bash-gate` plugin** (0.1.0) — a **PreToolUse hook**, not a skill. A
  deterministic-first gate over Bash that auto-allows provably-safe commands
  (writes confined to your dev roots, `rm` of git-clean/ignored files, safe
  `chmod`) so you stop re-approving them under `bypassPermissions` mode. Ships
  safe-by-default (auto-allows nothing until you opt in); optional LLM arbiter
  for the long tail; a `/bash-gate-add` skill to extend the classifier; a
  one-time SessionStart onboarding nudge.
- **`create-skill` plugin** (0.1.0) — author a Claude Code or cross-host Agent
  Skill end-to-end: scaffold, write against a portable authoring contract,
  structurally validate, and design-score, in one guided lifecycle. Spec-pure
  by default; Claude-only features are opt-in.
- Per-provider onboarding guides under `docs/install/` (Claude, Codex, Cursor)
  and a `scripts/smoke_host_load.py` host-load smoke test that exports skills
  into a temp tree shaped like each host's real discovery path and verifies
  they actually land, rather than trusting the exporter's own unit tests.

### Changed
- **`apply` plugin** (0.1.0 → 0.2.0) — resume tailoring now targets the
  evaluator engines big companies actually run, based on current (2025–2026)
  industry research. New `references/ats-engines.md` documents how Workday
  HiredScore (A–D per-req grading, skills inference), Taleo Req Rank +
  knockout auto-rejects, iCIMS keyword frequency, SuccessFactors, Greenhouse
  recruiter search, Lever, Ashby evidence-sentence matching, LinkedIn
  skills-match ranking, Eightfold-class deep-learning matchers, and LLM
  screeners each score resumes, with per-engine tactics. The tailoring guide
  gains tiered keyword mapping (hard skills > title > certs > soft/domain),
  placement rules (skills section + in-bullet evidence, top-third, recency,
  acronym dual forms, exact-title alignment), a quotable-evidence bullet
  formula, parse-fidelity format rules with a rendered-file round-trip check,
  and a coverage loop driven by a new stdlib `scripts/keyword_coverage.py`
  (weighted tiered scoring, ≥80 target, missing-term gap report). Truth lock
  unchanged: coverage is only ever closed with true content — the truth sets
  the score ceiling.
- **`compliance-review` plugin** — added a fifth input mode, `readiness`, which
  shifts the question from "does this artifact implement the controls" to "can
  this organization pass a SOC 2 examination," where most failures are
  evidentiary rather than technical. Readiness assesses governance, evidence
  gaps, program deliverables, phasing, and cost, and emits a risk register with
  discovery steps, fix/prevent actions, cost-of-inaction, and a
  dependency-ordered phase plan. Backed by a new
  `references/readiness-program.md`, a per-control `type` (technical vs program)
  column and governance-series (CC1–CC5) coverage in the SOC 2 catalog, and
  expanded scope-boundary guidance. New triggers include SOC 2 readiness, audit
  prep, Type I vs Type II, controls matrix, and evidence gaps.
- **`util-review` plugin** — added H008/H009 to the Hooks-Specific check
  category (non-blocking-hook checks), bringing that category from 7 to 9
  checks.
- **`config-chunks` plugin** (0.1.0 → 0.1.1) — the guidance-chunk size gate is
  now **fail-closed**: `reconcile.sh` exits non-zero on a bundle-size
  violation instead of only warning. Added a new `correction-scrutiny`
  doctrine chunk to the `recommended` group (now 9 chunks). Published the
  fail-closed gate to the plugin cache.
- **`aio` plugin** — synced the knowledge base with the latest research
  refresh (judge-validity claim, 13 evidence updates).
- **`foundry` plugin** — **decommissioned for public use.** The V0
  autonomous-fix loop (deterministic bash engine driving a Worker/Integrator
  pair over isolated git worktrees) has been retired; `/foundry-run` is now a
  compatibility shim that routes into the maintainer's private Sven Unit
  runtime, which is not distributed in this repo. The plugin is no longer
  functional for other marketplace installs and has been removed from the
  `all-skills` bundle. See `plugins/foundry/README.md`.

## [0.5.0] - 2026-06-22

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
  reranking research. The audit twin of a future `/retrieval-draft` (not yet
  built); a similar draft↔review split is planned for `/ontology-review`, but
  `/ontology-draft` doesn't exist yet either. Added to the `all-skills`
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
- **`foundry` plugin** — an autonomous-fix loop driver: drains a bucket of
  work-unit files one at a time, spawning an Opus Worker to implement each in an
  isolated git worktree and an independent Opus Integrator to review it — strictly
  serial, never pushing to a remote.

### Changed
- **Version alignment** — the established plugin suite (`aio`, `curriculum`,
  `strangler-fig`, `schema-review`, `compliance-review`, `util-review`, `debut`,
  `diagnose-queries`, `all-skills`) is brought to **0.5.0** to track the release
  line; the five plugins debuting this release (`config-chunks`, `ontology-review`,
  `retrieval-review`, `foundry`, `session-tracker`) ship at `0.1.0`.
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

[Unreleased]: https://github.com/mnox/mnox-ai/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/mnox/mnox-ai/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/mnox/mnox-ai/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/mnox/mnox-ai/releases/tag/v0.3.0
