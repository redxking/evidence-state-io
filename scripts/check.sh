#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
VENV_PYTHON="${REPO_ROOT}/.venv/bin/python"
CLI="${REPO_ROOT}/.venv/bin/evidence-state"

fail() {
  printf 'check: %s\n' "$*" >&2
  exit 1
}

[[ -x "${VENV_PYTHON}" ]] \
  || fail "repository-local environment not found; run ./scripts/setup.sh first"

cd -- "${REPO_ROOT}"
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_NO_CACHE_DIR=1
export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

for script in "${REPO_ROOT}"/scripts/*.sh; do
  bash -n "${script}"
done

command -v node >/dev/null 2>&1 \
  || fail "Node.js is required to validate the browser dashboard"
node "${REPO_ROOT}/tests/test_dashboard.js" \
  || fail "dashboard lossless/safe-render regression failed"

TEMP_CACHE="$(mktemp -d "${TMPDIR:-/tmp}/evidence-state-io-pyc.XXXXXX")"
cleanup() {
  case "${TEMP_CACHE}" in
    "${TMPDIR:-/tmp}"/evidence-state-io-pyc.*) rm -rf -- "${TEMP_CACHE}" ;;
    *) printf 'check: refusing to remove unexpected temporary path %s\n' "${TEMP_CACHE}" >&2 ;;
  esac
}
trap cleanup EXIT

PYTHONPYCACHEPREFIX="${TEMP_CACHE}" \
  "${VENV_PYTHON}" -m compileall -q -f "${REPO_ROOT}/src"
"${VENV_PYTHON}" -m pip check

"${VENV_PYTHON}" - "${REPO_ROOT}" <<'PY' \
  || fail "one or more local Markdown links do not resolve"
from __future__ import annotations

from pathlib import Path
import re
import sys
from urllib.parse import unquote


root = Path(sys.argv[1]).resolve()
markdown_files = sorted(root.glob("*.md")) + sorted((root / "docs").rglob("*.md"))
link_pattern = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
failures: list[str] = []

for document in markdown_files:
    text = document.read_text(encoding="utf-8")
    for raw_target in link_pattern.findall(text):
        target = raw_target.strip()
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1]
        target = target.split("#", 1)[0]
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        destination = (document.parent / unquote(target)).resolve()
        try:
            destination.relative_to(root)
        except ValueError:
            failures.append(f"{document.relative_to(root)}: link escapes repository: {raw_target}")
            continue
        if not destination.exists():
            failures.append(f"{document.relative_to(root)}: missing target: {raw_target}")

if failures:
    raise SystemExit("\n".join(failures))
PY

# Exercise the installed copy without the development source overlay.  The
# package snapshot check detects stale code even when a deterministic happy-
# path demo happens to remain unchanged.
env -u PYTHONPATH "${VENV_PYTHON}" - "${REPO_ROOT}/src/evidence_state_io" <<'PY' \
  || fail "installed package differs from the current source; rerun ./scripts/setup.sh"
from __future__ import annotations

from hashlib import sha256
from importlib.util import find_spec
from pathlib import Path
import sys


def snapshot(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        result[path.relative_to(root).as_posix()] = sha256(path.read_bytes()).hexdigest()
    return result


source = Path(sys.argv[1]).resolve()
spec = find_spec("evidence_state_io")
if spec is None or spec.origin is None:
    raise SystemExit("installed evidence_state_io package was not found")
installed = Path(spec.origin).resolve().parent
if snapshot(source) != snapshot(installed):
    raise SystemExit("source and installed package file snapshots differ")
PY

SOURCE_BENCHMARK="$("${VENV_PYTHON}" -m evidence_state_io demo --all)"
INSTALLED_BENCHMARK="$(env -u PYTHONPATH "${CLI}" demo --all)"
[[ "${SOURCE_BENCHMARK}" == "${INSTALLED_BENCHMARK}" ]] \
  || fail "installed package or EmptyBench result differs from the current source; rerun ./scripts/setup.sh"
env -u PYTHONPATH "${CLI}" --help >/dev/null

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  docker compose \
    --project-name evidence-state-io-lab \
    --file "${REPO_ROOT}/compose.yaml" \
    --profile lab \
    config --quiet
else
  printf 'check: Docker Compose unavailable; skipped optional compose validation\n' >&2
fi

printf 'Static checks passed.\n' >&2
