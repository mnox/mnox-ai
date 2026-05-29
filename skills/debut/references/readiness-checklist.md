# debut — consolidated readiness checklist

The full check catalog across all 6 domains, plus the authoritative sources each
check is grounded in. Agents own their domain section; this file is the
single reference an agent (or a curious human) reads to see the whole surface.

---

## D1 — secrets-history (weight 30) · SAFE SCANS ONLY · remediation is FLAG-ONLY

- **Full-history + working-tree secret scan.** Prefer tools when available:
  - `gitleaks detect --source . --redact -v` (scans all history)
  - `gitleaks dir .` (working tree)
  - `trufflehog git file://. --results=verified,unknown` — a **VERIFIED** hit is a
    live credential = 🔴 CRITICAL hard-block.
  - Tools absent → degraded mode: regex greps for AWS `AKIA`, PEM private-key
    blocks (`-----BEGIN .* PRIVATE KEY-----`), Slack `xox[baprs]-`, GitHub
    `ghp_`/`gho_`, bearer tokens, DB connection strings. **Clearly label degraded.**
- **Tracked cruft that should be git-ignored:**
  `git ls-files | grep -Ei '(^|/)(\.env|\.env\..*|.*\.pem|.*\.key|id_rsa|\.DS_Store|Thumbs\.db|\.idea/|\.vscode/|node_modules/|dist/|build/|\.terraform/|.*\.log)'`
- **`.gitignore` presence + coverage** — env, creds, build artifacts, node_modules,
  IDE dirs, OS cruft.
- **Embarrassing commit messages:**
  `git log --all --pretty='%H %s%n%b'` grep
  `(?i)wip|fixup|squash|todo|hack|temp|asdf|oops|nvm|fuck|shit|damn`.
- **PII / internal-reference leakage** in messages + content: employer domains,
  `*.internal` / `*.corp` / `*.local`, internal ticket prefixes, real personal
  emails, private IPs (`10.`, `192.168.`).
- **Repo bloat:** `git-sizer --verbose` if present, else largest-blob scan via
  `git rev-list --objects --all | git cat-file --batch-check` sorted by size.
  Flag committed binaries and any blob > 1 GiB.
- **REMEDIATION RULE:** every history fix (BFG Repo-Cleaner, `git filter-repo`) is
  **DESTRUCTIVE** → mark `destructive: true`, give the exact command, NEVER run it,
  and ALWAYS prepend: *"rotate/revoke the credential FIRST — rewriting history does
  not un-leak it."*
- **HARD-BLOCK:** any verified live secret/credential OR real PII in tree or
  history → CRITICAL → 🔴 NOT READY.

## D2 — community-health (weight 20)

- **README vs Standard Readme spec:** H1 title, short description, ToC (if > 100
  lines), Install, Usage (with a fenced quickstart code block), Contributing
  pointer, License section, status/shields badges. Title-only or template-default
  README = amateur smell.
- **Health files** (search `.github/` → root → `docs/`): CONTRIBUTING.md,
  CODE_OF_CONDUCT.md, SECURITY.md, `.github/ISSUE_TEMPLATE/` (valid frontmatter),
  PULL_REQUEST_TEMPLATE.md. Bonus: SUPPORT.md, CODEOWNERS, FUNDING.yml.
- **Discoverability:** `gh repo view --json description,repositoryTopics,homepageUrl`
  (gh optional — note if unavailable): description set, ≥ 3 topics, homepage/docs URL.

## D3 — licensing (weight 15)

- **LICENSE in root** (`LICENSE` / `LICENSE.md` / `LICENSE.txt` / `COPYING`).
  **ABSENT = hard cap: the repo CANNOT be SHIP IT.**
- **`gh repo view --json licenseInfo`** resolves to a recognized SPDX id (not
  "Other" / null).
- **SPDX headers** in source (`SPDX-License-Identifier:`) — nice-to-have.
- **Third-party dep license compatibility** — flag copyleft (GPL/AGPL) deps inside
  a permissive-licensed project.

