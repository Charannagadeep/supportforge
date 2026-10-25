"""SupportForge agent — deterministic evidence + live LLM investigation."""
from __future__ import annotations

import os
import re
from typing import Any

from . import engine, llm
from .security import allowed_case_path, allowed_output_path, audit_security, redact_secrets

ALLOWED_ACTIONS = {
    "read_case",
    "audit_case",
    "investigate_case",
    "save_handoff",
    "list_cases",
    "reset_demo",
    "inject_demo_evidence",
}
FORBIDDEN_ACTION_RE = re.compile(
    r"\b(?:shell|subprocess|kill\s+process|terminate\s+process|driver\s+change)\b|"
    r"\b(?:gpu\s+reset|reset\s+(?:the\s+)?gpu)\b|"
    r"\bexec(?:ute)?\s+(?:a\s+)?(?:shell|command|bash|zsh)\b|"
    r"send\s+\S+\s+email|read\s+\S*\s*private",
    re.I,
)


def _case_from_text(text: str, default: str | None = "CASE-1042") -> str | None:
    m = re.search(r"CASE-\d+", text, re.I)
    if m:
        return m.group(0).upper()
    cases = [c["id"] for c in engine.list_cases()]
    if default and default in cases:
        return default
    return cases[0] if cases else None


def handle_message(message: str, actor: str = "console-local") -> dict[str, Any]:
    """Interpret a user message and run local tools + optional local LLM."""
    engine.ensure_layout()
    text = (message or "").strip()
    low = text.lower()
    case_id = _case_from_text(text)
    provider = llm.detect_provider()

    if FORBIDDEN_ACTION_RE.search(text):
        audit_security("agent_tool", actor=actor, result="denied", tool="arbitrary_or_destructive_action")
        return {
            "reply": "Denied: SupportForge only reads approved case/runbook folders and writes audit/handoff state. Shell commands, GPU resets, process termination, driver changes, and external messaging are unavailable.",
            "audit": None,
            "case_id": case_id,
        }

    # Demo choreography
    if any(k in low for k in ("reset demo", "reset case", "start over", "incomplete")):
        audit_security("agent_tool", actor=actor, tool="reset_demo")
        audit = engine.reset_demo_case("CASE-1042")
        return _pack(
            "Reset **CASE-1042** to the incomplete pack (serving log only).\n"
            f"Completeness **{audit['completeness_percent']}%**.\n"
            "Missing: "
            + ", ".join(
                r["item"] for r in audit["evidence"] if r["required"] and r["status"] != "present"
            )
            + ".\n\nNext: **audit CASE-1042** or **investigate CASE-1042** (LLM).",
            audit,
            "CASE-1042",
            provider,
        )

    if any(k in low for k in ("inject", "add missing", "complete evidence", "new evidence")):
        audit_security("agent_tool", actor=actor, tool="inject_demo_evidence")
        cid = case_id or "CASE-1042"
        audit = engine.inject_complete_evidence(cid)
        reply = (
            f"Injected missing evidence into **{cid}**. Completeness **{audit['completeness_percent']}%**.\n\n"
            + _hyp_block(audit)
        )
        # Auto-run LLM on complete pack when model is up
        if provider.get("provider") not in ("none",):
            try:
                inv = _investigate(cid, audit)
                reply = inv["reply"]
                return _pack(reply, audit, cid, provider, model_meta=inv.get("model_meta"))
            except Exception as e:  # noqa: BLE001
                reply += f"\n\n_(LLM investigate deferred: {e})_"
        return _pack(
            reply + "\n\nOpen the **Handoff** tab for the engineering package.",
            audit,
            cid,
            provider,
        )

    if any(k in low for k in ("investigate", "reason", "deep dive", "explain", "summarize")):
        if not case_id:
            return {
                "reply": "Which case? Try: `Investigate CASE-1042`",
                "audit": None,
                "case_id": None,
                "provider": provider,
            }
        audit_security("agent_tool", actor=actor, tool="investigate_case", case_id=case_id)
        audit = engine.audit_case(case_id)
        try:
            inv = _investigate(case_id, audit)
            return _pack(inv["reply"], audit, case_id, provider, model_meta=inv.get("model_meta"))
        except Exception as e:  # noqa: BLE001
            return _pack(
                f"**{case_id}** audited (**{audit['completeness_percent']}%**), but LLM failed:\n`{e}`\n\n"
                + _hyp_block(audit)
                + "\n\nStart Ollama and ensure a model is pulled, then retry **investigate**.",
                audit,
                case_id,
                provider,
            )

    if any(k in low for k in ("audit", "triage", "handoff", "prepare", "analyze")):
        if not case_id:
            return {
                "reply": "Which case? Try: `Audit CASE-1042 and prepare the engineering handoff.`",
                "audit": None,
                "case_id": None,
                "provider": provider,
            }
        audit_security("agent_tool", actor=actor, tool="audit_case", case_id=case_id)
        audit = engine.audit_case(case_id)
        missing = [
            r["item"] for r in audit["evidence"] if r["required"] and r["status"] != "present"
        ]
        # Prefer LLM narrative when complete or when user asked for handoff
        want_llm = "handoff" in low or "prepare" in low or not missing
        if want_llm and provider.get("provider") not in ("none",):
            try:
                inv = _investigate(case_id, audit)
                return _pack(inv["reply"], audit, case_id, provider, model_meta=inv.get("model_meta"))
            except Exception:
                pass
        if missing:
            body = (
                f"**{case_id}** audited locally.\n"
                f"- Completeness: **{audit['completeness_percent']}%**\n"
                f"- Blocking gaps: {', '.join(missing)}\n"
                f"- Wrote `workspace/outbox/{case_id}-requests.md` and partial handoff.\n\n"
                "Next: **inject missing evidence**, or **investigate CASE-1042** once complete."
            )
        else:
            body = (
                f"**{case_id}** is complete (**{audit['completeness_percent']}%**).\n\n"
                + _hyp_block(audit)
                + f"\nHandoff ready at `workspace/outbox/{case_id}-handoff.md`.\n"
                "Say **investigate CASE-1042** for live model reasoning."
            )
        return _pack(body, audit, case_id, provider)

    if "list" in low and "case" in low:
        audit_security("agent_tool", actor=actor, tool="list_cases")
        cases = engine.list_cases()
        lines = [
            f"- **{c['id']}** — {c['completeness'] if c['completeness'] is not None else '?'}% · {c['files']} files"
            for c in cases
        ]
        return {
            "reply": "Cases on this laptop:\n" + "\n".join(lines),
            "audit": None,
            "case_id": None,
            "provider": provider,
        }

    if any(k in low for k in ("model", "provider", "which llm", "status")):
        return {
            "reply": _provider_status(provider),
            "audit": None,
            "case_id": case_id,
            "provider": provider,
        }

    if any(k in low for k in ("help", "what can you", "how do")):
        return {
            "reply": (
                "I'm **SupportForge** — local evidence audit + live LLM investigation.\n\n"
                "Demo arc:\n"
                "1. `Reset demo`\n"
                "2. `Audit CASE-1042` → gaps\n"
                "3. `Inject missing evidence`\n"
                "4. `Investigate CASE-1042` → model writes the handoff narrative\n\n"
                f"{_provider_status(provider)}\n"
                "Private case files stay on this machine."
            ),
            "audit": None,
            "case_id": None,
            "provider": provider,
        }

    # Default: treat as investigate if case mentioned, else help
    if case_id and len(text) > 8:
        audit = engine.audit_case(case_id)
        if provider.get("provider") not in ("none",):
            try:
                inv = _investigate(case_id, audit, extra_user=redact_secrets(text))
                return _pack(inv["reply"], audit, case_id, provider, model_meta=inv.get("model_meta"))
            except Exception as e:  # noqa: BLE001
                return _pack(
                    f"Audit done; LLM error: `{e}`\n\n" + _hyp_block(audit),
                    audit,
                    case_id,
                    provider,
                )

    if os.environ.get("ANTHROPIC_API_KEY") and any(k in low for k in ("explain", "summarize in prose")):
        audit_security("external_assist", actor=actor, result="denied", reason="disabled_by_default")
    return {
        "reply": (
            "Try:\n"
            "- `Reset demo`\n"
            "- `Audit CASE-1042`\n"
            "- `Inject missing evidence`\n"
            "- `Investigate CASE-1042`\n"
            "- `Model status`"
        ),
        "audit": None,
        "case_id": case_id,
        "provider": provider,
    }


