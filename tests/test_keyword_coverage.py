"""Tests for plugins/apply/skills/apply/scripts/keyword_coverage.py."""

from __future__ import annotations

import unittest

from tests._loader import load_script

kc = load_script("keyword_coverage")

RESUME = """\
Jane Doe — Senior Software Engineer
jane@example.com

Summary
Senior Software Engineer specializing in Kubernetes platforms and CI/CD.

Experience
Acme — Senior Software Engineer, Jan 2020 – Present
- Cut p99 latency 40% by migrating ingest to Kafka on Kubernetes (k8s).
- Built continuous integration pipelines serving 200+ services.

Skills
Kubernetes, Kafka, Python
"""

KEYWORDS = {
    "job_title": "Senior Software Engineer",
    "tiers": {
        "hard_skills": [
            {"term": "Kubernetes", "variants": ["k8s"]},
            {"term": "CI/CD", "variants": ["continuous integration"]},
            {"term": "Terraform"},
        ],
        "title_seniority": [{"term": "Senior Software Engineer"}],
        "soft_skills": ["stakeholder management"],
    },
}


class FindTermTest(unittest.TestCase):
    def test_counts_variants_and_case_insensitive(self) -> None:
        found = kc.find_term(RESUME, "Kubernetes", ["k8s"])
        self.assertEqual(found["count"], 4)  # Summary, bullet, "(k8s)", Skills
        self.assertTrue(found["top_third"])

    def test_boundary_prevents_substring_hits(self) -> None:
        self.assertEqual(kc.find_term("javascript", "java", [])["count"], 0)

    def test_punctuated_terms_match(self) -> None:
        self.assertEqual(kc.find_term("built CI/CD flows", "CI/CD", [])["count"], 1)

    def test_missing_term(self) -> None:
        found = kc.find_term(RESUME, "Terraform", [])
        self.assertEqual(found, {"count": 0, "first_pos": None, "top_third": False})


class CheckTest(unittest.TestCase):
    def test_report_shape_and_score(self) -> None:
        report = kc.check(KEYWORDS, RESUME)
        hard = report["tiers"]["hard_skills"]
        self.assertEqual(hard["present"], 2)
        self.assertEqual(hard["missing"], ["Terraform"])
        self.assertEqual(report["tiers"]["title_seniority"]["coverage"], 1.0)
        self.assertEqual(report["tiers"]["soft_skills"]["missing"], ["stakeholder management"])
        # weights: hard 50 * 2/3 + title 20 * 1 + soft 10 * 0 over 80 total
        self.assertEqual(report["score"], round(100 * (50 * (2 / 3) + 20) / 80))
        self.assertGreater(report["job_title"]["count"], 0)

    def test_empty_tiers_are_skipped_not_zeroed(self) -> None:
        report = kc.check({"job_title": "", "tiers": {"hard_skills": [{"term": "Kafka"}]}}, RESUME)
        self.assertEqual(report["score"], 100)

    def test_render_mentions_missing_and_target(self) -> None:
        text = kc.render(kc.check(KEYWORDS, RESUME))
        self.assertIn("MISSING: Terraform", text)
        self.assertIn(">=80", text)
        self.assertIn("never add a skill", text)


if __name__ == "__main__":
    unittest.main()
