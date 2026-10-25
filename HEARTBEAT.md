# Heartbeat

On each heartbeat:

1. Scan `workspace/cases/` for case folders modified since `workspace/memory/last-scan.json` (or all cases if missing).
2. For each changed case, run **evidence-audit**.
3. If completeness improved or required fields flipped present→missing, run **timeline-builder** (when logs exist) then **escalation-handoff**.
4. Write a one-line update to `workspace/outbox/WATCH.md` and stamp `workspace/memory/last-scan.json`.
5. If a messaging channel is connected and completeness changed, send a short notice: case id, completeness %, top missing item, handoff path.
6. If nothing changed, only update the heartbeat stamp — do not spam.
