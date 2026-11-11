#!/bin/sh
# quillo-support 1.0: support bundle của quillo (đội sản phẩm phát hành kèm bundle cài đặt).
# Khách chạy trong thư mục cài quillo bằng user vận hành (không cần root): sh quillo-support.sh > bundle.tar.gz
# Bundle được dựng trong /dev/shm và ghi ra stdout: không để lại tệp nào trên máy khách.
set -u

work=$(mktemp -d "${QUILLO_SUPPORT_TMP:-/dev/shm}/quillo-support.XXXXXX") || exit 1
trap 'rm -rf "$work"' EXIT
trap 'exit 130' INT TERM HUP
root=quillo-support-$(hostname)-$(date -u +%Y%m%dT%H%M%SZ)
dir=$work/$root
mkdir -p "$dir/system" "$dir/network" "$dir/quillo/logs"
: >"$dir/errors.txt"

redact() {
    sed -E \
        -e 's#([A-Za-z][A-Za-z0-9+.-]*://[^/:@[:space:]]*):[^@/[:space:]]*@#\1:***@#g' \
        -e 's#(Authorization:[[:space:]]*(Bearer|Basic|Token|Negotiate))[[:space:]]+[^[:space:]"]+#\1 ***#Ig' \
        -e 's#([A-Za-z0-9_.-]*(password|passwd|secret|token|api_key|private_key)[A-Za-z0-9_.-]*[[:space:]]*[=:][[:space:]]*"?)[^"[:space:],;]+#\1***#Ig'
}

collect() {
    target=$1
    shift
    "$@" >"$work/raw" 2>&1
    rc=$?
    [ "$rc" -eq 0 ] || printf '%s: "%s" thoát %s\n' "$target" "$*" "$rc" >>"$dir/errors.txt"
    redact <"$work/raw" >"$dir/$target"
    rm -f "$work/raw"
}

healthz() {
    curl -sS --noproxy '*' -m 10 -w '\nHTTP %{http_code}\n' "http://127.0.0.1:${QUILLO_PORT:-18080}/healthz"
}

env_file() {
    [ -f .env ] && sed -E 's/^([A-Za-z_][A-Za-z0-9_]*(PASSWORD|TOKEN|SECRET)[A-Za-z0-9_]*)=.*/\1=***/' .env
}

printf 'quillo-support 1.0\ncollected_utc=%s\nhost=%s\ncwd=%s\nuser=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    "$(hostname)" "$(pwd)" "$(id -un)" >"$dir/meta.txt"
collect system/os-release cat /etc/os-release
collect system/uname.txt uname -a
collect system/uptime.txt uptime
collect system/df.txt df -h
collect system/df-inodes.txt df -i
collect system/memory.txt free -m
collect system/environment.txt cat /etc/environment
collect network/ip.txt ip addr
collect network/route.txt ip route
collect network/listen.txt ss -ltn
collect network/resolv.conf cat /etc/resolv.conf
collect quillo/env.txt env_file
collect quillo/compose-ps.txt docker compose ps -a
collect quillo/images.txt docker compose images
collect quillo/healthz.txt healthz
collect quillo/docker-info.txt docker info
for service in api worker db llm embed; do
    collect "quillo/logs/$service.log" docker compose logs --no-color --tail 400 "$service"
done
tar -C "$work" -czf - "$root"
