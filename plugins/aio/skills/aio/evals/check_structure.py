#!/usr/bin/env python3
"""
AIO skill — deterministic structural eval suite.

Validates the invariants that must hold for the /aio + /aio-update skills to be
correct, independent of any LLM behavior. Run on every /aio-update (Step 5) and
any time the skill is hand-edited.

  python3 evals/check_structure.py            # human-readable report
  python3 evals/check_structure.py --quiet    # only FAIL/WARN lines + summary

Exit code: 0 if no FAILs (WARNs allowed), 1 if any FAIL. Stdlib only — no deps.

The checks, and why each exists:
  1. Files present            — the skill's referenced files actually exist.
  2. Frontmatter valid        — name/description present; name matches dir.
  3. Size budgets             — core SKILL.md is the always-loaded body; cap its
                                context cost. KB grows by consolidation, not bloat.
  4. Pointer integrity        — every [KB:id] resolves to exactly one ### [KB:id]
                                heading (duplicates break /aio-update's find-update).
  5. Tier discipline          — the core skill carries RULES, never provenance.
                                No arxiv/CVE/DOI/"et al" may leak into SKILL.md.
  6. KB format                — every claim block has a **Rule:** line.
  7. Trail discipline         — per-claim supersession trails stay compressed.
  8. aio-update paths         — the file paths the updater writes to exist.
  9. Registry cross-check     — every arxiv id cited in the KB is logged in the
                                dawks sources registry (catches unverified or
                                un-logged citations; WARN, since the registry may
                                legitimately lag a manual edit).
"""

import re
import sys
from pathlib import Path

# ---- locations (relative to this file: <skill>/evals/check_structure.py) -----
EVALS_DIR = Path(__file__).resolve().parent
AIO_DIR = EVALS_DIR.parent                       # ~/.claude/skills/aio
SKILLS_DIR = AIO_DIR.parent                      # ~/.claude/skills
CORE = AIO_DIR / "SKILL.md"
KB = AIO_DIR / "references" / "knowledge-base.md"
AUDIT_TPL = AIO_DIR / "references" / "audit-report-template.md"
CHECKLIST = AIO_DIR / "references" / "readiness-checklist.md"
UPDATE = SKILLS_DIR / "aio-update" / "SKILL.md"

# Budgets — keep in sync with aio-update/SKILL.md "Size budgets".
CORE_MAX_LINES = 350
CORE_MAX_WORDS = 2500
KB_WARN_LINES = 500
KB_FAIL_LINES = 600
TRAIL_WARN_WORDS = 70                             # a Trail line getting long

# Claim ids that legitimately carry no **Evidence** (reference data, not citations).
EVIDENCE_EXEMPT = {"frameworks", "eval-tools", "guardrail-tools", "cost-strategies"}

# Provenance tokens that must NOT appear in the core rules tier.
PROVENANCE_PATTERNS = [
    (re.compile(r"\barxiv\b", re.I), "arxiv reference"),
    (re.compile(r"\b\d{4}\.\d{4,5}\b"), "arxiv-style id"),
    (re.compile(r"\bCVE-\d{4}-\d+\b"), "CVE id"),
    (re.compile(r"\bet al\b", re.I), "academic citation"),
    (re.compile(r"\bdoi\b", re.I), "DOI"),
    (re.compile(r"\bopenreview\b", re.I), "openreview citation"),
]

KB_REF = re.compile(r"\[KB:([a-z0-9-]+)\]")
KB_DEF = re.compile(r"^###\s+\[KB:([a-z0-9-]+)\]")
# arxiv id, digit-delimited only: tolerates a trailing version suffix (…14136v1 in
# registry URLs) while still rejecting substrings of longer numbers (…141368).
# A plain \b fails here because \b sees no boundary between a digit and the 'v'.
ARXIV_ID = re.compile(r"(?<!\d)\d{4}\.\d{4,5}(?!\d)")
FAILS: list[str] = []
WARNS: list[str] = []
PASSES: list[str] = []


