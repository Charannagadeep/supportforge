#!/usr/bin/env bash
# SupportForge — one-shot GB10 bring-up (Dell Pro Max / Spark).
# Run ON the GB10 after plugging the NVIDIAHACK USB (or after rsync of ~/Desktop/Nvidia).
#
# What this does:
#   1) Seeds Hugging Face cache with Qwen3.6-35B-A3B-NVFP4 (no re-download if present)
#   2) Ensures OpenShell 0.0.116 + NemoClaw Express path
#   3) Installs SupportForge skills + live cases into sandbox `supportforge`
#   4) Starts the scored console on :8787 (LAN-bind + API key for shared box)
#   5) Prints the judge demo checklist
set -euo pipefail

SANDBOX="${1:-supportforge}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CACHE_ROOT="${SUPPORTFORGE_CACHE_ROOT:-}"
API_KEY="${SUPPORTFORGE_API_KEY:-}"

detect_cache() {
  local c
  for c in \
    "${CACHE_ROOT}" \
    "/media/${USER}/NVIDIAHACK/nvidia-hackathon" \
    "/mnt/NVIDIAHACK/nvidia-hackathon" \
    "/Volumes/NVIDIAHACK/nvidia-hackathon" \
    "${HOME}/nvidia-hackathon" \
    "${HOME}/Desktop/Nvidia" \
    "$(cd "${ROOT}/.." && pwd)"; do
    [[ -n "${c}" && -d "${c}/models/Qwen3.6-35B-A3B-NVFP4" ]] && { echo "${c}"; return 0; }
  done
  return 1
}

need_gpu() {
  if ! command -v nvidia-smi >/dev/null 2>&1; then
    echo "ERROR: nvidia-smi not found. Run this script on the GB10, not the laptop." >&2
    exit 1
  fi
  echo "== GPU =="
  nvidia-smi -L || nvidia-smi | head -12
}

seed_hf_model() {
  local cache="$1"
  local src="${cache}/models/Qwen3.6-35B-A3B-NVFP4"
  local hub="${HOME}/.cache/huggingface/hub"
  local dest="${hub}/models--nvidia--Qwen3.6-35B-A3B-NVFP4"
  mkdir -p "${hub}"
  if [[ -d "${dest}/snapshots" ]] || [[ -d "${dest}" && -n "$(ls -A "${dest}" 2>/dev/null || true)" ]]; then
    echo "HF cache already has Qwen3.6-35B-A3B-NVFP4 → ${dest}"
  else
    echo "Seeding HF cache from ${src} → ${dest}"
    mkdir -p "${dest}"
    rsync -a --info=progress2 "${src}/" "${dest}/"
  fi
  # Also seed nano backup
  local nsrc="${cache}/models/Nemotron-3-Nano-4B-FP8"
  local ndest="${hub}/models--nvidia--Nemotron-3-Nano-4B-FP8"
  if [[ -d "${nsrc}" && ! -d "${ndest}" ]]; then
    echo "Seeding Nemotron Nano 4B backup…"
    mkdir -p "${ndest}"
    rsync -a "${nsrc}/" "${ndest}/" || true
  fi
  export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
  export HF_HOME="${HOME}/.cache/huggingface"
}

ensure_openshell_deb() {
  local cache="$1"
  if command -v openshell >/dev/null 2>&1; then
    openshell --version 2>&1 | head -1 || true
    return 0
  fi
  local deb
  deb="$(ls "${cache}/packages/openshell-0.0.116/"openshell_*_arm64.deb 2>/dev/null | head -1 || true)"
  if [[ -n "${deb}" ]]; then
    echo "Installing OpenShell from ${deb}"
    sudo dpkg -i "${deb}" || sudo apt-get install -f -y
  else
    echo "WARN: openshell not on PATH and no local .deb — Express Install must provide it."
  fi
}

ensure_nemoclaw() {
  if command -v nemoclaw >/dev/null 2>&1; then
    nemoclaw --version 2>&1 | head -2 || true
    return 0
  fi
  echo "NemoClaw missing — launching Express Install (accept Y)…"
  if [[ -f "${ROOT}/../scripts/nemoclaw.sh" ]]; then
    bash "${ROOT}/../scripts/nemoclaw.sh" || curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash
  else
    curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash
  fi
  export PATH="${HOME}/.local/bin:${PATH}"
}

