#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ ! -d .venv ]]; then
  uv venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
uv pip install -e . -q
echo "SupportForge console → http://127.0.0.1:8787"
exec python -m uvicorn app.main:app --host "${SUPPORTFORGE_HOST:-127.0.0.1}" --port "${SUPPORTFORGE_PORT:-8787}"
