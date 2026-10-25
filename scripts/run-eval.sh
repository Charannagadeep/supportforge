#!/usr/bin/env bash
# Laptop-only eval. Rule suite is fast; LLM suite needs Ollama + qwen2.5:7b-instruct.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source .venv/bin/activate
MODE="${1:-rule}"

echo "=== pytest (deterministic) ==="
python -m pytest tests/test_engine_security.py tests/test_eval_rule.py -q

if [[ "$MODE" == "llm" || "$MODE" == "all" ]]; then
  echo "=== live LLM suite via API (console must be up) ==="
  curl -sf -X POST http://127.0.0.1:8787/api/eval/run \
    -H 'content-type: application/json' \
    -d '{"mode":"llm"}' | python3 -m json.tool | tee workspace/outbox/eval-llm-pretty.json
else
  echo "=== rule suite via Python ==="
  python - <<'PY'
from app.eval import run_suite
import json
print(json.dumps(run_suite("rule"), indent=2))
PY
fi

echo "Done. Artifacts under workspace/outbox/eval-*.json"
