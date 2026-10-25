"""Rule-layer eval suite — runs without LLM."""
from __future__ import annotations

from app import eval as evalkit


def test_rule_suite_pass_rate():
    payload = evalkit.run_suite(mode="rule")
    assert payload["cases"] == 5
    assert payload["pass_rate"] >= 80.0
    assert payload["avg_score"] >= 75.0
    for r in payload["results"]:
        assert r["completeness"] == 100
        assert r["false_claim_hits"] == 0


def test_goldens_present():
    goldens = evalkit.list_goldens()
    ids = {g["case_id"] for g in goldens}
    assert ids == {"CASE-1042", "CASE-1088", "CASE-1101", "CASE-1120", "CASE-1155"}
