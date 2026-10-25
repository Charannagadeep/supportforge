"""Behavioral tests for the always-on case watcher (Task 3).

Run with:  pytest -q   (from the repo root, inside the venv)

These exercise the watcher without a live model, so they verify the
deterministic contract: auto re-audit on evidence change, de-duplicated
notices, restart safety, and no false completion from unrelated files.
"""
from __future__ import annotations

import shutil

import pytest

from app import engine, watcher

ROOT = engine.ROOT
DEMO = ROOT / "cases"


@pytest.fixture()
def fresh(tmp_path):
    """Run against the real workspace, snapshotting and restoring it.

    The engine and security layers both resolve paths from their own module
    ``WORKSPACE`` constant, so redirecting one without the other is inconsistent.
    Testing the real wiring end-to-end (and restoring afterwards) exercises
    exactly what ships. Live case state and watcher memory/outbox are backed up
    and restored so the test leaves no trace.
    """
    ws = engine.WORKSPACE
    live_cases = engine.CASES_DIR
    backup = tmp_path / "ws-backup"
    if ws.exists():
        shutil.copytree(ws, backup, dirs_exist_ok=True)

    # Start from a clean watcher state + outbox.
    for p in (watcher.STATE_PATH, watcher.WATCH_LOG):
        if p.exists():
            p.unlink()
    if live_cases.exists():
        shutil.rmtree(live_cases)
    watcher.set_channel_notifier(None)

    engine.ensure_layout()
    engine.seed_all_demo_cases()
    engine.reset_demo_case("CASE-1042")
    try:
        yield live_cases
    finally:
        watcher.set_channel_notifier(None)
        if backup.exists():
            if ws.exists():
                shutil.rmtree(ws)
            shutil.copytree(backup, ws, dirs_exist_ok=True)


def _notices():
    bucket: list[dict] = []
    watcher.set_channel_notifier(bucket.append)
    return bucket


def test_initial_scan_audits_incomplete(fresh):
    state = watcher.scan_once()
    assert state["cases"]["CASE-1042"]["completeness"] == 60


def test_no_change_rescan_is_silent(fresh):
    notices = _notices()
    state = watcher.scan_once()
    notices.clear()
    before = watcher.WATCH_LOG.read_text()
    watcher.scan_once(state)
    assert watcher.WATCH_LOG.read_text() == before
    assert notices == []


def test_raw_file_drop_auto_updates(fresh):
    """Core Task 3 contract: a hand-dropped file re-audits with no API call."""
    notices = _notices()
    state = watcher.scan_once()
    notices.clear()
    # copy2 preserves the source mtime (backdated) — signature detection must
    # still catch it, which a newest-mtime-only check would miss.
    shutil.copy2(
        DEMO / "CASE-1042-complete" / "incoming" / "environment.json",
        fresh / "CASE-1042" / "incoming" / "environment.json",
    )
    state = watcher.scan_once(state)
    assert state["cases"]["CASE-1042"]["completeness"] == 80
    assert len(notices) == 1 and notices[0]["case_id"] == "CASE-1042"


def test_unrelated_file_does_not_complete(fresh):
    state = watcher.scan_once()
    (fresh / "CASE-1042" / "incoming" / "notes.txt").write_text("scratch\n")
    state = watcher.scan_once(state)
    assert state["cases"]["CASE-1042"]["completeness"] == 60


def test_restart_retains_history(fresh):
    notices = _notices()
    watcher.scan_once()
    notices.clear()
    reloaded = watcher._load_state()  # simulates a fresh process
    watcher.scan_once(reloaded)
    assert notices == []


def test_regression_flips_present_to_missing(fresh):
    state = watcher.scan_once()
    for name in ("environment.json", "nvidia-smi.txt"):
        shutil.copy2(
            DEMO / "CASE-1042-complete" / "incoming" / name,
            fresh / "CASE-1042" / "incoming" / name,
        )
    state = watcher.scan_once(state)
    assert state["cases"]["CASE-1042"]["completeness"] == 100
    (fresh / "CASE-1042" / "incoming" / "nvidia-smi.txt").unlink()
    notices = _notices()
    state = watcher.scan_once(state)
    assert state["cases"]["CASE-1042"]["completeness"] < 100
    assert len(notices) == 1
