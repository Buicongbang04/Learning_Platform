#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C

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
  if [[ "$1" == "-" ]]; then
    cat
  elif [[ -r "$1" ]]; then
    cat -- "$1"
  else
    echo "Không đọc được tệp: $1" >&2
    exit 1
  fi
}

fields() {
  awk -F'"' '
    {
      split($3, sb, " ")
      n = split($2, req, " ")
      path = (n == 3) ? req[2] : ""
      sub(/\?.*/, "", path)
      rt = $NF
      sub(/^.*rt=/, "", rt)
      match($1, /\[[^]]+\]/)
      minute = substr($1, RSTART + 13, 5)
      split($1, head, " ")
      print head[1], sb[1], path == "" ? "-" : path, rt, minute
    }'
}

cmd_status() {
  fields | awk '{ print $2 }' | sort | uniq -c | awk '{ print $2, $1 }' | sort -k1,1n
}

cmd_top_ips() {
  fields | awk '{ print $1 }' | sort | uniq -c | sort -k1,1nr -k2,2 | head -n "$1" | awk '{ print $1, $2 }'
}

cmd_errors() {
  fields | awk '$2 ~ /^5/ && $3 != "-" { print $3 }' | sort | uniq -c | sort -k1,1nr -k2,2 | awk '{ print $1, $2 }'
}

cmd_slow() {
  fields | awk -v t="$1" '$3 != "-" && $4 + 0 >= t + 0 { print $4, $2, $3 }' | sort -k1,1gr -k3,3
}

cmd_per_minute() {
  fields | awk '
    !($5 in total) { order[++n] = $5 }
    { total[$5]++; if ($2 ~ /^5/) errors[$5]++ }
    END { for (i = 1; i <= n; i++) print order[i], total[order[i]], errors[order[i]] + 0 }'
}

cmd_upstream_errors() {
  command -v jq >/dev/null || { echo "Cần jq" >&2; exit 1; }
  jq -r '
    [(.upstream_addr | split(", ")), (.upstream_status | split(", "))]
    | transpose[]
    | select(.[1] | startswith("5"))
    | .[0]' | sort | uniq -c | sort -k1,1nr -k2,2 | awk '{ print $1, $2 }'
}

[[ $# -ge 1 ]] || usage
command="$1"
shift
case "$command" in
  status) [[ $# -eq 1 ]] || usage; input "$1" | cmd_status ;;
  top-ips) [[ $# -eq 2 && "$1" =~ ^[0-9]+$ ]] || usage; input "$2" | cmd_top_ips "$1" ;;
  errors) [[ $# -eq 1 ]] || usage; input "$1" | cmd_errors ;;
  slow) [[ $# -eq 2 && "$1" =~ ^[0-9]+(\.[0-9]+)?$ ]] || usage; input "$2" | cmd_slow "$1" ;;
  per-minute) [[ $# -eq 1 ]] || usage; input "$1" | cmd_per_minute ;;
  upstream-errors) [[ $# -eq 1 ]] || usage; input "$1" | cmd_upstream_errors ;;
  *) usage ;;
esac
