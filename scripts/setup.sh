#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
VENV_DIR="${REPO_ROOT}/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"

fail() {
  printf 'setup: %s\n' "$*" >&2
  exit 1
}

command -v "${PYTHON_BIN}" >/dev/null 2>&1 \
  || fail "${PYTHON_BIN} was not found; set PYTHON_BIN to Python 3.11, 3.12, or 3.13"

"${PYTHON_BIN}" - <<'PY' \
  || fail "Python 3.11, 3.12, or 3.13 is required"
import sys

if not ((3, 11) <= sys.version_info < (3, 14)):
    raise SystemExit(1)
PY

[[ -f "${REPO_ROOT}/pyproject.toml" ]] \
  || fail "pyproject.toml is missing from ${REPO_ROOT}"

if [[ -e "${VENV_DIR}" && ! -x "${VENV_DIR}/bin/python" ]]; then
  fail "${VENV_DIR} exists but is not a usable virtual environment; it was not modified"
fi

if [[ ! -d "${VENV_DIR}" ]]; then
  printf 'Creating repository-local virtual environment at %s\n' "${VENV_DIR}" >&2
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
else
  printf 'Reusing repository-local virtual environment at %s\n' "${VENV_DIR}" >&2
fi

"${VENV_DIR}/bin/python" - <<'PY' \
  || fail "the existing .venv is not Python 3.11, 3.12, or 3.13; move it aside and rerun setup"
import sys

if not ((3, 11) <= sys.version_info < (3, 14)):
    raise SystemExit(1)
PY

export PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_NO_CACHE_DIR=1
"${VENV_DIR}/bin/python" -m pip install --upgrade "${REPO_ROOT}[dev]"

"${VENV_DIR}/bin/python" - "${REPO_ROOT}/pyproject.toml" <<'PY' \
  || fail "installed package code and metadata do not match pyproject.toml; recreate .venv"
from importlib.metadata import version
from pathlib import Path
import sys
import tomllib

import evidence_state_io


expected = tomllib.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["project"][
    "version"
]
observed = {
    "module": evidence_state_io.__version__,
    "metadata": version("evidence-state-io"),
}
if set(observed.values()) != {expected}:
    raise SystemExit(
        f"expected {expected!r}, observed module={observed['module']!r} "
        f"metadata={observed['metadata']!r}"
    )
PY

[[ -x "${VENV_DIR}/bin/evidence-state" ]] \
  || fail "installation completed without the evidence-state console entry point"

"${VENV_DIR}/bin/evidence-state" --help >/dev/null \
  || fail "the evidence-state console entry point was installed but cannot import the package"

printf '\nSetup complete. Next commands:\n' >&2
printf '  source %q\n' "${VENV_DIR}/bin/activate" >&2
printf '  ./scripts/test.sh\n' >&2
printf '  ./scripts/demo.sh\n' >&2
