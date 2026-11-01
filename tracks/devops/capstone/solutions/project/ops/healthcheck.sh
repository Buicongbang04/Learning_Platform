#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 [-u base_url] [-t timeout_giây] [-w chờ_tối_đa_giây]" >&2
  exit 2
}

base_url="${OLIST_SHOP_API_URL:-http://127.0.0.1:${OLIST_SHOP_API_PORT:-28000}}"
timeout=3
wait_max=0

while getopts ":u:t:w:" opt; do
  case "$opt" in
    u) base_url="$OPTARG" ;;
    t) timeout="$OPTARG" ;;
    w) wait_max="$OPTARG" ;;
    *) usage ;;
  esac
done
shift $((OPTIND - 1))
[[ $# -eq 0 && -n "$base_url" ]] || usage
[[ "$timeout" =~ ^[1-9][0-9]*$ && "$wait_max" =~ ^[0-9]+$ ]] || usage
base_url="${base_url%/}"

body_file="$(mktemp)"
trap 'rm -f -- "$body_file"' EXIT
result=""

check_once() {
  local code rc=0 fields db redis
  local -a failing=()
  code="$(curl -s --max-time "$timeout" -o "$body_file" -w '%{http_code}' -- "$base_url/readyz")" || rc=$?
  if ((rc != 0)); then
    result="FAIL api unreachable (curl exit $rc)"
    return 1
  fi
  result="FAIL readyz=$code unexpected response"
  fields="$(jq -r 'select(type == "object") | "\(.db) \(.redis)"' "$body_file" 2>/dev/null)" || return 1
  read -r db redis <<<"$fields" || return 1
  [[ "$db" =~ ^(ok|error)$ && "$redis" =~ ^(ok|error)$ ]] || return 1
  if [[ "$code" == 200 && "$db" == ok && "$redis" == ok ]]; then
    result="OK db=ok redis=ok"
    return 0
  fi
  [[ "$code" == 503 ]] || return 1
  [[ "$db" == error ]] && failing+=(db)
  [[ "$redis" == error ]] && failing+=(redis)
  ((${#failing[@]} > 0)) || return 1
  result="FAIL readyz=503 failing=$(IFS=,; echo "${failing[*]}")"
  return 1
}

deadline=$((SECONDS + wait_max))
until check_once; do
  if ((SECONDS >= deadline)); then
    echo "$result"
    exit 1
  fi
  sleep 1
done
echo "$result"