def ok(msg): PASSES.append(msg)
def warn(msg): WARNS.append(msg)
def fail(msg): FAILS.append(msg)


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ---- 1. files present --------------------------------------------------------
def check_files():
    required = {"core SKILL.md": CORE, "knowledge-base.md": KB,
                "audit-report-template.md": AUDIT_TPL,
                "readiness-checklist.md": CHECKLIST}
    for label, p in required.items():
        if p.is_file():
            ok(f"file present: {label}")
        else:
            fail(f"missing file: {label} ({p})")
    # aio-update is a sibling maintenance skill, not part of the published aio
    # plugin (e.g. the mnox-ai marketplace ships aio alone). Validate it when
    # present; WARN-skip when absent so the suite stays portable.
    if UPDATE.is_file():
        ok("file present: aio-update SKILL.md")
    else:
        warn(f"aio-update SKILL.md absent ({UPDATE}) — sibling skill not in this context; skipping its checks")


# ---- 2. frontmatter ----------------------------------------------------------
def check_frontmatter():
    for p, expected_name in ((CORE, "aio"), (UPDATE, "aio-update")):
        if not p.is_file():
            continue
        text = read(p)
        if not text.startswith("---"):
            fail(f"{p.name}: no YAML frontmatter block")
            continue
        fm = text.split("---", 2)[1]
        name = re.search(r"^name:\s*(\S+)", fm, re.M)
        desc = re.search(r"^description:\s*\S", fm, re.M)
        if not name:
            fail(f"{p.name}: frontmatter missing name")
        elif name.group(1).strip().strip('"') != expected_name:
            fail(f"{p.name}: frontmatter name '{name.group(1)}' != '{expected_name}'")
        else:
            ok(f"{p.name}: frontmatter name == {expected_name}")
        if not desc:
            fail(f"{p.name}: frontmatter missing description")
        else:
            ok(f"{p.name}: frontmatter has description")


# ---- 3. size budgets ---------------------------------------------------------
def check_sizes():
    if CORE.is_file():
        text = read(CORE)
        lines = text.count("\n") + 1
        words = len(text.split())
        if lines <= CORE_MAX_LINES:
            ok(f"core SKILL.md lines {lines} <= {CORE_MAX_LINES}")
        else:
            fail(f"core SKILL.md lines {lines} > {CORE_MAX_LINES} — provenance likely mis-routed into the rules tier")
        if words <= CORE_MAX_WORDS:
            ok(f"core SKILL.md words {words} <= {CORE_MAX_WORDS}")
        else:
            fail(f"core SKILL.md words {words} > {CORE_MAX_WORDS}")
    if KB.is_file():
        lines = read(KB).count("\n") + 1
        if lines <= KB_WARN_LINES:
            ok(f"knowledge-base.md lines {lines} <= {KB_WARN_LINES}")
        elif lines <= KB_FAIL_LINES:
            warn(f"knowledge-base.md lines {lines} > {KB_WARN_LINES} soft cap — consolidate (merge near-duplicate claims, prune dead trails)")
        else:
            fail(f"knowledge-base.md lines {lines} > {KB_FAIL_LINES} hard cap")


# ---- 4. pointer integrity ----------------------------------------------------
def check_pointers():
    if not KB.is_file():
        return
    kb_lines = read(KB).splitlines()
    defs: dict[str, int] = {}
    dupes = []
    for i, line in enumerate(kb_lines, 1):
        m = KB_DEF.match(line)
        if m:
            cid = m.group(1)
            if cid in defs:
                dupes.append(cid)
            else:
                defs[cid] = i
    for cid in sorted(set(dupes)):
        fail(f"duplicate KB heading [KB:{cid}] — breaks /aio-update deterministic find-update")
    if not dupes:
        ok(f"no duplicate KB headings ({len(defs)} claims defined)")

    # collect references from core skill + all reference files (exclude the
    # illustrative 'claim-id' token used in prose/templates)
    referers = [CORE, KB, AUDIT_TPL, CHECKLIST]
    refs: dict[str, set[str]] = {}
    for p in referers:
        if not p.is_file():
            continue
        for cid in KB_REF.findall(read(p)):
            if cid == "claim-id":
                continue
            refs.setdefault(cid, set()).add(p.name)

    broken = sorted(c for c in refs if c not in defs)
    for cid in broken:
        fail(f"dangling pointer [KB:{cid}] (in {', '.join(sorted(refs[cid]))}) — no matching heading")
    if not broken:
        ok(f"all {len(refs)} referenced [KB:*] pointers resolve to a heading")

    # truly-dead claims: defined but referenced from nowhere at all
    orphans = sorted(c for c in defs if c not in refs)
    for cid in orphans:
        warn(f"orphan claim [KB:{cid}] — defined but referenced nowhere (core, KB cross-ref, or templates)")


