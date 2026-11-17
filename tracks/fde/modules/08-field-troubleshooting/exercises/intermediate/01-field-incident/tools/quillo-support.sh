#!/bin/sh
# quillo-support 1.0: support bundle của quillo (đội sản phẩm phát hành kèm bundle cài đặt).
# Khách chạy trong thư mục cài quillo bằng user vận hành (không cần root): sh quillo-support.sh > bundle.tar.gz
# Bundle được dựng trong /dev/shm và ghi ra stdout: không để lại tệp nào trên máy khách.
# Secret quillo giữ trong thư mục cài là QUILLO_ADMIN_TOKEN và QUILLO_DB_PASSWORD (.env); client secret OIDC nằm trong
# oidc/ (không đọc). Công cụ thay đúng hai giá trị đó ở mọi tệp, và không thu nguồn nào ngoài sản phẩm có thể chứa secret
# của khách (biến môi trường, tệp cấu hình hệ thống).
set -u

dir=$(mktemp -d "${QUILLO_SUPPORT_TMP:-/dev/shm}/quillo-support.XXXXXX") || exit 1
trap 'rm -rf "$dir"' EXIT
trap 'exit 130' INT TERM HUP
root=quillo-support-$(hostname)-$(date -u +%Y%m%dT%H%M%SZ)
out=$dir/$root
mkdir -p "$out/system" "$out/network" "$out/quillo/logs"
: >"$out/errors.txt"

known() {
    [ -f .env ] && sed -n "s/^$1=//p" .env | head -n 1
}
token=$(known QUILLO_ADMIN_TOKEN)
password=$(known QUILLO_DB_PASSWORD)
[ -n "$token" ] || token=no-admin-token-$$
[ -n "$password" ] || password=no-db-password-$$

save() {
    target=$1
    shift
    "$@" >"$out/$target.raw" 2>&1 || echo "$target: $* thoát $?" >>"$out/errors.txt"
    sed -e "s/$token/<QUILLO_ADMIN_TOKEN>/g" -e "s/$password/<QUILLO_DB_PASSWORD>/g" \
        "$out/$target.raw" >"$out/$target"
    rm -f "$out/$target.raw"
}

env_file() {
    [ -f .env ] && sed -e 's/^QUILLO_ADMIN_TOKEN=.*/QUILLO_ADMIN_TOKEN=<đã che>/' \
        -e 's/^QUILLO_DB_PASSWORD=.*/QUILLO_DB_PASSWORD=<đã che>/' .env
}

healthz() {
    curl -sS --noproxy '*' -m 10 -w '\nHTTP %{http_code}\n' "http://127.0.0.1:${QUILLO_PORT:-18080}/healthz"
}

printf 'quillo-support 1.0\ncollected_utc=%s\nhost=%s\ncwd=%s\nuser=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    "$(hostname)" "$(pwd)" "$(id -un)" >"$out/meta.txt"
save system/os-release cat /etc/os-release
save system/uname.txt uname -a
save system/uptime.txt uptime
save system/df.txt df -h
save system/df-inodes.txt df -i
save system/memory.txt free -m
save network/ip.txt ip addr
save network/route.txt ip route
save network/listen.txt ss -ltn
save network/resolv.conf cat /etc/resolv.conf
save quillo/env.txt env_file
save quillo/compose-ps.txt docker compose ps -a
save quillo/images.txt docker compose images
save quillo/healthz.txt healthz
save quillo/docker-info.txt docker info
for service in api worker db llm embed; do
    save "quillo/logs/$service.log" docker compose logs --no-color --tail 400 "$service"
done
tar -C "$dir" -czf - "$root"