## D4 — code-quality (weight 15) · TS/Node-first, generalize to detected language

- **Linter configured + clean:** `eslint.config.*` / `.eslintrc*` / `biome.json`;
  `npx eslint . --max-warnings=0` → nonzero exit = dirty.
- **Formatter pinned + clean:** `.prettierrc*` or biome formatter;
  `prettier --check .`.
- **Strict types:** `tsconfig.json` `compilerOptions.strict === true` (ideally a
  strictest base); `npx tsc --noEmit` zero errors.
- **`any` / suppression density:** grep `: any\b`, `as any`, `<any>`, `@ts-ignore`,
  `@ts-nocheck` (prefer zero; `@ts-expect-error` with a comment is acceptable).
- **Cleanliness smells:** `console.log|console.debug|debugger`; hardcoded local
  paths (`/Users/`, `/home/[a-z]+`, `C:\Users`) + personal emails;
  TODO/FIXME/HACK/XXX density; commented-out code blocks; giant files (> 400–500
  LOC); dead exports (`ts-prune`).
- **Non-TS repos:** detect language, run the equivalent linter/formatter or mark
  N/A with a note. Do **not** fabricate findings for a stack you didn't actually run.

## D5 — tests-ci (weight 10)

- **CI workflow present** (`.github/workflows/*.yml`) with `on: pull_request`
  running lint + typecheck + test; uses `npm ci` (not `install`); status badge in
  README.
- **Tests exist + meaningful:** count `**/*.{test,spec}.*`; runner in devDeps +
  `test` script; flag "runner present but 0 test files" and trivial
  `expect(true)` smoke-only suites.
- **Coverage signal:** coverage config/threshold or a codecov badge.

## D6 — deps-release (weight 10)

- **Lockfile committed** (`package-lock.json` / `pnpm-lock.yaml` / `yarn.lock`) and
  tracked.
- **`npm audit --audit-level=high`** clean (no high/critical advisories).
- **Unused / extraneous deps** (`npx depcheck`); Dependabot/Renovate config present.
- **Releases:** SemVer git tags (`^v?\d+\.\d+\.\d+`); GitHub releases
  (`gh release list`); `CHANGELOG.md` per keepachangelog (an `## [Unreleased]`
  section, dated versions `## [x.y.z] - YYYY-MM-DD`, with
  Added/Changed/Deprecated/Removed/Fixed/Security headings).

---

## Sources

- **GitHub community-profile docs** — the canonical health-file set
  (CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, issue/PR templates, FUNDING).
  https://docs.github.com/communities
- **Standard Readme spec** — README structure contract.
  https://github.com/RichardLitt/standard-readme
- **Keep a Changelog 1.1.0** — CHANGELOG structure + change headings.
  https://keepachangelog.com/en/1.1.0/
- **Semantic Versioning 2.0.0** — version tag grammar.
  https://semver.org/
- **choosealicense.com** — license selection + SPDX identifiers.
  https://choosealicense.com/
- **gitleaks** — git secret scanner. https://github.com/gitleaks/gitleaks
- **trufflehog** — verified-secret scanner. https://github.com/trufflesecurity/trufflehog
- **BFG Repo-Cleaner** / **git-filter-repo** — history rewriting (DESTRUCTIVE).
  https://rtyley.github.io/bfg-repo-cleaner/ · https://github.com/newren/git-filter-repo
- **git-sizer** — repo bloat / large-blob analysis.
  https://github.com/github/git-sizer
- **TypeScript `strict` docs / `@tsconfig/strictest` base** — strict type posture.
  https://www.typescriptlang.org/tsconfig#strict · https://github.com/tsconfig/bases
- **OpenSSF Scorecard** — automated OSS-health/security signals.
  https://github.com/ossf/scorecard
- **OWASP NPM Security Cheat Sheet** — lockfiles, audit, supply-chain hygiene.
  https://cheatsheetseries.owasp.org/cheatsheets/NPM_Security_Cheat_Sheet.html
