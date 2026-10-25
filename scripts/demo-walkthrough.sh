#!/usr/bin/env bash
# Full SupportForge demo: evidence engine + live LLM investigate.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${SUPPORTFORGE_URL:-http://127.0.0.1:8787}"

echo "=== Health ==="
curl -sf "$BASE/api/health" | python3 -m json.tool
echo

echo "=== STEP 1: Reset incomplete CASE-1042 ==="
curl -sf -X POST "$BASE/api/demo/reset?case_id=CASE-1042" | python3 -c 'import sys,json; a=json.load(sys.stdin); print("completeness=%s%%" % a["completeness_percent"])'

echo "=== STEP 2: Inject complete evidence ==="
curl -sf -X POST "$BASE/api/demo/inject-complete?case_id=CASE-1042" | python3 -c 'import sys,json; a=json.load(sys.stdin); print("completeness=%s%%" % a["completeness_percent"]); print("hyps:");
[print(" -",h) for h in a.get("hypotheses",[])]'

echo
echo "=== STEP 3: Live LLM investigate (may take 30–120s) ==="
curl -sf -X POST "$BASE/api/cases/CASE-1042/investigate" \
  -H 'content-type: application/json' | python3 -c '
import sys, json
d = json.load(sys.stdin)
meta = d.get("model_meta") or {}
print("provider:", meta.get("provider"), meta.get("model"))
print("--- reply (head) ---")
print((d.get("reply") or "")[:2500])
'
echo
echo "Full handoff: $BASE/api/cases/CASE-1042/handoff"
echo "LLM report:   $BASE/api/cases/CASE-1042/llm-report"
