#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <pid> [timeout_giây]" >&2
  exit 2
}

[[ $# -ge 1 && $# -le 2 ]] || usage
pid="$1"
timeout="${2:-10}"
[[ "$pid" =~ ^[0-9]+$ ]] || usage
(( pid > 1 )) || usage
[[ "$timeout" =~ ^[0-9]+$ ]] || usage

alive() {
  local state
  state="$(ps -o stat= -p "$pid" 2>/dev/null)" || return 1
  [[ -n "$state" && "$state" != Z* ]]
}

wait_gone() {
  local ticks=$(( $1 * 10 ))
  while alive; do
    (( ticks-- > 0 )) || return 1
    sleep 0.1
  done
}

if ! ps -p "$pid" >/dev/null 2>&1; then
  echo "Không có tiến trình $pid" >&2
  exit 1
fi
if ! kill -0 "$pid" 2>/dev/null; then
  echo "Không có quyền gửi signal tới $pid (tiến trình của user khác?)" >&2
  exit 4
fi

kill -TERM "$pid" 2>/dev/null || true
if wait_gone "$timeout"; then
  echo "stopped $pid SIGTERM"
  exit 0
fi

echo "Tiến trình $pid không dừng sau ${timeout}s, gửi SIGKILL" >&2
kill -KILL "$pid" 2>/dev/null || true
if wait_gone 5; then
  echo "killed $pid SIGKILL"
  exit 3
fi
echo "Tiến trình $pid vẫn còn sau SIGKILL (trạng thái D, chờ I/O của kernel?)" >&2
exit 5
