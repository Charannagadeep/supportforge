#!/usr/bin/env bash
# Practice the SupportForge demo on your laptop (no GB10 / no LLM required).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LIVE="$ROOT/workspace/cases/CASE-1042"
COMPLETE="$ROOT/cases/CASE-1042-complete"
PY="$ROOT/scripts/audit_case.py"

rm -rf "$LIVE"
mkdir -p "$LIVE"
rsync -a "$ROOT/cases/CASE-1042/" "$LIVE/"
mkdir -p "$ROOT/workspace/outbox"

echo "=== STEP 1: Incomplete case ==="
python3 "$PY" "$LIVE"
echo
echo "--- requests ---"
cat "$ROOT/workspace/outbox/CASE-1042-requests.md"
echo

echo "=== STEP 2: Add missing evidence ==="
cp "$COMPLETE/incoming/environment.json" "$LIVE/incoming/"
cp "$COMPLETE/incoming/nvidia-smi.txt" "$LIVE/incoming/"

echo "=== STEP 3: Refresh handoff ==="
python3 "$PY" "$LIVE"
echo
echo "--- handoff (tail) ---"
tail -40 "$ROOT/workspace/outbox/CASE-1042-handoff.md"
echo
echo "Demo files ready under $ROOT/workspace/outbox/"
