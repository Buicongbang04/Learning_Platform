#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage: log_report.sh <lệnh> [tham số] <tệp log | ->
  status <log>                 số request theo status code
  top-ips <N> <log>            N IP gửi nhiều request nhất
  errors <log>                 số request 5xx theo path (bỏ query string)
  slow <giây> <log>            request có request_time >= ngưỡng
  per-minute <log>             mỗi phút: tổng request và số 5xx
  upstream-errors <jsonl>      số lần upstream trả 5xx, đếm cả lần retry (dùng jq)
USAGE
  exit 2
}

input() {
  # TODO 1: "-" là stdin; tệp không tồn tại thì báo lỗi ra stderr, exit 1
  cat "$1"
}

cmd_status() {
  # TODO 2
  echo "TODO" >&2
  exit 99
}

cmd_top_ips() {
  # TODO 3
  echo "TODO" >&2
  exit 99
}

cmd_errors() {
  # TODO 4
  echo "TODO" >&2
  exit 99
}

cmd_slow() {
  # TODO 5
  echo "TODO" >&2
  exit 99
}

cmd_per_minute() {
  # TODO 6
  echo "TODO" >&2
  exit 99
}

cmd_upstream_errors() {
  # TODO 7
  echo "TODO" >&2
  exit 99
}

[[ $# -ge 1 ]] || usage
command="$1"
shift
case "$command" in
  status) [[ $# -eq 1 ]] || usage; input "$1" | cmd_status ;;
  top-ips) [[ $# -eq 2 ]] || usage; input "$2" | cmd_top_ips "$1" ;;
  errors) [[ $# -eq 1 ]] || usage; input "$1" | cmd_errors ;;
  slow) [[ $# -eq 2 ]] || usage; input "$2" | cmd_slow "$1" ;;
  per-minute) [[ $# -eq 1 ]] || usage; input "$1" | cmd_per_minute ;;
  upstream-errors) [[ $# -eq 1 ]] || usage; input "$1" | cmd_upstream_errors ;;
  *) usage ;;
esac
