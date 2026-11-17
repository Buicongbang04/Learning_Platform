#!/bin/sh
set -u

out=${1:?"cách dùng: sh support_bundle.sh <tệp ra .tar.gz>"}
case $out in
    /*) ;;
    *) out=$(pwd)/$out ;;
esac
umask 077
work=$(mktemp -d "${TMPDIR:-/tmp}/support-bundle.XXXXXX") || { echo "không tạo được thư mục tạm" >&2; exit 1; }
trap 'rm -rf "$work"' EXIT
trap 'exit 130' INT TERM HUP
root=support-$(hostname)-$(date -u +%Y%m%dT%H%M%SZ)
dir=$work/$root
mkdir -p "$dir/system" "$dir/network" "$dir/docbridge" "$dir/docker"
: >"$dir/errors.txt"

redact() {
    sed -E \
        -e 's#([A-Za-z][A-Za-z0-9+.-]*://[^/:@[:space:]]*):[^@/[:space:]]*@#\1:***@#g' \
        -e 's#(Authorization:[[:space:]]*(Bearer|Basic|Token|Negotiate))[[:space:]]+[^[:space:]"]+#\1 ***#Ig' \
        -e 's#([A-Za-z0-9_.-]*(password|passwd|pwd|secret|token|apikey|api_key|private_key|credential)[A-Za-z0-9_.-]*[[:space:]]*[=:][[:space:]]*"?)[^"[:space:],;]+#\1***#Ig'
}

collect() {
    target=$1
    shift
    "$@" >"$work/raw" 2>&1
    rc=$?
    if [ "$rc" -ne 0 ]; then
        printf '%s: "%s" thoát %s: %s\n' "$target" "$*" "$rc" "$(head -c 300 "$work/raw" | tr '\n' ' ')" \
            | redact >>"$dir/errors.txt"
    fi
    redact <"$work/raw" >"$dir/$target"
    rm -f "$work/raw"
}

app_log() {
    tail -n 5000 /var/log/docbridge/docbridge.log | tail -c 1900000
}

collect system/os-release cat /etc/os-release
collect system/uname.txt uname -a
collect system/df.txt df -h
collect system/memory.txt free -m
collect system/uptime.txt uptime
collect network/listen.txt ss -ltn
collect network/ip.txt ip addr
collect docbridge/status.txt systemctl status --no-pager --lines 20 docbridge
collect docbridge/journal.txt journalctl -u docbridge -n 500 --no-pager
collect docbridge/docbridge.conf cat /etc/docbridge/docbridge.conf
collect docbridge/docbridge.log app_log
collect docker/ps.txt docker ps -a
collect docker/docbridge-cache.log docker logs --tail 500 docbridge-cache
collect docker/docbridge-cache.json docker inspect docbridge-cache

part=$out.part
if ! tar -C "$work" -czf "$part" "$root"; then
    rm -f "$part"
    echo "không ghi được $out" >&2
    exit 1
fi
mv -f "$part" "$out"
echo "đã ghi $out ($(wc -c <"$out") byte)"
