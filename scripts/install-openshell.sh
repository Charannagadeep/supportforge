#!/usr/bin/env bash
# Install SupportForge into a NemoClaw/OpenShell sandbox.
# Laptop: Colima + Ollama.  GB10: Express Install vLLM/NIM (set SUPPORTFORGE_RUNTIME=gb10).
set -euo pipefail

SANDBOX="${1:-supportforge}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="${HOME}/supportforge-openshell-stage"
RUNTIME="${SUPPORTFORGE_RUNTIME:-}"

export PATH="${HOME}/homebrew/bin:${HOME}/.local/bin:/usr/local/bin:${PATH}"
if [[ -x "${HOME}/homebrew/bin/brew" ]]; then
  # shellcheck disable=SC1090
  eval "$("${HOME}/homebrew/bin/brew" shellenv)"
fi

# Auto-detect GB10
if [[ -z "${RUNTIME}" ]]; then
  if command -v nvidia-smi >/dev/null 2>&1; then
    RUNTIME=gb10
  else
    RUNTIME=laptop
  fi
fi

need() { command -v "$1" >/dev/null 2>&1 || { echo "missing: $1" >&2; exit 1; }; }
need nemoclaw
need openshell

echo "== SupportForge → OpenShell sandbox: ${SANDBOX} (${RUNTIME}) =="
echo "Source: ${ROOT}"

if [[ "${RUNTIME}" == "laptop" ]]; then
  need docker
  need ollama
  if ! docker info >/dev/null 2>&1; then
    echo "Docker not ready — starting Colima (4 CPU / 8G / 40G)…"
    colima start --cpu 4 --memory 8 --disk 40
  fi
  ollama list 2>/dev/null | grep -q 'qwen2.5:7b-instruct' || ollama pull qwen2.5:7b-instruct
else
  # GB10: Docker or container runtime should already be up from Express Install
  if command -v docker >/dev/null 2>&1 && ! docker info >/dev/null 2>&1; then
    echo "WARN: docker not ready — Express Install / NemoClaw may still manage the sandbox."
  fi
  if ! curl -sf -m 2 http://127.0.0.1:8000/v1/models >/dev/null 2>&1; then
    echo "WARN: vLLM/NIM not responding on :8000 yet — start Express serving, then investigate."
  else
    echo "vLLM/NIM healthy on :8000"
    curl -sS -m 3 http://127.0.0.1:8000/v1/models | head -c 300; echo
  fi
fi

if ! nemoclaw list 2>/dev/null | grep -q "${SANDBOX}"; then
  if [[ "${RUNTIME}" == "gb10" ]]; then
    cat >&2 <<EOF
Sandbox '${SANDBOX}' not found on GB10.
Run Express Install / onboard once (Spark profile → Qwen3.6-35B-A3B-NVFP4 + OpenClaw),
name the sandbox '${SANDBOX}', then re-run:

  bash scripts/gb10-bringup.sh ${SANDBOX}
  # or: bash scripts/install-openshell.sh ${SANDBOX}
EOF
  else
    cat >&2 <<EOF
Sandbox '${SANDBOX}' not found.
Create it once (laptop + Colima + Ollama), then re-run this script:

  export NEMOCLAW_PROVIDER=ollama
  export NEMOCLAW_MODEL=qwen2.5:7b-instruct
  export NEMOCLAW_SANDBOX=${SANDBOX}
  export NEMOCLAW_AGENT=openclaw
  bash ../scripts/nemoclaw.sh --non-interactive --yes-i-accept-third-party-software
EOF
  fi
  exit 1
fi

nemoclaw "${SANDBOX}" start 2>/dev/null || true
nemoclaw use "${SANDBOX}" >/dev/null 2>&1 || true

# Stage host tree
rm -rf "${STAGE}"
mkdir -p "${STAGE}/workspace/cases" "${STAGE}/workspace/demo-complete" \
  "${STAGE}/workspace/outbox" "${STAGE}/workspace/runbooks" \
  "${STAGE}/workspace/memory" "${STAGE}/workspace/corpus"