# ---- 5. tier discipline ------------------------------------------------------
def check_tier_discipline():
    if not CORE.is_file():
        return
    violations = []
    for i, line in enumerate(read(CORE).splitlines(), 1):
        for pat, label in PROVENANCE_PATTERNS:
            if pat.search(line):
                violations.append((i, label, line.strip()[:80]))
    for i, label, snippet in violations:
        fail(f"core SKILL.md:{i} leaks provenance ({label}) into the rules tier: \"{snippet}\"")
    if not violations:
        ok("core SKILL.md carries no citations/arxiv/CVE/DOI — tier discipline holds")


# ---- 6 & 7. KB claim format + trail discipline -------------------------------
def check_kb_format():
    if not KB.is_file():
        return
    text = read(KB)
    # split into claim blocks on ### [KB:id] headings
    blocks = re.split(r"(?m)^###\s+\[KB:", text)
    missing_rule, long_trails = [], []
    for blk in blocks[1:]:
        cid = blk.split("]", 1)[0]
        body = blk
        if "**Rule:**" not in body:
            missing_rule.append(cid)
        if cid not in EVIDENCE_EXEMPT and "**Evidence:**" not in body:
            warn(f"[KB:{cid}] has no **Evidence:** line (only reference-table claims are exempt)")
        tm = re.search(r"\*\*Trail:\*\*(.*)", body)
        if tm and len(tm.group(1).split()) > TRAIL_WARN_WORDS:
            long_trails.append(cid)
    for cid in missing_rule:
        fail(f"[KB:{cid}] missing **Rule:** line")
    if not missing_rule:
        ok("every KB claim block has a **Rule:** line")
    for cid in long_trails:
        warn(f"[KB:{cid}] Trail is long (>{TRAIL_WARN_WORDS} words) — drop the oldest superseded source")


# ---- 8. aio-update path integrity --------------------------------------------
def check_update_paths():
    if not UPDATE.is_file():
        return
    text = read(UPDATE)
    # absolute paths and ~ paths appearing in inline-code spans
    for raw in set(re.findall(r"`(~?/[^`]+\.md)`", text)):
        p = Path(raw.replace("~", str(Path.home()), 1)) if raw.startswith("~") else Path(raw)
        if p.is_file():
            ok(f"aio-update path exists: {raw}")
        elif "dawks" in raw:
            warn(f"aio-update path missing (dawks — machine-specific?): {raw}")
        else:
            fail(f"aio-update path missing: {raw}")


# ---- 9. registry cross-check (WARN-only) -------------------------------------
def check_registry_crosscheck():
    if not KB.is_file():
        return
    registry = SKILLS_DIR.parent  # placeholder; resolve real dawks path from update skill
    reg_path = None
    if UPDATE.is_file():
        m = re.search(r"`(/[^`]*agentic-optimization-sources\.md)`", read(UPDATE))
        if m:
            reg_path = Path(m.group(1))
    if not reg_path or not reg_path.is_file():
        warn("registry cross-check skipped — sources registry not found (dawks not on this machine?)")
        return
    reg_ids = set(ARXIV_ID.findall(read(reg_path)))
    kb_ids = set(ARXIV_ID.findall(read(KB)))
    unlogged = sorted(kb_ids - reg_ids)
    if not unlogged:
        ok(f"all {len(kb_ids)} arxiv ids cited in KB are logged in the sources registry")
    else:
        warn(f"{len(unlogged)} arxiv id(s) cited in KB but NOT in the sources registry "
             f"(unverified or un-logged): {', '.join(unlogged[:12])}"
             + (" …" if len(unlogged) > 12 else ""))


def main():
    quiet = "--quiet" in sys.argv
    for chk in (check_files, check_frontmatter, check_sizes, check_pointers,
                check_tier_discipline, check_kb_format, check_update_paths,
                check_registry_crosscheck):
        chk()

    if not quiet:
        for m in PASSES:
            print(f"  \033[32mPASS\033[0m {m}")
    for m in WARNS:
        print(f"  \033[33mWARN\033[0m {m}")
    for m in FAILS:
        print(f"  \033[31mFAIL\033[0m {m}")

    print(f"\n  {len(PASSES)} passed · {len(WARNS)} warnings · {len(FAILS)} failures")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