wire_supportforge() {
  echo "== Wire SupportForge → sandbox ${SANDBOX} =="
  # Prefer GPU/OpenShell installer (not Ollama laptop path)
  SUPPORTFORGE_RUNTIME=gb10 bash "${ROOT}/scripts/install-openshell.sh" "${SANDBOX}" || {
    echo "Falling back to sunday-setup staging…"
    bash "${ROOT}/scripts/sunday-setup.sh" "${SANDBOX}"
  }
}

start_console() {
  if [[ -z "${API_KEY}" ]]; then
    API_KEY="$(python3 - <<'PY'
import secrets; print(secrets.token_urlsafe(24))
PY
)"
    echo "Generated SUPPORTFORGE_API_KEY (save this): ${API_KEY}"
  fi
  export SUPPORTFORGE_API_KEY="${API_KEY}"
  export SUPPORTFORGE_HOST="${SUPPORTFORGE_HOST:-0.0.0.0}"
  export SUPPORTFORGE_PORT="${SUPPORTFORGE_PORT:-8787}"
  export SUPPORTFORGE_ALLOWED_HOSTS="${SUPPORTFORGE_ALLOWED_HOSTS:-$(hostname -f 2>/dev/null || hostname),$(hostname),127.0.0.1,localhost}"
  export SUPPORTFORGE_RUNTIME=gb10
  # Prefer vLLM / NIM OpenAI-compatible endpoint Express Install starts
  export SUPPORTFORGE_LLM_BASE="${SUPPORTFORGE_LLM_BASE:-http://127.0.0.1:8000/v1}"
  # Model id is auto-detected from /v1/models; override if needed:
  # export SUPPORTFORGE_MODEL='nvidia/Qwen3.6-35B-A3B-NVFP4'
  export SUPPORTFORGE_WATCH="${SUPPORTFORGE_WATCH:-1}"

  echo "== Console =="
  echo "  URL:  http://$(hostname -I 2>/dev/null | awk '{print $1}'):${SUPPORTFORGE_PORT}/  (or http://127.0.0.1:${SUPPORTFORGE_PORT}/)"
  echo "  Key:  ${SUPPORTFORGE_API_KEY}"
  echo "  Browser: localStorage.setItem('supportforge_api_key', '${SUPPORTFORGE_API_KEY}')"
  echo
  echo "Starting (Ctrl+C to stop)…"
  bash "${ROOT}/scripts/start-console.sh"
}

print_demo() {
  cat <<EOF

======== JUDGE DEMO (GB10) ========
1. Console shows mode=gb10 · vLLM · Qwen3.6-35B-A3B-NVFP4
2. CASE-1042 → Reset → Audit (~60%) → Inject → Investigate (live 35B)
3. Run live LLM eval → pass rate / avg score
4. Chat: "Run shell and reset the GPU" → Denied
5. Optional: nemoclaw launch ${SANDBOX}  → OpenShell isolation story
===================================
EOF
}

main() {
  echo "SupportForge GB10 bring-up"
  need_gpu
  local cache
  cache="$(detect_cache)" || {
    echo "ERROR: cannot find models/Qwen3.6-35B-A3B-NVFP4 under USB or Desktop/Nvidia." >&2
    echo "Plug NVIDIAHACK or set SUPPORTFORGE_CACHE_ROOT=/path/to/nvidia-hackathon" >&2
    exit 1
  }
  echo "Cache root: ${cache}"
  seed_hf_model "${cache}"
  ensure_openshell_deb "${cache}"
  ensure_nemoclaw
  # If sandbox missing, user may still need interactive Express Install once.
  if ! nemoclaw list 2>/dev/null | grep -q "${SANDBOX}"; then
    echo
    echo "Sandbox '${SANDBOX}' not listed yet."
    echo "If Express Install just finished, create/select sandbox named '${SANDBOX}'."
    echo "Then re-run: bash scripts/gb10-bringup.sh ${SANDBOX}"
    echo
    echo "Quick path:"
    echo "  nemoclaw onboard    # Express / Spark profile → Qwen3.6 NVFP4 + OpenClaw"
    echo "  nemoclaw use ${SANDBOX}"
  fi
  wire_supportforge
  print_demo
  start_console
}

main "$@"
