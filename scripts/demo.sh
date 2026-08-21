#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
CLI="${REPO_ROOT}/.venv/bin/evidence-state"

if [[ ! -x "${CLI}" ]]; then
  printf 'demo: repository-local evidence-state command not found; run ./scripts/setup.sh first\n' >&2
  exit 1
fi

cd -- "${REPO_ROOT}"
export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
exec "${CLI}" demo "$@"
