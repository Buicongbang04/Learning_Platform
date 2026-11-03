#!/bin/sh
set -u
LC_ALL=C
export LC_ALL

out=${1:?Cách dùng: sh support_bundle.sh <thư mục ra>}
work="$out/support-bundle"
rm -rf "$work"
mkdir -p "$work" || exit 1

collect() {
    file=$1
    shift
    if ! "$@" > "$work/$file" 2>&1; then
        printf '\n[support_bundle] lệnh "%s" lỗi hoặc không có trên máy này\n' "$*" >> "$work/$file"
    fi
}

has() {
    command -v "$1" >/dev/null 2>&1
}

json_string() {
    printf '"%s"' "$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g')"
}

os_name=$(. /etc/os-release && printf '%s-%s' "$ID" "${VERSION_ID:-}")

collect os-release.txt cat /etc/os-release
collect uname.txt uname -a
collect meminfo.txt cat /proc/meminfo
collect disk.txt df -P -k
collect net.txt sh -c 'ip addr; ip route'
collect listening.txt ss -t -l -n
collect time.txt timedatectl
collect limits.txt sh -c 'ulimit -a'

if dmesg > "$work/kernel.txt" 2>/dev/null; then
    :
else
    echo "dmesg bị chặn với user thường (kernel.dmesg_restrict=1); không dùng sudo, bỏ qua log kernel" > "$work/kernel.txt"
fi

if has getenforce; then
    collect security.txt sh -c 'getenforce; sestatus 2>/dev/null || true'
elif has aa-status; then
    collect security.txt sh -c 'aa-enabled 2>/dev/null; aa-status 2>&1 || true'
else
    echo "Không có getenforce hay aa-status" > "$work/security.txt"
fi

servers=""
if has resolvectl && resolvectl dns > "$work/dns.txt" 2>&1; then
    servers=$(sed 's/^[^:]*: *//' "$work/dns.txt" | tr ' ' '\n' | sed '/^$/d' | sort -u)
fi
if [ -z "$servers" ]; then
    { echo "# resolvectl không dùng được, đọc /etc/resolv.conf"; cat /etc/resolv.conf; } > "$work/dns.txt" 2>&1
    servers=$(awk '$1 == "nameserver" {print $2}' /etc/resolv.conf | sort -u)
fi

engine=none
if has docker && version=$(docker version --format '{{.Server.Version}}' 2>/dev/null) && [ -n "$version" ]; then
    engine="docker $version"
    collect runtime.txt docker info
elif has podman && version=$(podman version --format '{{.Client.Version}}' 2>/dev/null) && [ -n "$version" ]; then
    engine="podman $version"
    collect runtime.txt podman info
else
    echo "Không có Docker daemon hay Podman trả lời cho user này" > "$work/runtime.txt"
fi

mem_kb=$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)
dns_json=""
for server in $servers; do
    dns_json="${dns_json:+$dns_json, }$(json_string "$server")"
done

{
    printf '{\n'
    printf '  "os": %s,\n' "$(json_string "$os_name")"
    printf '  "kernel": %s,\n' "$(json_string "$(uname -r)")"
    printf '  "runtime": %s,\n' "$(json_string "$engine")"
    printf '  "dns": [%s],\n' "$dns_json"
    printf '  "mem_kb": %s\n' "$mem_kb"
    printf '}\n'
} > "$work/summary.json"

tar -czf "$out/support-bundle.tar.gz" -C "$out" support-bundle || exit 1
echo "Đã tạo $out/support-bundle.tar.gz, gửi tệp này lại cho đội hỗ trợ."
