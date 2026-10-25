"""SupportForge console API + static UI."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import agent, engine, llm

STATIC = Path(__file__).parent / "static"

app = FastAPI(title="SupportForge", version="0.2.0")


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
        "version": "0.2.0",
        "provider": provider,
        "model_online": provider.get("provider") not in ("none",) and provider.get("status") != "no_models",
    }


@app.get("/api/provider")
def provider() -> dict[str, Any]:
    return llm.detect_provider()


@app.post("/api/chat")
def chat(body: ChatIn) -> dict[str, Any]:
    return agent.handle_message(body.message)


@app.get("/api/cases")
def cases() -> list[dict[str, Any]]:
    return engine.list_cases()


@app.get("/api/cases/{case_id}")
def case_detail(case_id: str) -> dict[str, Any]:
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


@app.post("/api/cases/{case_id}/audit")
def run_audit(case_id: str) -> dict[str, Any]:
    try:
        return engine.audit_case(case_id)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e


@app.post("/api/cases/{case_id}/investigate")
def investigate(case_id: str) -> dict[str, Any]:
    """Run evidence audit + live LLM investigation."""
    try:
        return agent.handle_message(f"Investigate {case_id}")
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e


@app.post("/api/demo/reset")
def demo_reset(case_id: str = "CASE-1042") -> dict[str, Any]:
    try:
        return engine.reset_demo_case(case_id)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e


@app.post("/api/demo/inject-complete")
def demo_inject(case_id: str = "CASE-1042") -> dict[str, Any]:
    try:
        return engine.inject_complete_evidence(case_id)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e


@app.get("/api/cases/{case_id}/handoff")
def handoff(case_id: str) -> PlainTextResponse:
    try:
        return PlainTextResponse(engine.read_outbox_file(case_id, "handoff"))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e


@app.get("/api/cases/{case_id}/requests")
def requests_md(case_id: str) -> PlainTextResponse:
    try:
        return PlainTextResponse(engine.read_outbox_file(case_id, "requests"))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e


@app.get("/api/cases/{case_id}/llm-report")
def llm_report(case_id: str) -> PlainTextResponse:
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

    uvicorn.run("app.main:app", host="0.0.0.0", port=8787, reload=False)


if __name__ == "__main__":
    run()