cp "${ROOT}/SOUL.md" "${ROOT}/AGENTS.md" "${ROOT}/HEARTBEAT.md" "${STAGE}/"
[[ -f "${ROOT}/SECURITY.md" ]] && cp "${ROOT}/SECURITY.md" "${STAGE}/"
[[ -f "${ROOT}/BENCHMARK.md" ]] && cp "${ROOT}/BENCHMARK.md" "${STAGE}/"
rsync -a "${ROOT}/skills/" "${STAGE}/skills/"
[[ -d "${ROOT}/workspace/runbooks" ]] && rsync -a "${ROOT}/workspace/runbooks/" "${STAGE}/workspace/runbooks/"

for cid in CASE-1042 CASE-1088 CASE-1101 CASE-1120 CASE-1155 CASE-2161 CASE-2163; do
  [[ -d "${ROOT}/cases/${cid}" ]] && rsync -a "${ROOT}/cases/${cid}/" "${STAGE}/workspace/cases/${cid}/"
  [[ -d "${ROOT}/cases/${cid}-complete" ]] && rsync -a "${ROOT}/cases/${cid}-complete/" "${STAGE}/workspace/demo-complete/${cid}/"
done

WS="/sandbox/.openclaw/workspace"
for f in SOUL.md AGENTS.md HEARTBEAT.md SECURITY.md BENCHMARK.md; do
  [[ -f "${STAGE}/${f}" ]] && nemoclaw "${SANDBOX}" upload "${STAGE}/${f}" "${WS}/${f}"
done
for d in cases demo-complete outbox runbooks memory corpus; do
  [[ -d "${STAGE}/workspace/${d}" ]] && nemoclaw "${SANDBOX}" upload "${STAGE}/workspace/${d}/" "${WS}/${d}/"
done

for sk in evidence-audit timeline-builder escalation-handoff; do
  echo "skill install: ${sk}"
  nemoclaw "${SANDBOX}" skill install "${ROOT}/skills/${sk}"
done

# On GB10 the 35B model can tool-call — restore a sane coding profile (not the laptop 7B lockdown)
if [[ "${RUNTIME}" == "gb10" ]]; then
  echo "Restoring OpenClaw coding tool profile for GB10 (35B)…"
  nemoclaw "${SANDBOX}" exec --timeout 30 -- bash -lc '
    openclaw config set tools.profile coding 2>/dev/null || true
    openclaw config set tools.deny --strict-json '\''["web_search","browser","image_generate","music_generate","video_generate","tts","computer","mobile_ui"]'\'' 2>/dev/null || true
  ' || true
fi

echo
echo "== Isolation check =="
echo -n "Blocked public egress: "
nemoclaw "${SANDBOX}" exec --timeout 15 -- \
  bash -lc 'curl -sS -m 5 https://example.com >/dev/null 2>&1; echo exit:$?' || echo "blocked (expected)"
echo -n "Inference path: "
nemoclaw "${SANDBOX}" status 2>&1 | grep -E 'Inference:|Model:|Provider:|OpenClaw:|GPU' | head -8 || true

echo
echo "Ready. Demo (one line at a time):"
echo "  nemoclaw launch ${SANDBOX}"
echo "  nemoclaw ${SANDBOX} agent --agent main -m 'Audit CASE-1042 with evidence-audit'"
echo "  nemoclaw ${SANDBOX} dashboard-url"
if [[ "${RUNTIME}" == "gb10" ]]; then
  echo "Console: SUPPORTFORGE_RUNTIME=gb10 bash scripts/start-console.sh"
  echo "Or full path: bash scripts/gb10-bringup.sh ${SANDBOX}"
else
  echo "Console: bash scripts/start-console.sh → http://127.0.0.1:8787"
fi
