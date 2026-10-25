"""Live LLM eval — skipped automatically if Ollama is offline."""
from __future__ import annotations

import pytest

from app import eval as evalkit
from app import llm


@pytest.mark.live
def test_live_llm_suite():
    provider = llm.detect_provider()
    if provider.get("provider") in ("none",) or provider.get("status") == "no_models":
        pytest.skip("Ollama model not online")
    # Smoke one high-signal case for CI speed; full suite via scripts/run-eval.sh
    score = evalkit.score_investigate("CASE-1042")
    assert score.completeness == 100
    assert score.hypothesis_hits >= 1
    assert score.score >= 50.0
