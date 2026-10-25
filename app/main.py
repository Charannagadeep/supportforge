"""SupportForge console API + static UI."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dataclasses import asdict

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field

from . import agent, corpus, engine, eval as evalkit, llm, watcher
from .security import (
    SecurityMiddleware,
    allowed_hosts,
    allowed_output_path,
    audit_security,
    authorize_user,
    require_api_key,
)

STATIC = Path(__file__).parent / "static"

app = FastAPI(title="SupportForge", version="0.3.0")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts())
app.add_middleware(SecurityMiddleware)
configured_origins = [o.strip() for o in os.getenv("SUPPORTFORGE_CORS_ORIGINS", "").split(",") if o.strip()]
if configured_origins:
    app.add_middleware(CORSMiddleware, allow_origins=configured_origins, allow_methods=["GET", "POST"], allow_headers=["content-type", "x-api-key", "x-supportforge-user"])


@app.on_event("startup")
def _startup() -> None:
    engine.ensure_layout()
    # Ensure newly added case packs appear in the live workspace.
    import shutil

    for cid in ("CASE-1101", "CASE-1120", "CASE-1155", "CASE-2163", "CASE-2161"):
        dest = engine.CASES_DIR / cid
        src = engine.DEMO_COMPLETE / cid
        if src.is_dir() and not dest.exists():
            shutil.copytree(src, dest)
            engine.audit_case(cid)
    engine.seed_all_demo_cases()
    # Always-on agent: auto re-audit + refresh handoffs when case evidence
    # changes. Opt-in via SUPPORTFORGE_WATCH=1 so tests stay deterministic.
    watcher.start_background()


@app.on_event("shutdown")
def _shutdown() -> None:
    watcher.stop_background()


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=8000)


@app.get("/api/health")
def health() -> dict[str, Any]:
    provider = llm.detect_provider()
    return {
        "ok": True,
        "service": "supportforge",
        "local": True,
        "mode": "laptop",
        "runtime": "macos-local",
        "version": "0.3.0",
        "provider": provider,
        "model_online": provider.get("provider") not in ("none",) and provider.get("status") != "no_models",
        "cases": len(engine.list_cases()),
        "goldens": len(evalkit.list_goldens()),
        "corpus_issues": corpus.stats().get("issues", 0),
        "corpus_incomplete_rate": corpus.stats().get("incomplete_rate_pct"),
        "security": {
            "api_key_required": bool(os.getenv("SUPPORTFORGE_API_KEY", "").strip()),
            "bind_default": "127.0.0.1",
            "external_assist": os.getenv("SUPPORTFORGE_ALLOW_EXTERNAL_ASSIST") == "1",
        },
    }


@app.get("/api/provider", dependencies=[Depends(require_api_key)])
def provider() -> dict[str, Any]:
    return llm.detect_provider()


@app.post("/api/chat", dependencies=[Depends(require_api_key)])
def chat(body: ChatIn, x_supportforge_user: str | None = Header(default=None)) -> dict[str, Any]:
    actor = authorize_user(x_supportforge_user)
    audit_security("chat_command", actor=actor, command=body.message[:80])
    return agent.handle_message(body.message, actor=actor)


@app.get("/api/cases", dependencies=[Depends(require_api_key)])
def cases() -> list[dict[str, Any]]:
    return engine.list_cases()


@app.get("/api/cases/{case_id}", dependencies=[Depends(require_api_key)])
def case_detail(case_id: str) -> dict[str, Any]:
    try:
        case_id = engine.validate_case_id(case_id)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e
    case = engine.CASES_DIR / case_id
    if not case.is_dir():
        raise HTTPException(404, "case not found")
    audit_path = case / "audit.json"
    audit = json.loads(audit_path.read_text()) if audit_path.exists() else None
    files = sorted(
        str(p.relative_to(case)) for p in case.rglob("*") if p.is_file() and p.name != "audit.json"
    )
    try:
        has_llm = allowed_output_path(case_id, "llm-report.md").exists()
    except ValueError:
        has_llm = False
    return {
        "id": case_id,
        "files": files,
        "audit": audit,
        "has_llm_report": has_llm,
    }


@app.post("/api/cases/{case_id}/audit", dependencies=[Depends(require_api_key)])
def run_audit(case_id: str) -> dict[str, Any]:
    try:
        return engine.audit_case(case_id)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e


@app.post("/api/cases/{case_id}/investigate", dependencies=[Depends(require_api_key)])
def investigate(case_id: str) -> dict[str, Any]:
    """Run evidence audit + live LLM investigation."""
    try:
        return agent.handle_message(f"Investigate {case_id}")
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e


@app.post("/api/demo/reset", dependencies=[Depends(require_api_key)])
def demo_reset(case_id: str = "CASE-1042") -> dict[str, Any]:
    try:
        return engine.reset_demo_case(case_id)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e


@app.post("/api/demo/inject-complete", dependencies=[Depends(require_api_key)])
def demo_inject(case_id: str = "CASE-1042") -> dict[str, Any]:
    try:
        return engine.inject_complete_evidence(case_id)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e


@app.get("/api/cases/{case_id}/handoff", dependencies=[Depends(require_api_key)])
def handoff(case_id: str) -> PlainTextResponse:
    try:
        return PlainTextResponse(engine.read_outbox_file(case_id, "handoff"))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e


@app.get("/api/cases/{case_id}/requests", dependencies=[Depends(require_api_key)])
def requests_md(case_id: str) -> PlainTextResponse:
    try:
        return PlainTextResponse(engine.read_outbox_file(case_id, "requests"))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e


@app.get("/api/cases/{case_id}/llm-report", dependencies=[Depends(require_api_key)])
def llm_report(case_id: str) -> PlainTextResponse:
    try:
        case_id = engine.validate_case_id(case_id)
        path = allowed_output_path(case_id, "llm-report.md")
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(404, str(e)) from e
    if not path.exists():
        raise HTTPException(404, "No LLM report yet — run Investigate")
    return PlainTextResponse(path.read_text())


class EvalIn(BaseModel):
    mode: str = Field(default="rule", pattern="^(rule|llm)$")
    case_ids: list[str] | None = None


@app.get("/api/eval/goldens", dependencies=[Depends(require_api_key)])
def eval_goldens() -> list[dict[str, Any]]:
    return evalkit.list_goldens()


@app.post("/api/eval/run", dependencies=[Depends(require_api_key)])
def eval_run(body: EvalIn) -> dict[str, Any]:
    audit_security("eval_suite", mode=body.mode, cases=len(body.case_ids or []))
    try:
        return evalkit.run_suite(mode=body.mode, case_ids=body.case_ids)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, str(e)) from e


@app.post("/api/eval/case/{case_id}", dependencies=[Depends(require_api_key)])
def eval_one(case_id: str, mode: str = "rule") -> dict[str, Any]:
    try:
        case_id = engine.validate_case_id(case_id)
        if mode == "llm":
            score = evalkit.score_investigate(case_id)
        else:
            score = evalkit.score_audit(case_id, use_complete=True)
        row = asdict(score)
        row["passed"] = score.passed
        return row
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e


@app.get("/api/corpus/stats", dependencies=[Depends(require_api_key)])
def corpus_stats() -> dict[str, Any]:
    return corpus.stats()


@app.get("/api/corpus/issues", dependencies=[Depends(require_api_key)])
def corpus_issues(q: str = "", incomplete_only: bool = True, limit: int = 40) -> list[dict[str, Any]]:
    return corpus.list_issues(q=q, incomplete_only=incomplete_only, limit=limit)


@app.get("/api/corpus/issues/{issue_number}", dependencies=[Depends(require_api_key)])
def corpus_issue(issue_number: str) -> dict[str, Any]:
    item = corpus.get_issue(issue_number)
    if not item:
        raise HTTPException(404, "issue not found in corpus")
    return item


@app.get("/api/watch", dependencies=[Depends(require_api_key)])
def watch_status() -> dict[str, Any]:
    """Always-on agent status: whether the watcher runs and per-case state."""
    state = watcher._load_state()  # read-only snapshot
    log_tail = ""
    if watcher.WATCH_LOG.exists():
        lines = watcher.WATCH_LOG.read_text(errors="replace").splitlines()
        log_tail = "\n".join(lines[-40:])
    return {
        "enabled": bool(watcher._THREAD and watcher._THREAD.is_alive()),
        "interval_seconds": float(os.getenv("SUPPORTFORGE_WATCH_INTERVAL", "3")),
        "last_scan": state.get("updated"),
        "cases": state.get("cases", {}),
        "watch_log_tail": log_tail,
    }


@app.get("/", response_class=HTMLResponse)
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


if STATIC.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


def run() -> None:
    import uvicorn

    host = os.getenv("SUPPORTFORGE_HOST", "127.0.0.1")
    port = int(os.getenv("SUPPORTFORGE_PORT", "8787"))
    uvicorn.run("app.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run()
