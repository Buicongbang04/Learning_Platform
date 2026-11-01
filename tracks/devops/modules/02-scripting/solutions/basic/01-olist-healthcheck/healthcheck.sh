#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 [-u base_url] [-t timeout_giây]" >&2
  exit 3
}

base_url="${OLIST_SHOP_API_URL:-http://localhost:${OLIST_SHOP_API_PORT:-28000}}"
timeout=3

while getopts ":u:t:" opt; do
  case "$opt" in
    u) base_url="$OPTARG" ;;
    t) timeout="$OPTARG" ;;
    *) usage ;;
  esac
done
shift $((OPTIND - 1))
[[ $# -eq 0 ]] || usage
[[ "$timeout" =~ ^[1-9][0-9]*$ ]] || usage
base_url="${base_url%/}"

body_file="$(mktemp)"
trap 'rm -f "$body_file"' EXIT

fetch() {
  local rc=0
  code="$(curl -sS --max-time "$timeout" -o "$body_file" -w '%{http_code}' "$base_url$1" 2>/dev/null)" || rc=$?
  if ((rc != 0)); then
    echo "CRITICAL - api unreachable (curl exit $rc)"
    exit 2
  fi
}

fetch /healthz
if [[ "$code" != 200 ]]; then
  echo "CRITICAL - healthz=$code"
  exit 2
fi

fetch /readyz
unknown() {
  echo "UNKNOWN - unexpected readyz response (status $code)"
  exit 3
}
[[ "$code" == 200 || "$code" == 503 ]] || unknown
fields="$(jq -r 'select(type == "object") | "\(.db) \(.redis)"' "$body_file" 2>/dev/null)" || unknown
read -r db redis <<<"$fields" || unknown
[[ "$db" =~ ^(ok|error)$ && "$redis" =~ ^(ok|error)$ ]] || unknown

summary="healthz=200 readyz=$code db=$db redis=$redis"
if [[ "$code" == 200 && "$db" == ok && "$redis" == ok ]]; then
  echo "OK - $summary"
  exit 0
fi
[[ "$code" == 503 ]] || unknown
if [[ "$db" == error ]]; then
  echo "CRITICAL - $summary"
  exit 2
fi
[[ "$redis" == error ]] || unknown
echo "WARNING - $summary"
exit 1
