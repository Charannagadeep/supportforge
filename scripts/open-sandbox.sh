#!/usr/bin/env bash
# Open the SupportForge OpenShell sandbox (fixes PATH for user Homebrew openshell).
set -euo pipefail
SANDBOX="${1:-supportforge}"
export PATH="${HOME}/homebrew/bin:${HOME}/.local/bin:${PATH}"
if [[ -x "${HOME}/homebrew/bin/brew" ]]; then
  # shellcheck disable=SC1090
  eval "$("${HOME}/homebrew/bin/brew" shellenv)"
fi
command -v openshell >/dev/null || {
  echo "openshell missing — install via brew or re-run NemoClaw setup" >&2
  exit 1
}
command -v nemoclaw >/dev/null || {
  echo "nemoclaw missing — check ~/.local/bin" >&2
  exit 1
}
exec nemoclaw launch "${SANDBOX}"
