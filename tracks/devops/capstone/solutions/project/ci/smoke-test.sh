#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $(basename "$0") <base-url> <expected-version>" >&2
  echo "  SMOKE_TIMEOUT: số giây chờ tối đa (mặc định 60)" >&2
  exit 2
}

[[ $# -eq 2 && -n "$1" && -n "$2" ]] || usage
base="${1%/}"
expected="$2"
timeout="${SMOKE_TIMEOUT:-60}"
[[ "$timeout" =~ ^[0-9]+$ ]] || usage

probe() {
  local path="$1" body status
  body="$(curl -sS --max-time 3 -w '\n%{http_code}' "$base$path" 2>/dev/null)" || return 1
  status="${body##*$'\n'}"
  printf '%s\n%s' "$status" "${body%$'\n'*}"
}

reason="chưa gọi được $base"
deadline=$((SECONDS + timeout))
while :; do
  if health="$(probe /healthz)"; then
    status="${health%%$'\n'*}"
    version="$(jq -r '.version // empty' <<<"${health#*$'\n'}" 2>/dev/null || true)"
    if [[ "$status" != 200 ]]; then
      reason="healthz=$status"
    elif [[ "$version" != "$expected" ]]; then
      reason="version=${version:-?} expected=$expected"
    elif ready="$(probe /readyz)" && [[ "${ready%%$'\n'*}" == 200 ]]; then
      echo "OK version=$version url=$base"
      exit 0
    else
      reason="readyz=${ready%%$'\n'*} version=$version"
    fi
  else
    reason="không kết nối được $base"
  fi
  if (( SECONDS >= deadline )); then
    echo "FAIL $reason sau ${timeout}s" >&2
    exit 1
  fi
  sleep 1
done
