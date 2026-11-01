#!/usr/bin/env bash
set -uo pipefail

usage() {
  echo "Usage: $0 [-n lần_thử] [-d giây_đầu] [-m giây_tối_đa] [-r mã,mã] [-j] [--] lệnh [tham số...]" >&2
  exit 64
}

attempts=5
base=1
max_delay=30
codes="6,7,28,75"
jitter=0
sleep_cmd="${RETRY_SLEEP_CMD:-sleep}"

while getopts ":n:d:m:r:j" opt; do
  case "$opt" in
    n) attempts="$OPTARG" ;;
    d) base="$OPTARG" ;;
    m) max_delay="$OPTARG" ;;
    r) codes="$OPTARG" ;;
    j) jitter=1 ;;
    *) usage ;;
  esac
done
shift $((OPTIND - 1))
(($# > 0)) || usage
[[ "$attempts" =~ ^[1-9][0-9]*$ ]] || usage
[[ "$base" =~ ^[0-9]+$ && "$max_delay" =~ ^[0-9]+$ ]] || usage
[[ "$codes" =~ ^[0-9]+(,[0-9]+)*$ ]] || usage

retryable() {
  [[ ",$codes," == *",$1,"* ]]
}

delay=$((base < max_delay ? base : max_delay))
for ((attempt = 1; ; attempt++)); do
  "$@"
  rc=$?
  ((rc == 0)) && exit 0
  if ! retryable "$rc"; then
    echo "retry: exit $rc is not retryable" >&2
    exit "$rc"
  fi
  if ((attempt >= attempts)); then
    echo "retry: giving up after $attempts attempts (exit $rc)" >&2
    exit "$rc"
  fi
  wait_for=$delay
  ((jitter)) && wait_for=$((RANDOM % (delay + 1)))
  echo "retry: attempt $attempt/$attempts exited $rc; sleeping ${wait_for}s" >&2
  "$sleep_cmd" "$wait_for"
  delay=$((delay * 2 < max_delay ? delay * 2 : max_delay))
done
