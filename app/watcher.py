"""Always-on case watcher for SupportForge.

Implements the loop described in HEARTBEAT.md:

1. Scan ``workspace/cases/`` for case folders changed since the last scan.
2. For each changed case, run the deterministic evidence audit.
3. If completeness improved (or a required field flipped present->missing),
   refresh the live-model narrative when a local model is online.
4. Append one line to ``workspace/outbox/WATCH.md`` and stamp
   ``workspace/memory/last-scan.json``.
5. If a channel is connected and completeness changed, emit a single short
   notice (de-duplicated per revision — never spam).

Design notes
------------
* Pure-local: no network calls of its own; LLM use goes through the existing
  ``agent._investigate`` path, which is already guarded and local-first.
* Restart-safe: per-case state (mtime, completeness, last notified revision)
  is persisted in ``last-scan.json`` so a restart does not re-notify.
* Degrades gracefully: when no model is online it still audits, refreshes the
  rule-layer handoff, and records a WATCH line marked ``model offline``.
* Opt-in: the FastAPI app only starts this when ``SUPPORTFORGE_WATCH=1`` so
  tests and CI stay deterministic.
"""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import agent, engine, llm
from .security import audit_security

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "workspace"
CASES_DIR = WORKSPACE / "cases"
OUTBOX = WORKSPACE / "outbox"
MEMORY = WORKSPACE / "memory"
STATE_PATH = MEMORY / "last-scan.json"
WATCH_LOG = OUTBOX / "WATCH.md"

# One lock guards audit+investigate for a single case so the background watcher
# and a manual /investigate call never interleave writes to the same handoff.
_CASE_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()

# Optional channel sink. Task 5 (console/channel) can register a callable here
# via ``set_channel_notifier``. It receives a dict payload and should return
# truthy on success. Kept as a seam so the watcher owns the *trigger* and
# de-duplication while the transport lives elsewhere.
_CHANNEL_NOTIFIER: Callable[[dict[str, Any]], Any] | None = None


def set_channel_notifier(fn: Callable[[dict[str, Any]], Any] | None) -> None:
    """Register (or clear) the channel transport used for change notices."""
    global _CHANNEL_NOTIFIER
    _CHANNEL_NOTIFIER = fn


def _case_lock(case_id: str) -> threading.Lock:
    with _LOCKS_GUARD:
        lock = _CASE_LOCKS.get(case_id)
        if lock is None:
            lock = threading.Lock()
            _CASE_LOCKS[case_id] = lock
        return lock


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_state() -> dict[str, Any]:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            audit_security("watch_state", result="reset", reason="unreadable_state")
    return {"cases": {}, "updated": None}


def _save_state(state: dict[str, Any]) -> None:
    MEMORY.mkdir(parents=True, exist_ok=True)
    state["updated"] = _now()
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def _case_signature(case: Path) -> str:
    """Content signature over evidence files, ignoring engine-written artifacts.

    Uses the sorted set of relative paths plus each file's size and mtime. This
    catches additions, removals, and edits even when a copy preserves the source
    mtime (e.g. ``cp -p`` / ``shutil.copy2``) or an editor writes a backdated
    timestamp — cases a newest-mtime-only check would miss.
    """
    parts: list[str] = []
    for p in sorted(case.rglob("*")):
        if not p.is_file() or p.name in {"audit.json", "timeline.md"}:
            continue
        try:
            st = p.stat()
        except OSError:
            continue
        parts.append(f"{p.relative_to(case)}:{st.st_size}:{int(st.st_mtime)}")
    return "|".join(parts)


def _missing_required(audit: dict[str, Any]) -> list[str]:
    return [
        r["item"]
        for r in audit.get("evidence", [])
        if r.get("required") and r.get("status") != "present"
    ]


def _append_watch_line(line: str) -> None:
    OUTBOX.mkdir(parents=True, exist_ok=True)
    if not WATCH_LOG.exists():
        WATCH_LOG.write_text("# SupportForge watch log\n\n")
    with WATCH_LOG.open("a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")


def _notify_channel(payload: dict[str, Any]) -> None:
    """Emit one de-duplicated change notice via the registered transport."""
    if _CHANNEL_NOTIFIER is None:
        return
    try:
        _CHANNEL_NOTIFIER(payload)
        audit_security(
            "channel_notify",
            actor="watcher",
            case_id=payload.get("case_id"),
            completeness=payload.get("completeness_percent"),
        )
    except Exception as e:  # noqa: BLE001 — a bad channel must not kill the loop
        audit_security(
            "channel_notify",
            actor="watcher",
            result="error",
            case_id=payload.get("case_id"),
            error=type(e).__name__,
        )


