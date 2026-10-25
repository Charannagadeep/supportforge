"""Laptop-local SupportForge agent (no GB10 / no cloud required)."""
from __future__ import annotations

import os
import re
from typing import Any

from . import engine


def _case_from_text(text: str, default: str | None = "CASE-1042") -> str | None:
    m = re.search(r"CASE-\d+", text, re.I)
    if m:
        return m.group(0).upper()
    cases = [c["id"] for c in engine.list_cases()]
    if default and default in cases:
        return default
    return cases[0] if cases else None


def handle_message(message: str) -> dict[str, Any]:
    """Interpret a user message and run local tools."""
    engine.ensure_layout()
    text = (message or "").strip()
    low = text.lower()
    case_id = _case_from_text(text)

    # Demo choreography
    if any(k in low for k in ("reset demo", "reset case", "start over", "incomplete")):
        audit = engine.reset_demo_case("CASE-1042")
        return _pack(
            "Reset CASE-1042 to the incomplete pack (serving log only). "
            f"Completeness is **{audit['completeness_percent']}%**. "
            "Missing: "
            + ", ".join(
                r["item"] for r in audit["evidence"] if r["required"] and r["status"] != "present"
            )
            + ". Say **audit CASE-1042** or click Run evidence audit.",
            audit,
            "CASE-1042",
        )

    if any(k in low for k in ("inject", "add missing", "complete evidence", "new evidence")):
        cid = case_id or "CASE-1042"
        audit = engine.inject_complete_evidence(cid)
        return _pack(
            f"Injected missing evidence into **{cid}**. Completeness **{audit['completeness_percent']}%**.\n\n"
            + _hyp_block(audit)
            + "\nOpen the **Handoff** tab for the full engineering package.",
            audit,
            cid,
        )

    if any(k in low for k in ("audit", "triage", "handoff", "investigate", "prepare", "analyze")):
        if not case_id:
            return {
                "reply": "Which case? Try: `Audit CASE-1042 and prepare the engineering handoff.`",
                "audit": None,
                "case_id": None,
            }
        audit = engine.audit_case(case_id)
        missing = [
            r["item"] for r in audit["evidence"] if r["required"] and r["status"] != "present"
        ]
        if missing:
            body = (
                f"**{case_id}** audited locally.\n"
                f"- Completeness: **{audit['completeness_percent']}%**\n"
                f"- Blocking gaps: {', '.join(missing)}\n"
                f"- Wrote `workspace/outbox/{case_id}-requests.md` and partial handoff.\n\n"
                "Next: provide the missing files, or say **inject missing evidence** for the demo pack."
            )
        else:
            body = (
                f"**{case_id}** is complete (**{audit['completeness_percent']}%**).\n\n"
                + _hyp_block(audit)
                + f"\nHandoff ready at `workspace/outbox/{case_id}-handoff.md`."
            )
        return _pack(body, audit, case_id)

    if "list" in low and "case" in low:
        cases = engine.list_cases()
        lines = [
            f"- **{c['id']}** — {c['completeness'] if c['completeness'] is not None else '?'}% · {c['files']} files"
            for c in cases
        ]
        return {
            "reply": "Cases on this laptop:\n" + "\n".join(lines),
            "audit": None,
            "case_id": None,
        }

    if any(k in low for k in ("help", "what can you", "how do")):
        return {
            "reply": (
                "I'm SupportForge running **fully on your laptop** (no GB10 needed for this demo).\n\n"
                "Try:\n"
                "1. `Reset demo`\n"
                "2. `Audit CASE-1042 and prepare the engineering handoff`\n"
                "3. `Inject missing evidence`\n"
                "4. `List cases`\n\n"
                "Private case files never leave this machine."
            ),
            "audit": None,
            "case_id": None,
        }

    # Optional: light cloud assist only if key present AND user asks to "explain"
    if os.environ.get("ANTHROPIC_API_KEY") and any(k in low for k in ("explain", "summarize in prose")):
        try:
            return _claude_wrap(text, case_id)
        except Exception as e:  # noqa: BLE001
            return {
                "reply": f"Local tools only (Claude helper failed: {e}). Try `audit CASE-1042`.",
                "audit": None,
                "case_id": case_id,
            }

    return {
        "reply": (
            "I didn't catch that. On laptop mode, use:\n"
            "- `Reset demo`\n"
            "- `Audit CASE-1042 and prepare the engineering handoff`\n"
            "- `Inject missing evidence`"
        ),
        "audit": None,
        "case_id": case_id,
    }


def _hyp_block(audit: dict[str, Any]) -> str:
    hyps = audit.get("hypotheses") or []
    if not hyps:
        return ""
    return "**Hypotheses**\n" + "\n".join(f"{i}. {h}" for i, h in enumerate(hyps, 1))


def _pack(reply: str, audit: dict[str, Any], case_id: str) -> dict[str, Any]:
    return {"reply": reply, "audit": audit, "case_id": case_id}


def _claude_wrap(text: str, case_id: str | None) -> dict[str, Any]:
    """Optional prose layer — evidence still comes from local engine."""
    import json
    import urllib.request

    audit = engine.audit_case(case_id) if case_id else None
    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 400,
        "messages": [
            {
                "role": "user",
                "content": (
                    "You are SupportForge. Explain this local audit briefly for engineers. "
                    "Do not invent evidence.\n\n"
                    f"User asked: {text}\n\nAudit JSON:\n{json.dumps(audit, indent=2)[:6000]}"
                ),
            }
        ],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode(),
        headers={
            "content-type": "application/json",
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    reply = data["content"][0]["text"]
    return {"reply": reply, "audit": audit, "case_id": case_id}
