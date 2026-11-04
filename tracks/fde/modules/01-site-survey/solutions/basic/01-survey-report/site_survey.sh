#!/bin/sh
set -u
LC_ALL=C
export LC_ALL

json_string() {
    if [ -n "$1" ]; then
        printf '"%s"' "$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g')"
    else
        printf 'null'
    fi
}

os_id=$(. /etc/os-release && printf '%s' "$ID")
os_version=$(. /etc/os-release && printf '%s' "${VERSION_ID:-}")
kernel_major=$(uname -r | cut -d. -f1-2)

glibc=$(getconf GNU_LIBC_VERSION 2>/dev/null | awk '{print $2}')
if [ -z "$glibc" ]; then
    glibc=$(ldd --version 2>/dev/null | awk 'NR==1 {print $NF}')
fi

cpus=$(nproc 2>/dev/null || getconf _NPROCESSORS_ONLN)
mem_mb=$(awk '/^MemTotal:/ {printf "%d", $2 / 1024}' /proc/meminfo)
disk_free=$(df -P -k / | awk 'NR==2 {printf "%.1f", $4 / 1048576}')

gpu=""
if command -v nvidia-smi >/dev/null 2>&1; then
    gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n 1)
fi
if [ -z "$gpu" ] && [ -e /dev/nvidia0 ]; then
    gpu="nvidia (nvidia-smi không trả lời)"
fi

proxy_from_file() {
    [ -r /etc/environment ] || return 0
    sed -n "s/^[[:space:]]*\(export[[:space:]]\{1,\}\)\{0,1\}$1=[\"']\{0,1\}\([^\"']*\).*/\2/p" /etc/environment | head -n 1
}
proxy_url=${https_proxy:-${HTTPS_PROXY:-}}
[ -n "$proxy_url" ] || proxy_url=$(proxy_from_file https_proxy)
[ -n "$proxy_url" ] || proxy_url=$(proxy_from_file HTTPS_PROXY)
proxy_url=$(printf '%s' "$proxy_url" | sed 's#//[^/]*@#//#')

if sudo -n true >/dev/null 2>&1; then
    sudo_ok=true
else
    sudo_ok=false
fi

if command -v getenforce >/dev/null 2>&1; then
    selinux=$(getenforce 2>/dev/null | tr 'A-Z' 'a-z')
elif [ -r /sys/fs/selinux/enforce ]; then
    if [ "$(cat /sys/fs/selinux/enforce)" = 1 ]; then selinux=enforcing; else selinux=permissive; fi
else
    selinux=""
fi
[ -n "$selinux" ] || selinux="n/a"

runtime=""
if command -v docker >/dev/null 2>&1; then
    if docker --version 2>/dev/null | grep -qi podman; then runtime=podman; else runtime=docker; fi
elif command -v podman >/dev/null 2>&1; then
    runtime=podman
fi

egress=none
if curl -fsSI --noproxy '*' --max-time 5 -o /dev/null https://pypi.org/simple/ 2>/dev/null; then
    egress=open
elif [ -n "$proxy_url" ] && curl -sSI --max-time 5 -o /dev/null --proxy "$proxy_url" http://pypi.org/simple/ 2>/dev/null; then
    egress=proxy
fi

printf '{\n'
printf '  "os_id": %s,\n' "$(json_string "$os_id")"
printf '  "os_version": %s,\n' "$(json_string "$os_version")"
printf '  "kernel_major": %s,\n' "$(json_string "$kernel_major")"
printf '  "glibc": %s,\n' "$(json_string "$glibc")"
printf '  "cpus": %s,\n' "$cpus"
printf '  "mem_mb": %s,\n' "$mem_mb"
printf '  "disk_free_gb_max": %s,\n' "$disk_free"
printf '  "gpu": %s,\n' "$(json_string "$gpu")"
printf '  "proxy_url": %s,\n' "$(json_string "$proxy_url")"
printf '  "sudo": %s,\n' "$sudo_ok"
printf '  "selinux": %s,\n' "$(json_string "$selinux")"
printf '  "runtime": %s,\n' "$(json_string "$runtime")"
printf '  "egress": %s\n' "$(json_string "$egress")"
printf '}\n'
