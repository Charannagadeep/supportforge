"""Small, dependency-free security boundary for the SupportForge API.

The console is local-first, so authentication is opt-in for local development
and can be enabled for a GB10 or other shared deployment with an API key.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from ipaddress import ip_address
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import Header, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "workspace"
AUDIT_LOG = WORKSPACE / "memory" / "security-audit.jsonl"
CASE_ID_RE = re.compile(r"^CASE-[0-9]+$")
SUSPICIOUS_INSTRUCTION_RE = re.compile(
    r"ignore (?:all|any|previous|the) instructions|read (?:a )?(?:private|secret)|send .* to|exfiltrat|run (?:a )?shell|execute .*command",
    re.I,
)
SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|token|secret|password|authorization|private[_-]?key)\s*[:=]\s*([^\s,;]+)"
)


def _csv(name: str, default: str) -> list[str]:
    return [v.strip() for v in os.getenv(name, default).split(",") if v.strip()]


def audit_security(action: str, *, actor: str = "system", result: str = "allowed", **details: Any) -> None:
    """Write metadata only; never put evidence contents or secrets in the log."""
    WORKSPACE.joinpath("memory").mkdir(parents=True, exist_ok=True)
    record = {
        "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "action": action,
        "actor": actor[:120],
        "result": result,
        **{k: str(v)[:300] for k, v in details.items() if k not in {"content", "secret", "body"}},
    }
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


def redact_secrets(text: str) -> str:
    """Remove common credential-shaped values before model/channel processing."""
    return SECRET_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)


def find_prompt_injection_markers(text: str) -> list[str]:
    """Detect instruction-like evidence; callers must report, never follow it."""
    return ["instruction-like content detected in evidence"] if SUSPICIOUS_INSTRUCTION_RE.search(text) else []


def authorize_user(user: str | None) -> str:
    allowed = _csv("SUPPORTFORGE_ALLOWED_USERS", "")
    actor = (user or "console-local").strip()[:120]
    if allowed and actor not in allowed:
        audit_security("user_authorization", actor=actor, result="denied")
        raise HTTPException(status_code=403, detail="User is not authorized")
    audit_security("user_authorization", actor=actor)
    return actor


def authorize_channel(channel: str | None) -> str:
    allowed = _csv("SUPPORTFORGE_ALLOWED_CHANNELS", "")
    name = (channel or "console").strip()[:120]
    if allowed and name not in allowed:
        audit_security("channel_authorization", actor=name, result="denied")
        raise PermissionError("Channel is not authorized")
    audit_security("channel_authorization", actor=name)
    return name


def network_destination_allowed(host: str) -> bool:
    """Application-level egress gate for optional integrations."""
    allowed = _csv("SUPPORTFORGE_ALLOWED_EXTERNAL_HOSTS", "api.anthropic.com")
    return host in allowed


def allowed_case_path(case_id: str, relative: str = "") -> Path:
    """Resolve only files below workspace/cases/<CASE-ID>."""
    if not CASE_ID_RE.fullmatch(case_id or ""):
        raise ValueError("invalid case identifier")
    base = (WORKSPACE / "cases" / case_id).resolve()
    candidate = (base / relative).resolve()
    if candidate != base and base not in candidate.parents:
        raise ValueError("path outside approved case folder")
    return candidate


def allowed_output_path(case_id: str, filename: str) -> Path:
    """Resolve generated artifacts only inside the designated outbox."""
    if not CASE_ID_RE.fullmatch(case_id or "") or not re.fullmatch(r"[A-Za-z0-9._-]+", filename or ""):
        raise ValueError("invalid output path")
    outbox = (WORKSPACE / "outbox").resolve()
    candidate = (outbox / f"{case_id}-{filename}").resolve()
    if outbox not in candidate.parents:
        raise ValueError("path outside approved output folder")
    return candidate


def _is_loopback(request: Request) -> bool:
    # Starlette's in-process TestClient uses this synthetic peer name.
    if request.client and request.client.host in {"testclient", "testserver"}:
        return True
    try:
        return ip_address(request.client.host if request.client else "").is_loopback
    except ValueError:
        return False


async def require_api_key(request: Request, x_api_key: str | None = Header(default=None)) -> None:
    """Protect API routes when SUPPORTFORGE_API_KEY is configured.

    With no key configured, only loopback callers are accepted. This preserves
    the laptop demo while preventing an accidentally exposed unauthenticated
    server when it is bound beyond localhost.
    """
    configured = os.getenv("SUPPORTFORGE_API_KEY", "").strip()
    client = request.client.host if request.client else "unknown"
    if not configured:
        if _is_loopback(request):
            return
        audit_security("api_key", actor=client, result="denied", reason="missing_key_non_loopback")
        raise HTTPException(status_code=401, detail="API key required for non-local access")
    supplied = x_api_key or ""
    if not hmac.compare_digest(hashlib.sha256(supplied.encode()).digest(), hashlib.sha256(configured.encode()).digest()):
        audit_security("api_key", actor=client, result="denied", reason="invalid_or_missing_key")
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


class SecurityMiddleware(BaseHTTPMiddleware):
    """Headers, request-size guard, and modest in-process abuse protection."""

    def __init__(self, app, max_body_bytes: int = 1_048_576, rate_limit: int = 120):
        super().__init__(app)
        self.max_body_bytes = max_body_bytes
        self.rate_limit = rate_limit
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path.startswith("/api/"):
            length = request.headers.get("content-length")
            if length:
                try:
                    too_large = int(length) > self.max_body_bytes
                except ValueError:
                    return JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)
                if too_large:
                    return JSONResponse({"detail": "Request body too large"}, status_code=413)
            client = request.client.host if request.client else "unknown"
            now = time.monotonic()
            with self._lock:
                hits = self._hits[client]
                while hits and now - hits[0] > 60:
                    hits.popleft()
                if len(hits) >= self.rate_limit:
                    return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
                hits.append(now)

        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; script-src 'self'")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response


def allowed_hosts() -> list[str]:
    return _csv("SUPPORTFORGE_ALLOWED_HOSTS", "127.0.0.1,localhost,testserver")
