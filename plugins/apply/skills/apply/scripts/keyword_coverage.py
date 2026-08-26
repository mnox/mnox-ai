#!/usr/bin/env python3
"""Deterministic keyword-coverage check for a tailored resume.

The agent extracts a tiered keyword map from the job description (judgment);
this script verifies presence in the resume text (determinism) and reports
coverage per tier plus placement signals, so tailoring iterates against a
number instead of a feeling.

Input keyword map (JSON):
{
  "job_title": "Senior Software Engineer",
  "tiers": {
    "hard_skills":   [{"term": "Kubernetes", "variants": ["k8s"]}, ...],
    "title_seniority": [...],
    "certifications": [...],
    "soft_skills":  [...],
    "domain":       [...]
  }
}

Usage:
  python3 keyword_coverage.py --keywords keywords.json --resume resume.md
  python3 keyword_coverage.py --keywords keywords.json --resume resume.md --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Tier weights mirror how matching engines and recruiter searches weigh terms:
# hard skills dominate, title/seniority next, certs, then soft/domain color.
TIER_WEIGHTS = {
    "hard_skills": 50,
    "title_seniority": 20,
    "certifications": 15,
    "soft_skills": 10,
    "domain": 5,
}

TOP_THIRD_LABEL = "top third"


def _pattern(term: str) -> re.Pattern[str]:
    escaped = re.escape(term.strip())
    # Word-ish boundaries that tolerate punctuation around terms like "CI/CD",
    # "C++", or ".NET".
    return re.compile(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", re.IGNORECASE)


def find_term(text: str, term: str, variants: list[str]) -> dict:
    hits = []
    for candidate in [term, *variants]:
        if not candidate.strip():
            continue
        for match in _pattern(candidate).finditer(text):
            hits.append(match.start())
    hits.sort()
    top_third = bool(hits) and hits[0] <= len(text) // 3
    return {"count": len(hits), "first_pos": hits[0] if hits else None, "top_third": top_third}


def check(keywords: dict, resume_text: str) -> dict:
    tiers_out: dict[str, dict] = {}
    weighted_total = 0.0
    weighted_hit = 0.0
    for tier, weight in TIER_WEIGHTS.items():
        entries = keywords.get("tiers", {}).get(tier, [])
        rows = []
        for entry in entries:
            if isinstance(entry, str):
                entry = {"term": entry}
            term = entry["term"]
            variants = entry.get("variants", [])
            found = find_term(resume_text, term, variants)
            rows.append({"term": term, "variants": variants, **found})
        present = [r for r in rows if r["count"] > 0]
        coverage = (len(present) / len(rows)) if rows else None
        tiers_out[tier] = {
            "weight": weight,
            "total": len(rows),
            "present": len(present),
            "coverage": coverage,
            "missing": [r["term"] for r in rows if r["count"] == 0],
            "terms": rows,
        }
        if rows:
            weighted_total += weight
            weighted_hit += weight * coverage
    title = keywords.get("job_title", "")
    title_hit = find_term(resume_text, title, []) if title else {"count": 0, "top_third": False}
    score = round(100 * weighted_hit / weighted_total) if weighted_total else 0
    return {
        "score": score,
        "job_title": {"term": title, **title_hit},
        "tiers": tiers_out,
    }


def render(report: dict) -> str:
    lines = [f"Weighted keyword coverage: {report['score']}/100  (target: >=80 truthfully)"]
    title = report["job_title"]
    if title["term"]:
        status = "OK" if title["count"] else "MISSING"
        where = f" ({TOP_THIRD_LABEL})" if title.get("top_third") else ""
        lines.append(f"Job title '{title['term']}': {status}{where}")
    for tier, data in report["tiers"].items():
        if not data["total"]:
            continue
        pct = f"{round(100 * data['coverage'])}%"
        counts = f"{data['present']}/{data['total']}"
        lines.append(f"- {tier} (weight {data['weight']}): {counts} = {pct}")
        for row in data["terms"]:
            if row["count"]:
                extras = []
                if row["count"] == 1:
                    extras.append("only once — add a second in-context use if truthful")
                if row.get("top_third"):
                    extras.append(TOP_THIRD_LABEL)
                note = f"  ({'; '.join(extras)})" if extras else ""
                lines.append(f"    [x] {row['term']} x{row['count']}{note}")
        if data["missing"]:
            lines.append(f"    MISSING: {', '.join(data['missing'])}")
    lines.append(
        "Missing terms are GAPS to close only with true content (or accept the "
        "lower score) — never add a skill the profile doesn't support."
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keywords", required=True, type=Path)
    parser.add_argument("--resume", required=True, type=Path)
    parser.add_argument("--json", action="store_true", help="emit the full JSON report")
    args = parser.parse_args(argv)
    keywords = json.loads(args.keywords.read_text(encoding="utf-8"))
    resume_text = args.resume.read_text(encoding="utf-8")
    report = check(keywords, resume_text)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
