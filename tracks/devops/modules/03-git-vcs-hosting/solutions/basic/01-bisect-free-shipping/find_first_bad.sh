#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <good-ref> <bad-ref>" >&2
  exit 2
}

[[ $# -eq 2 ]] || usage
good=$1
bad=$2
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

cleanup() {
  git bisect reset >/dev/null 2>&1 || true
}
trap cleanup EXIT

if ! git bisect start "$bad" "$good" >&2; then
  echo "error: không bắt đầu được bisect với good=$good bad=$bad" >&2
  exit 1
fi

if ! git bisect run bash "$here/check_free_shipping.sh" >&2; then
  echo "error: bisect không kết luận được, xem git bisect log" >&2
  exit 1
fi

first_bad=$(git rev-parse --verify --quiet refs/bisect/bad) || {
  echo "error: không có refs/bisect/bad" >&2
  exit 1
}
echo "first-bad $first_bad"
