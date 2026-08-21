#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
VENV_PYTHON="${REPO_ROOT}/.venv/bin/python"

fail() {
  printf 'test: %s\n' "$*" >&2
  exit 1
}

[[ -x "${VENV_PYTHON}" ]] \
  || fail "repository-local environment not found; run ./scripts/setup.sh first"

cd -- "${REPO_ROOT}"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONHASHSEED=0
export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

"${VENV_PYTHON}" -c 'import pytest' 2>/dev/null \
  || fail "pytest is unavailable in .venv; rerun ./scripts/setup.sh"

exec "${VENV_PYTHON}" -m pytest -p no:cacheprovider "$@"
