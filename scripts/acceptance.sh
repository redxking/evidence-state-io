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

# The MCP server is a transport, and the property it must not break is the
# one the project rests on: the same input produces the same decision, and
# the decision is the library's.  Replay a fixed frame sequence through the
# installed server from inside and outside a checkout, then check the
# assessment against a decision computed directly from the library.
"${WHEEL_VENV}/bin/python" - > "${ACCEPTANCE_TEMP}/mcp-frames.jsonl" <<'PY'
import json

from evidence_state_io.emptybench import seed_case_dicts, seed_profile_context

context = seed_profile_context().to_dict()
request = seed_case_dicts()[0]["request"]
frames = [
    {"jsonrpc": "2.0", "id": 1, "method": "server/discover"},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "describe_evidence_requirements", "arguments": {}},
    },
    {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "assess_negative_claim",
            "arguments": {
                "request": request,
                "registry_snapshot": context["registry_snapshot"],
                "trust_selection": context["trust_selection"],
            },
        },
    },
]
for frame in frames:
    print(json.dumps(frame, sort_keys=True))
PY

( cd "${ISOLATED}"
  env -u PYTHONPATH "${WHEEL_VENV}/bin/evidence-state-mcp" < "${ACCEPTANCE_TEMP}/mcp-frames.jsonl"
) > "${ACCEPTANCE_TEMP}/mcp-isolated.jsonl"
env -u PYTHONPATH "${WHEEL_VENV}/bin/evidence-state-mcp" < "${ACCEPTANCE_TEMP}/mcp-frames.jsonl" \
  > "${ACCEPTANCE_TEMP}/mcp-from-repo.jsonl"
cmp -s "${ACCEPTANCE_TEMP}/mcp-isolated.jsonl" "${ACCEPTANCE_TEMP}/mcp-from-repo.jsonl" \
  || fail "installed MCP server output depends on the working directory"

"${FRESH_VENV}/bin/python" - "${ACCEPTANCE_TEMP}/mcp-isolated.jsonl" <<'PY'
import json
import sys

from evidence_state_io.emptybench import seed_case_dicts, seed_profile_context
from evidence_state_io.gate import NegativeClaimRequest, evaluate_negative_claim

with open(sys.argv[1], encoding="utf-8") as handle:
    responses = {
        json.loads(line)["id"]: json.loads(line) for line in handle if line.strip()
    }

if sorted(responses) != [1, 2, 3, 4]:
    raise SystemExit(f"MCP server did not answer every request: {sorted(responses)}")

discover = responses[1]["result"]
if not discover["protocolVersions"] or "tools" not in discover["capabilities"]:
    raise SystemExit("MCP server advertised no protocol version or no tools capability")

listed = [tool["name"] for tool in responses[2]["result"]["tools"]]
expected_tools = ["assess_negative_claim", "explain_rejection", "describe_evidence_requirements"]
if listed != expected_tools:
    raise SystemExit(f"unexpected MCP tool list: {listed}")

for identifier in (3, 4):
    if responses[identifier]["result"]["isError"]:
        raise SystemExit(f"MCP tool call {identifier} returned an error")

served = responses[4]["result"]["structuredContent"]
expected = evaluate_negative_claim(
    NegativeClaimRequest.from_dict(seed_case_dicts()[0]["request"]),
    seed_profile_context(),
).to_dict()
if served != expected:
    raise SystemExit("MCP server decision differs from the library decision")
if served["decision"] != "PERMIT_SCOPED_NEGATIVE":
    raise SystemExit(f"unexpected seed decision through MCP: {served['decision']}")

if json.loads(responses[4]["result"]["content"][0]["text"]) != served:
    raise SystemExit("MCP text content differs from its structured content")

print(json.dumps({"mcp_server": {"tools": expected_tools, "decision_matches_library": True}, "status": "PASS"}, sort_keys=True))
PY
printf 'MVP local acceptance gate passed at %s.\n' "$(git rev-parse HEAD)"