def process_case(case_id: str, prev: dict[str, Any] | None) -> dict[str, Any]:
    """Audit one case, refresh the narrative on meaningful change, notify once.

    Returns the new per-case state record. Safe to call directly from tests.
    """
    with _case_lock(case_id):
        audit = engine.audit_case(case_id)
        new_pct = int(audit.get("completeness_percent", 0))
        new_missing = _missing_required(audit)

        prev = prev or {}
        prev_pct = prev.get("completeness")
        prev_missing = set(prev.get("missing", []) or [])
        flipped_to_missing = bool(set(new_missing) - prev_missing)
        improved = prev_pct is None or new_pct > prev_pct
        # A change worth surfacing: first time we've audited this case in a
        # running session, a completeness delta, or a required field regressing.
        changed = (prev_pct is None) or (new_pct != prev_pct) or flipped_to_missing

        model_note = "rule-layer only (model offline)"
        provider = llm.detect_provider()
        model_online = provider.get("provider") not in ("none",) and provider.get("status") != "no_models"

        # Refresh the live-model narrative only when the picture meaningfully
        # changed and a local model is actually reachable.
        if (improved or flipped_to_missing) and model_online:
            try:
                inv = agent._investigate(case_id, audit)  # noqa: SLF001 — internal reuse by design
                meta = inv.get("model_meta") or {}
                model_note = f"{meta.get('provider', provider.get('provider'))}/{meta.get('model', provider.get('model'))}"
            except Exception as e:  # noqa: BLE001
                model_note = f"model error: {type(e).__name__}"
                audit_security(
                    "watch_investigate",
                    actor="watcher",
                    result="error",
                    case_id=case_id,
                    error=type(e).__name__,
                )

        # The notice key is the *state* the notice describes — completeness plus
        # the sorted missing set — not the audit timestamp. Two audits in the
        # same clock-second share a timestamp, so keying on the timestamp would
        # wrongly suppress a real change; keying on observable state means an
        # identical state is never re-announced but any real change is.
        revision = f"{new_pct}:{','.join(sorted(new_missing))}"
        last_notified = prev.get("notified_revision")

        # Only surface when the observable state actually differs from what we
        # last announced. This keeps a restart (state reloaded from disk) and a
        # no-op rescan silent, while any real transition logs + notifies once.
        if changed and revision != last_notified:
            top_missing = new_missing[0] if new_missing else "none"
            _append_watch_line(
                f"- {_now()} · **{case_id}** → {new_pct}% "
                f"(was {prev_pct if prev_pct is not None else '—'}%) · "
                f"top missing: {top_missing} · {model_note} · "
                f"handoff: `workspace/outbox/{case_id}-handoff.md`"
            )
            _notify_channel(
                {
                    "case_id": case_id,
                    "completeness_percent": new_pct,
                    "top_missing": top_missing,
                    "handoff_path": f"workspace/outbox/{case_id}-handoff.md",
                    "revision": revision,
                    "model": model_note,
                }
            )
            last_notified = revision
            audit_security(
                "watch_update",
                actor="watcher",
                case_id=case_id,
                completeness=new_pct,
                changed="yes",
            )

        return {
            "signature": _case_signature(CASES_DIR / case_id),
            "completeness": new_pct,
            "missing": new_missing,
            "notified_revision": last_notified,
            "last_seen": _now(),
        }


def scan_once(state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run one heartbeat pass over all cases. Returns the updated state."""
    engine.ensure_layout()
    state = state if state is not None else _load_state()
    cases_state: dict[str, Any] = state.setdefault("cases", {})

    for d in sorted(CASES_DIR.iterdir() if CASES_DIR.exists() else []):
        if not d.is_dir() or d.name.startswith("."):
            continue
        case_id = d.name
        prev = cases_state.get(case_id)
        current_sig = _case_signature(d)
        # First sight (no prior state) or any evidence change -> reprocess.
        if prev is None or current_sig != prev.get("signature"):
            cases_state[case_id] = process_case(case_id, prev)

    _save_state(state)
    return state


def run_loop(interval: float, stop: threading.Event) -> None:
    """Poll on ``interval`` seconds until ``stop`` is set."""
    audit_security("watch_start", actor="watcher", interval=interval)
    state = _load_state()
    # Prime once immediately so a fresh start reflects current reality.
    try:
        state = scan_once(state)
    except Exception as e:  # noqa: BLE001
        audit_security("watch_scan", result="error", error=type(e).__name__)
    while not stop.wait(interval):
        try:
            state = scan_once(state)
        except Exception as e:  # noqa: BLE001 — never let one bad pass stop the watcher
            audit_security("watch_scan", result="error", error=type(e).__name__)
    audit_security("watch_stop", actor="watcher")


_THREAD: threading.Thread | None = None
_STOP: threading.Event | None = None


def start_background() -> bool:
    """Start the watcher thread if ``SUPPORTFORGE_WATCH=1``. Returns started?."""
    global _THREAD, _STOP
    if os.getenv("SUPPORTFORGE_WATCH", "").strip() not in ("1", "true", "yes", "on"):
        return False
    if _THREAD and _THREAD.is_alive():
        return True
    interval = float(os.getenv("SUPPORTFORGE_WATCH_INTERVAL", "3"))
    _STOP = threading.Event()
    _THREAD = threading.Thread(
        target=run_loop, args=(interval, _STOP), name="supportforge-watcher", daemon=True
    )
    _THREAD.start()
    return True


def stop_background() -> None:
    """Signal the watcher thread to stop (best-effort; daemon dies with proc)."""
    if _STOP is not None:
        _STOP.set()