def _file_snippets(case_id: str, audit: dict[str, Any], limit_per: int = 3500) -> dict[str, str]:
    out: dict[str, str] = {}
    paths: list[str] = []
    for row in audit.get("evidence") or []:
        paths.extend(row.get("paths") or [])
    for extra in ("customer/description.md", "customer/steps-tried.md"):
        if extra not in paths:
            try:
                if allowed_case_path(case_id, extra).is_file():
                    paths.append(extra)
            except ValueError:
                continue
    for rel in paths[:12]:
        try:
            p = allowed_case_path(case_id, rel)
        except ValueError:
            audit_security("file_access", result="denied", path=rel, case_id=case_id)
            continue
        if p.is_file():
            out[rel] = redact_secrets(p.read_text(errors="replace")[:limit_per])
    return out


def _investigate(
    case_id: str, audit: dict[str, Any], extra_user: str | None = None
) -> dict[str, Any]:
    snippets = _file_snippets(case_id, audit)
    result = llm.investigate_case(case_id, audit, snippets)
    path = allowed_output_path(case_id, "llm-report.md")
    header = (
        f"# LLM investigation — {case_id}\n\n"
        f"**Provider:** `{result.provider}` · **Model:** `{result.model}`\n\n"
        f"_Evidence completeness: {audit.get('completeness_percent')}%_\n\n---\n\n"
    )
    if extra_user:
        header += f"_User ask:_ {redact_secrets(extra_user)}\n\n"
    path.write_text(header + result.text + "\n")
    audit_security("agent_tool", tool="save_handoff", case_id=case_id, artifact="llm-report.md")
    handoff = allowed_output_path(case_id, "handoff.md")
    if handoff.exists() and audit.get("completeness_percent", 0) >= 80:
        existing = handoff.read_text()
        marker = "## Live model investigation"
        block = (
            f"\n{marker}\n\n"
            f"_Generated by `{result.provider}` / `{result.model}`_\n\n"
            f"{result.text}\n"
        )
        if marker in existing:
            existing = existing.split(marker)[0].rstrip() + "\n" + block
        else:
            existing = existing.rstrip() + "\n" + block
        handoff.write_text(existing)
    meta = {"provider": result.provider, "model": result.model, "report_path": str(path)}
    reply = (
        f"**Live investigation · {result.provider} / {result.model}**\n"
        f"Completeness **{audit.get('completeness_percent')}%**\n\n"
        f"{result.text}"
    )
    return {"reply": reply, "model_meta": meta}


def _provider_status(provider: dict[str, str]) -> str:
    p = provider.get("provider", "none")
    if p == "none":
        return "Model: **offline** — start Ollama (`open -a Ollama`) and pull `qwen2.5:7b-instruct`."
    status = provider.get("status")
    if status == "no_models":
        return f"Ollama up, but **no models** pulled yet. Pulling `qwen2.5:7b-instruct`…"
    return f"Model online: **{p}** · `{provider.get('model')}`"


def _hyp_block(audit: dict[str, Any]) -> str:
    hyps = audit.get("hypotheses") or []
    if not hyps:
        return ""
    return "**Rule hypotheses**\n" + "\n".join(f"{i}. {h}" for i, h in enumerate(hyps, 1))


def _pack(
    reply: str,
    audit: dict[str, Any],
    case_id: str,
    provider: dict[str, str] | None = None,
    model_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "reply": reply,
        "audit": audit,
        "case_id": case_id,
        "provider": provider or llm.detect_provider(),
        "model_meta": model_meta,
    }
