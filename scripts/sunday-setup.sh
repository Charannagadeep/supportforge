#!/usr/bin/env bash
# Install SupportForge workspace into a NemoClaw/OpenClaw sandbox (GB10 or laptop).
# Prefer the full OpenShell path: bash scripts/install-openshell.sh supportforge
set -euo pipefail

SANDBOX="${1:-my-assistant}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ "${SANDBOX}" == "supportforge" ]] || command -v openshell >/dev/null 2>&1; then
  exec bash "${ROOT}/scripts/install-openshell.sh" "${SANDBOX}"
fi

echo "== SupportForge → sandbox: $SANDBOX =="
echo "Source: $ROOT"

# Prefer nemoclaw connect + copy into workspace. Paths vary slightly by install;
# we try common OpenClaw workspace locations.
copy_into_sandbox() {
  local dest="$1"
  echo "Copying skills + workspace + demo cases → $dest"
  mkdir -p "$dest"
  rsync -a --delete \
    "$ROOT/SOUL.md" "$ROOT/AGENTS.md" "$ROOT/HEARTBEAT.md" \
    "$dest/" 2>/dev/null || {
      cp "$ROOT/SOUL.md" "$ROOT/AGENTS.md" "$ROOT/HEARTBEAT.md" "$dest/"
    }
  rsync -a "$ROOT/skills/" "$dest/skills/"
  rsync -a "$ROOT/workspace/" "$dest/workspace/"
  mkdir -p "$dest/workspace/cases"
  rsync -a "$ROOT/cases/CASE-1042/" "$dest/workspace/cases/CASE-1042/"
  # Keep complete pack outside live case for demo step 2
  rsync -a "$ROOT/cases/CASE-1042-complete/" "$dest/workspace/demo-complete/CASE-1042/"
  echo "Live case ready: $dest/workspace/cases/CASE-1042"
  echo "Complete pack:   $dest/workspace/demo-complete/CASE-1042"
}

if command -v nemoclaw >/dev/null 2>&1; then
  echo "NemoClaw detected. Opening sandbox shell to copy files..."
  # Host-side staging that also works if connect is awkward:
  STAGE="${HOME}/supportforge-stage"
  rm -rf "$STAGE"
  mkdir -p "$STAGE"
  copy_into_sandbox "$STAGE"
  echo
  echo "Staged at $STAGE"
  echo "Next: copy into the sandbox workspace, e.g."
  echo "  nemoclaw $SANDBOX connect"
  echo "  # then inside sandbox, place files in the OpenClaw workspace root"
  echo "Or from host (if openshell mount available):"
  echo "  rsync -a $STAGE/ <sandbox-workspace>/"
else
  STAGE="${HOME}/supportforge-stage"
  rm -rf "$STAGE"
  copy_into_sandbox "$STAGE"
  echo "nemoclaw not on PATH yet — staged locally at $STAGE"
  echo "Run Express Install first, then re-run this script."
fi

echo
echo "Demo prompt after install:"
echo "  Audit CASE-1042 and prepare the engineering handoff."
echo "Then copy missing files from workspace/demo-complete/CASE-1042/incoming/"
echo "  into workspace/cases/CASE-1042/incoming/ and ask to refresh the handoff."
