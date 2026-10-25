# Heartbeat

On each heartbeat:

1. Scan `workspace/cases/` for case folders modified since `workspace/memory/last-scan.json` (or all cases if missing).
2. For each changed case, run **evidence-audit**.
3. If completeness improved or required fields flipped present→missing, run **timeline-builder** (when logs exist) then **escalation-handoff**.
4. Write a one-line update to `workspace/outbox/WATCH.md` and stamp `workspace/memory/last-scan.json`.
5. If a messaging channel is connected and completeness changed, send a short notice: case id, completeness %, top missing item, handoff path.
6. If nothing changed, only update the heartbeat stamp — do not spam.

## Implementation

This loop is implemented in `app/watcher.py` and started from the FastAPI
app on startup when `SUPPORTFORGE_WATCH=1` is set:

```bash
SUPPORTFORGE_WATCH=1 SUPPORTFORGE_WATCH_INTERVAL=3 bash scripts/start-console.sh
```

- **Change detection** is a content signature (relative path + size + mtime per
  evidence file), so it catches additions, edits, and removals even when a copy
  preserves a backdated mtime — not a newest-mtime-only check.
- **De-duplication** keys each WATCH line / channel notice on the observable
  case state (`completeness:sorted(missing)`), so an unchanged rescan or a
  restart stays silent while any real transition is surfaced exactly once.
- **State** lives in `workspace/memory/last-scan.json` and survives restarts.
- **Graceful degradation**: with no local model online it still audits and
  refreshes the rule-layer handoff, marking the line `model offline`.
- **First discovery** audits and records state only; live-model refresh runs on
  later completeness transitions (set `SUPPORTFORGE_WATCH_LLM=0` to keep the
  loop rule-only).
- **Status** is exposed read-only at `GET /api/watch`.
- **Default off**: without `SUPPORTFORGE_WATCH=1` the console behaves exactly
  as before (safe for demos).

Verify with: `pytest tests/test_watcher.py -q`.
