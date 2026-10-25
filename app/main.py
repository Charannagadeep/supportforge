"""SupportForge console API + static UI."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field

from . import agent, engine, llm
from .security import SecurityMiddleware, allowed_hosts, audit_security, authorize_user, require_api_key

STATIC = Path(__file__).parent / "static"

app = FastAPI(title="SupportForge", version="0.2.1")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts())
app.add_middleware(SecurityMiddleware)
configured_origins = [o.strip() for o in os.getenv("SUPPORTFORGE_CORS_ORIGINS", "").split(",") if o.strip()]
if configured_origins:
    app.add_middleware(CORSMiddleware, allow_origins=configured_origins, allow_methods=["GET", "POST"], allow_headers=["content-type", "x-api-key", "x-supportforge-user"])


@app.on_event("startup")
def _startup() -> None:
    engine.ensure_layout()
    engine.seed_all_demo_cases()


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
        "version": "0.2.1",
        "provider": provider,
        "model_online": provider.get("provider") not in ("none",) and provider.get("status") != "no_models",
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
    llm_report = engine.OUTBOX / f"{case_id}-llm-report.md"
    return {
        "id": case_id,
        "files": files,
        "audit": audit,
        "has_llm_report": llm_report.exists(),
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
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e
    path = engine.OUTBOX / f"{case_id}-llm-report.md"
    if not path.exists():
        raise HTTPException(404, "No LLM report yet — run Investigate")
    return PlainTextResponse(path.read_text())


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
