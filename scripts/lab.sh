#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
PROJECT_NAME="evidence-state-io-lab"
ADMIN_PORT="${ESIO_LAB_TOXIPROXY_PORT:-58474}"
PROXY_NAME="source-db"
TOXIC_NAME="esio-fault"

usage() {
  cat >&2 <<'EOF'
Usage: ./scripts/lab.sh <up|status|latency|timeout|clear|down>

  up       Start the loopback-only synthetic Postgres and Toxiproxy lab.
  status   Show Compose and proxy status.
  latency  Add 1500 ms downstream latency with 250 ms jitter.
  timeout  Add a downstream timeout toxic.
  clear    Remove the fault created by this script.
  down     Stop containers and network; preserve the named data volume.
EOF
}

fail() {
  printf 'lab: %s\n' "$*" >&2
  exit 1
}

validate_port() {
  local value="$1"
  [[ "${value}" =~ ^[0-9]+$ ]] || fail "port must be numeric"
  ((value >= 1 && value <= 65535)) || fail "port must be between 1 and 65535"
}

validate_port "${ADMIN_PORT}"

command -v docker >/dev/null 2>&1 || fail "Docker is required for the optional lab"
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is required"
command -v curl >/dev/null 2>&1 || fail "curl is required to control the local fault proxy"

compose() {
  docker compose \
    --project-name "${PROJECT_NAME}" \
    --file "${REPO_ROOT}/compose.yaml" \
    --profile lab \
    "$@"
}

api_url() {
  printf 'http://127.0.0.1:%s%s' "${ADMIN_PORT}" "$1"
}

wait_for_proxy() {
  local attempt
  for attempt in $(seq 1 40); do
    if curl --silent --fail --max-time 1 "$(api_url /version)" >/dev/null; then
      return 0
    fi
    sleep 0.25
  done
  fail "local Toxiproxy API did not become ready"
}

ensure_proxy() {
  if curl --silent --fail --max-time 2 \
    "$(api_url "/proxies/${PROXY_NAME}")" >/dev/null; then
    return 0
  fi

  curl --silent --show-error --fail --max-time 5 \
    -X POST \
    -H 'Content-Type: application/json' \
    --data '{"name":"source-db","listen":"0.0.0.0:15432","upstream":"postgres:5432","enabled":true}' \
    "$(api_url /proxies)" >/dev/null
}

clear_fault() {
  local code
  code="$(curl --silent --output /dev/null --write-out '%{http_code}' --max-time 3 \
    -X DELETE "$(api_url "/proxies/${PROXY_NAME}/toxics/${TOXIC_NAME}")")"
  case "${code}" in
    204|404) return 0 ;;
    *) fail "failed to clear scripted toxic; local API returned HTTP ${code}" ;;
  esac
}

add_fault() {
  local payload="$1"
  wait_for_proxy
  ensure_proxy
  clear_fault
  curl --silent --show-error --fail --max-time 5 \
    -X POST \
    -H 'Content-Type: application/json' \
    --data "${payload}" \
    "$(api_url "/proxies/${PROXY_NAME}/toxics")" >/dev/null
}

action="${1:-}"
case "${action}" in
  up)
    compose up -d postgres toxiproxy
    wait_for_proxy
    ensure_proxy
    printf 'Lab is ready. Direct DB: 127.0.0.1:%s; proxied DB: 127.0.0.1:%s\n' \
      "${ESIO_LAB_POSTGRES_PORT:-55432}" "${ESIO_LAB_PROXY_PORT:-55433}" >&2
    ;;
  status)
    compose ps
    wait_for_proxy
    curl --silent --show-error --fail --max-time 3 \
      "$(api_url "/proxies/${PROXY_NAME}")"
    printf '\n'
    ;;
  latency)
    add_fault '{"name":"esio-fault","type":"latency","stream":"downstream","toxicity":1.0,"attributes":{"latency":1500,"jitter":250}}'
    printf 'Injected local downstream latency.\n' >&2
    ;;
  timeout)
    add_fault '{"name":"esio-fault","type":"timeout","stream":"downstream","toxicity":1.0,"attributes":{"timeout":1000}}'
    printf 'Injected local downstream timeout.\n' >&2
    ;;
  clear)
    wait_for_proxy
    ensure_proxy
    clear_fault
    printf 'Cleared the scripted local fault.\n' >&2
    ;;
  down)
    compose down
    printf 'Lab containers stopped; named Postgres volume was preserved.\n' >&2
    ;;
  *)
    usage
    exit 2
    ;;
esac
