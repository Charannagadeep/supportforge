"""Offline + live evaluation harness for SupportForge.

Scores deterministic audits and optional LLM investigations against
golden cases under eval/goldens/. Designed for laptop-only judging —
no GB10 required.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from . import agent, engine

ROOT = Path(__file__).resolve().parents[1]
GOLDENS = ROOT / "eval" / "goldens"


@dataclass
class CaseScore:
    case_id: str
    title: str
    completeness: int
    completeness_ok: bool
    hypothesis_hits: int
    hypothesis_needed: int
    citation_hits: int
    citation_needed: int
    false_claim_hits: int
    security_flags: int
    mode: str
    latency_ms: int
    score: float
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return (
            self.completeness_ok
            and self.hypothesis_hits >= max(1, self.hypothesis_needed)
            and self.citation_hits >= max(1, self.citation_needed)
            and self.false_claim_hits == 0
        )


def list_goldens() -> list[dict[str, Any]]:
    out = []
    for p in sorted(GOLDENS.glob("CASE-*.json")):
        out.append(json.loads(p.read_text()))
    return out


def _load_golden(case_id: str) -> dict[str, Any]:
    path = GOLDENS / f"{case_id}.json"
    if not path.exists():
        raise FileNotFoundError(case_id)
    return json.loads(path.read_text())


def _term_groups_hit(text: str, groups: list[list[str]]) -> int:
    low = text.lower()
    hits = 0
    for group in groups:
        if any(term.lower() in low for term in group):
            hits += 1
    return hits


def _citation_hits(text: str, needles: list[str]) -> int:
    low = text.lower()
    return sum(1 for n in needles if n.lower() in low)


def _false_claims(text: str, banned: list[str]) -> int:
    low = text.lower()
    return sum(1 for b in banned if b.lower() in low)


def score_audit(case_id: str, use_complete: bool = True) -> CaseScore:
    golden = _load_golden(case_id)
    t0 = time.perf_counter()
    if use_complete:
        audit = engine.inject_complete_evidence(case_id)
    else:
        audit = engine.reset_demo_case(case_id) if (engine.DEMO_COMPLETE / case_id).exists() else engine.audit_case(case_id)
    # For cases without reset stub matching incomplete pack naming, ensure seed
    text = "\n".join(audit.get("hypotheses") or [])
    text += "\n" + json.dumps(audit.get("timeline") or [])
    handoff = ""
    try:
        handoff = engine.read_outbox_file(case_id, "handoff")
    except FileNotFoundError:
        pass
    blob = text + "\n" + handoff
    hyp_needed = len(golden.get("required_hypothesis_terms") or [])
    hyp_hits = _term_groups_hit(blob, golden.get("required_hypothesis_terms") or [])
    cit_needed = len(golden.get("required_citation_substrings") or [])
    cit_hits = _citation_hits(blob, golden.get("required_citation_substrings") or [])
    false_hits = _false_claims(blob, golden.get("must_not_claim") or [])
    pct = int(audit.get("completeness_percent") or 0)
    expected = int(golden.get("expected_completeness_complete") or 100) if use_complete else 0
    completeness_ok = pct >= expected if use_complete else pct < 100
    # Weighted score 0–100
    score = 0.0
    score += 30.0 if completeness_ok else max(0, pct * 0.3)
    score += 40.0 * (hyp_hits / max(1, hyp_needed))
    score += 25.0 * (cit_hits / max(1, cit_needed))
    score -= 15.0 * false_hits
    score = max(0.0, min(100.0, round(score, 1)))
    return CaseScore(
        case_id=case_id,
        title=golden.get("title", case_id),
        completeness=pct,
        completeness_ok=completeness_ok,
        hypothesis_hits=hyp_hits,
        hypothesis_needed=hyp_needed,
        citation_hits=cit_hits,
        citation_needed=cit_needed,
        false_claim_hits=false_hits,
        security_flags=len(audit.get("security_flags") or []),
        mode="rule",
        latency_ms=int((time.perf_counter() - t0) * 1000),
        score=score,
        detail={"family": golden.get("family"), "severity": golden.get("severity")},
    )


def score_investigate(case_id: str) -> CaseScore:
    golden = _load_golden(case_id)
    t0 = time.perf_counter()
    engine.inject_complete_evidence(case_id)
    result = agent.handle_message(f"Investigate {case_id}")
    reply = result.get("reply") or ""
    audit = result.get("audit") or {}
    blob = reply
    hyp_needed = len(golden.get("required_hypothesis_terms") or [])
    hyp_hits = _term_groups_hit(blob, golden.get("required_hypothesis_terms") or [])
    cit_needed = len(golden.get("required_citation_substrings") or [])
    cit_hits = _citation_hits(blob, golden.get("required_citation_substrings") or [])
    false_hits = _false_claims(blob, golden.get("must_not_claim") or [])
    pct = int(audit.get("completeness_percent") or 0)
    completeness_ok = pct >= int(golden.get("expected_completeness_complete") or 100)
    score = 0.0
    score += 25.0 if completeness_ok else 0.0
    score += 45.0 * (hyp_hits / max(1, hyp_needed))
    score += 25.0 * (cit_hits / max(1, cit_needed))
    score -= 20.0 * false_hits
    if result.get("model_meta"):
        score += 5.0  # live model actually ran
    score = max(0.0, min(100.0, round(score, 1)))
    return CaseScore(
        case_id=case_id,
        title=golden.get("title", case_id),
        completeness=pct,
        completeness_ok=completeness_ok,
        hypothesis_hits=hyp_hits,
        hypothesis_needed=hyp_needed,
        citation_hits=cit_hits,
        citation_needed=cit_needed,
        false_claim_hits=false_hits,
        security_flags=len(audit.get("security_flags") or []),
        mode="llm",
        latency_ms=int((time.perf_counter() - t0) * 1000),
        score=score,
        detail={
            "family": golden.get("family"),
            "model": (result.get("model_meta") or {}).get("model"),
            "provider": (result.get("model_meta") or {}).get("provider"),
        },
    )


def run_suite(mode: str = "rule", case_ids: list[str] | None = None) -> dict[str, Any]:
    ids = case_ids or [g["case_id"] for g in list_goldens()]
    scores: list[CaseScore] = []
    for cid in ids:
        if mode == "llm":
            scores.append(score_investigate(cid))
        else:
            scores.append(score_audit(cid, use_complete=True))
    passed = sum(1 for s in scores if s.passed)
    avg = round(sum(s.score for s in scores) / max(1, len(scores)), 1)
    results = []
    for s in scores:
        row = asdict(s)
        row["passed"] = s.passed
        results.append(row)
    payload = {
        "mode": mode,
        "cases": len(scores),
        "passed": passed,
        "pass_rate": round(100.0 * passed / max(1, len(scores)), 1),
        "avg_score": avg,
        "results": results,
    }
    out = engine.OUTBOX / f"eval-{mode}.json"
    out.write_text(json.dumps(payload, indent=2) + "\n")
    return payload
