#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Auto-detect GB10 when not set
if [[ -z "${SUPPORTFORGE_RUNTIME:-}" ]]; then
  if command -v nvidia-smi >/dev/null 2>&1 || curl -sf -m 1 http://127.0.0.1:8000/v1/models >/dev/null 2>&1; then
    export SUPPORTFORGE_RUNTIME=gb10
  else
    export SUPPORTFORGE_RUNTIME=laptop
  fi
fi

if [[ "${SUPPORTFORGE_RUNTIME}" == "gb10" ]]; then
  export SUPPORTFORGE_LLM_BASE="${SUPPORTFORGE_LLM_BASE:-http://127.0.0.1:8000/v1}"
  export SUPPORTFORGE_HOST="${SUPPORTFORGE_HOST:-0.0.0.0}"
  export SUPPORTFORGE_WATCH="${SUPPORTFORGE_WATCH:-1}"
  if [[ -z "${SUPPORTFORGE_API_KEY:-}" ]]; then
    echo "WARN: GB10 shared box should set SUPPORTFORGE_API_KEY (see scripts/gb10-bringup.sh)" >&2
  fi
fi

if [[ ! -d .venv ]]; then
  if command -v uv >/dev/null 2>&1; then
    uv venv .venv
  else
    python3 -m venv .venv
  fi
fi
# shellcheck disable=SC1091
source .venv/bin/activate
if command -v uv >/dev/null 2>&1; then
  uv pip install -e . -q
else
  pip install -e . -q
fi

HOST="${SUPPORTFORGE_HOST:-127.0.0.1}"
PORT="${SUPPORTFORGE_PORT:-8787}"
echo "SupportForge console [${SUPPORTFORGE_RUNTIME}] → http://${HOST}:${PORT}"
if [[ "${SUPPORTFORGE_RUNTIME}" == "gb10" ]]; then
  echo "Expect provider: vLLM · Qwen3.6-35B-A3B-NVFP4 (or served id on :8000)"
fi
exec python -m uvicorn app.main:app --host "${HOST}" --port "${PORT}"
