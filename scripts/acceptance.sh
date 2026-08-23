#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"

fail() {
  printf 'acceptance: %s\n' "$*" >&2
  exit 1
}

command -v "${PYTHON_BIN}" >/dev/null 2>&1 \
  || fail "${PYTHON_BIN} is unavailable"

cd -- "${REPO_ROOT}"
if [[ "${ESIO_ALLOW_DIRTY:-0}" != "1" ]] && [[ -n "$(git status --porcelain)" ]]; then
  fail "the acceptance worktree must be clean; use ESIO_ALLOW_DIRTY=1 only for development"
fi

ACCEPTANCE_TEMP="$(mktemp -d "${TMPDIR:-/tmp}/esio-acceptance.XXXXXX")"
cleanup_acceptance() {
  case "${ACCEPTANCE_TEMP}" in
    "${TMPDIR:-/tmp}"/esio-acceptance.*) rm -rf -- "${ACCEPTANCE_TEMP}" ;;
    *) printf 'acceptance: refusing to remove unexpected path %s\n' "${ACCEPTANCE_TEMP}" >&2 ;;
  esac
}
trap cleanup_acceptance EXIT

FRESH_VENV="${ACCEPTANCE_TEMP}/fresh"
WHEEL_VENV="${ACCEPTANCE_TEMP}/wheel"
DIST_DIR="${ACCEPTANCE_TEMP}/dist"
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_NO_CACHE_DIR=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHONHASHSEED=0

"${PYTHON_BIN}" -m venv "${FRESH_VENV}"
"${FRESH_VENV}/bin/python" -m pip install ".[dev]"

env -u PYTHONPATH "${FRESH_VENV}/bin/ruff" check src tests
env -u PYTHONPATH "${FRESH_VENV}/bin/ruff" format --check src tests
env -u PYTHONPATH "${FRESH_VENV}/bin/mypy" src/evidence_state_io
env -u PYTHONPATH "${FRESH_VENV}/bin/coverage" erase
env -u PYTHONPATH "${FRESH_VENV}/bin/coverage" run --branch -m pytest -p no:cacheprovider -q
env -u PYTHONPATH "${FRESH_VENV}/bin/coverage" report --fail-under=90

for runtime in python3.11 python3.12 python3.13; do
  command -v "${runtime}" >/dev/null 2>&1 || fail "${runtime} is unavailable"
  PYTHONPATH=src "${runtime}" -m unittest discover -s tests -q
done

node tests/test_dashboard.js
PYTHONPATH=src "${FRESH_VENV}/bin/python" scripts/build_site.py --output .site-build
node tests/test_site_demo.js
"${FRESH_VENV}/bin/python" scripts/public_release_gate.py --repo .
env -u PYTHONPATH ./scripts/check.sh

mkdir -p "${DIST_DIR}"
env -u PYTHONPATH "${FRESH_VENV}/bin/python" -m build --outdir "${DIST_DIR}"
wheels=("${DIST_DIR}"/*.whl)
[[ ${#wheels[@]} -eq 1 && -f "${wheels[0]}" ]] \
  || fail "expected exactly one built wheel"

"${PYTHON_BIN}" -m venv "${WHEEL_VENV}"
"${WHEEL_VENV}/bin/python" -m pip install "${wheels[0]}"
env -u PYTHONPATH "${WHEEL_VENV}/bin/python" -m unittest discover -s tests -q

# The installed distribution must behave identically outside a checkout.  Run
# it from a directory that is not the repository, and plant a decoy artifact
# directory beside the caller so a working-directory search cannot satisfy it.
ISOLATED="${ACCEPTANCE_TEMP}/isolated"
mkdir -p "${ISOLATED}/benchmarks"
for artifact in emptybench-p0-corpus emptybench-p0-oracle \
  emptybench-p1-composed-corpus emptybench-p1-composed-oracle; do
  printf '{"not": "a benchmark artifact"}\n' > "${ISOLATED}/benchmarks/${artifact}.json"
done
(
  cd "${ISOLATED}"
  env -u PYTHONPATH "${WHEEL_VENV}/bin/evidence-state" --help >/dev/null
  env -u PYTHONPATH "${WHEEL_VENV}/bin/evidence-state" demo >/dev/null
  env -u PYTHONPATH "${WHEEL_VENV}/bin/evidence-state" demo --all --pretty
) > "${ACCEPTANCE_TEMP}/emptybench.json"

env -u PYTHONPATH "${WHEEL_VENV}/bin/evidence-state" demo --all --pretty \
  > "${ACCEPTANCE_TEMP}/emptybench-from-repo.json"
cmp -s "${ACCEPTANCE_TEMP}/emptybench.json" "${ACCEPTANCE_TEMP}/emptybench-from-repo.json" \
  || fail "installed benchmark output depends on the working directory"

# The composed benchmark is what measures whether the gate discriminates
# multi-source evidence, so it is held to the same isolation requirement.
( cd "${ISOLATED}"
  env -u PYTHONPATH "${WHEEL_VENV}/bin/evidence-state" demo --benchmark composed --all --pretty
) > "${ACCEPTANCE_TEMP}/emptybench-composed.json"
env -u PYTHONPATH "${WHEEL_VENV}/bin/evidence-state" demo --benchmark composed --all --pretty \
  > "${ACCEPTANCE_TEMP}/emptybench-composed-from-repo.json"
cmp -s "${ACCEPTANCE_TEMP}/emptybench-composed.json" \
  "${ACCEPTANCE_TEMP}/emptybench-composed-from-repo.json" \
  || fail "installed composed benchmark output depends on the working directory"

"${FRESH_VENV}/bin/python" - "${ACCEPTANCE_TEMP}/emptybench.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
summary = report["summary"]
expected = {
    "all_passed": True,
    "false_rejections": 0,
    "pairs_discriminated": 12,
    "pairs_total": 12,
    "passed": 24,
    "total": 24,
    "unsafe_permits": 0,
}
if any(summary.get(key) != value for key, value in expected.items()):
    raise SystemExit(f"unexpected EmptyBench summary: {summary}")
print(json.dumps({"emptybench": expected, "status": "PASS"}, sort_keys=True))
PY

"${FRESH_VENV}/bin/python" - "${ACCEPTANCE_TEMP}/emptybench-composed.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
summary = report["summary"]
expected = {
    "all_passed": True,
    "false_rejections": 0,
    "pairs_discriminated": 6,
    "pairs_total": 6,
    "passed": 12,
    "total": 12,
    "unsafe_permits": 0,
}
if any(summary.get(key) != value for key, value in expected.items()):
    raise SystemExit(f"unexpected composed EmptyBench summary: {summary}")
print(json.dumps({"emptybench_composed": expected, "status": "PASS"}, sort_keys=True))
PY

printf 'MVP local acceptance gate passed at %s.\n' "$(git rev-parse HEAD)"
