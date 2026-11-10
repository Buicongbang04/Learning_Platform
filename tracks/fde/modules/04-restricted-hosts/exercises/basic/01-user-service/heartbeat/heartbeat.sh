#!/bin/sh
set -eu

conf=${HEARTBEAT_CONF:-$HOME/.config/heartbeat/heartbeat.env}
state=${XDG_STATE_HOME:-$HOME/.local/state}/heartbeat

[ -r "$conf" ] || { echo "heartbeat: không đọc được $conf" >&2; exit 1; }
token=$(sed -n 's/^TOKEN=//p' "$conf" | head -n 1)
interval=$(sed -n 's/^INTERVAL=//p' "$conf" | head -n 1)
[ -n "$token" ] || { echo "heartbeat: thiếu TOKEN trong $conf" >&2; exit 1; }
case $interval in
    '' | *[!0-9]*) interval=2 ;;
esac

mkdir -p "$state"
echo "heartbeat: pid $$, token $token, mỗi ${interval}s ghi vào $state/beats.log" >&2
while :; do
    printf '%s %s %s\n' "$(date +%s)" "$$" "$token" >> "$state/beats.log"
    sleep "$interval"
done
