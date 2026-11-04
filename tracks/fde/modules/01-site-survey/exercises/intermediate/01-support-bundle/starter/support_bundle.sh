#!/bin/sh
set -eu

out=${1:?Cách dùng: sh support_bundle.sh <thư mục ra>}
work="$out/support-bundle"
rm -rf "$work"
mkdir -p "$work"

distro=$(lsb_release -is | tr 'A-Z' 'a-z')
release=$(lsb_release -rs)

cat /etc/os-release > "$work/os-release.txt"
uname -a > "$work/uname.txt"
cat /proc/meminfo > "$work/meminfo.txt"
df -P -k > "$work/disk.txt"
{ ip addr; ip route; } > "$work/net.txt"
ss -t -l -n > "$work/listening.txt"
timedatectl > "$work/time.txt"
ulimit -a > "$work/limits.txt"
sudo -n dmesg > "$work/kernel.txt"
sudo -n aa-status > "$work/security.txt"
resolvectl dns > "$work/dns.txt"
docker info > "$work/runtime.txt" 2>&1

engine="docker $(docker version --format '{{.Server.Version}}')"
servers=$(sed 's/^[^:]*: *//' "$work/dns.txt" | tr ' ' '\n' | sed '/^$/d' | sort -u | tr '\n' ' ')
mem_kb=$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)

python3 - "$work/summary.json" "$distro-$release" "$(uname -r)" "$engine" "$servers" "$mem_kb" <<'EOF'
import json
import sys

path, os_name, kernel, runtime, dns, mem_kb = sys.argv[1:]
summary = {"os": os_name, "kernel": kernel, "runtime": runtime, "dns": dns.split(), "mem_kb": int(mem_kb)}
with open(path, "w") as f:
    json.dump(summary, f, indent=2)
EOF

tar -czf "$out/support-bundle.tar.gz" -C "$out" support-bundle
echo "Đã tạo $out/support-bundle.tar.gz, gửi tệp này lại cho đội hỗ trợ."
