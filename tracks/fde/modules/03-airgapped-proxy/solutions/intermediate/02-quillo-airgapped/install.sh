#!/bin/bash
set -euo pipefail

usb=$(cd "$(dirname "$0")" && pwd)
registry=${QUILLO_REGISTRY:-10.0.2.101:5000}
prefix=/opt/quillo
config=/etc/quillo/quillo.env
log=/var/log/quillo-install.log
plugin=/usr/local/lib/docker/cli-plugins/docker-compose
project=quillo
version=?
logged=0
work=""

say() { echo "install: $*"; }
record() {
    printf '%s %s %s\n' "$(date -Is)" "$version" "$*" >> "$log" 2>/dev/null || true
    logged=1
}
die() {
    echo "install: LỖI: $*" >&2
    record "failed $*"
    exit 1
}
finish() {
    local rc=$?
    [ -n "$work" ] && rm -rf "$work"
    if [ "$rc" -ne 0 ] && [ "$logged" -eq 0 ]; then
        echo "install: LỖI: dừng bất ngờ (mã $rc); xem output phía trên" >&2
        record "failed mã $rc"
    fi
}
trap finish EXIT

[ "$(id -u)" -eq 0 ] || { echo "install: cần chạy bằng root: sudo bash $0" >&2; exit 1; }
work=$(mktemp -d)
cd "$usb"

say "1/7 kiểm toàn vẹn bản chép từ USB"
[ -f SHA256SUMS ] || die "thiếu $usb/SHA256SUMS"
sha256sum --strict --quiet -c SHA256SUMS || die "tệp trên USB không khớp SHA256SUMS: chép lại từ bản gốc, đừng cài"
bundle=$(awk '{sub(/^\*/, "", $2)} $2 ~ /^quillo-[0-9]+\.[0-9]+\.[0-9]+\.tar$/ {print $2}' SHA256SUMS)
[ "$(printf '%s\n' "$bundle" | grep -c .)" -eq 1 ] || die "SHA256SUMS phải liệt kê đúng một quillo-X.Y.Z.tar"
grep -Eq '^[0-9a-f]{64}  \*?tools/docker-compose$' SHA256SUMS || die "SHA256SUMS không liệt kê tools/docker-compose"
version=${bundle#quillo-}
version=${version%.tar}

say "2/7 preflight"
for tool in docker python3 curl openssl tar sha256sum; do
    command -v "$tool" >/dev/null || die "thiếu lệnh $tool"
done
systemctl is-active --quiet docker || die "Docker daemon không chạy"
mkdir -p "$prefix/releases"
need_mb=$(( $(stat -c %s "$bundle") / 1048576 * 3 + 1024 ))
free_opt=$(df -Pm "$prefix" | awk 'NR==2 {print $4}')
free_docker=$(df -Pm /var/lib/docker | awk 'NR==2 {print $4}')
[ "$free_opt" -ge "$need_mb" ] || die "cần ~${need_mb} MB trống cho $prefix, còn ${free_opt} MB"
[ "$free_docker" -ge "$need_mb" ] || die "cần ~${need_mb} MB trống ở /var/lib/docker, còn ${free_docker} MB"
curl -q -fsS --noproxy '*' -m 10 "http://$registry/v2/" >/dev/null || die "không tới được registry nội bộ http://$registry"

say "3/7 giải nén và kiểm manifest của bundle $version"
release=$prefix/releases/$version
verify_tree() {
    (cd "$1" && python3 - <<'PY'
import hashlib, json, os, sys
expected = json.load(open("manifest.json"))["files"]
found = set()
for root, dirs, files in os.walk("."):
    for name in files:
        rel = os.path.relpath(os.path.join(root, name), ".")
        if rel != "manifest.json":
            found.add(rel)
problems = [f"thiếu {p}" for p in sorted(set(expected) - found)]
problems += [f"thừa {p}" for p in sorted(found - set(expected))]
for rel in sorted(set(expected) & found):
    digest = hashlib.sha256()
    with open(rel, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected[rel]:
        problems.append(f"sha256 sai {rel}")
if problems:
    sys.exit("manifest: " + "; ".join(problems))
PY
    )
}
if [ -d "$release" ]; then
    verify_tree "$release" || die "$release đã có nhưng không còn khớp manifest.json (bị sửa?); kiểm tay trước khi cài lại"
else
    stage=$prefix/releases/.$version.partial
    rm -rf "$stage"
    mkdir -p "$stage"
    tar -xf "$bundle" -C "$stage" --strip-components=1 --no-same-owner || { rm -rf "$stage"; die "giải nén $bundle lỗi"; }
    if ! verify_tree "$stage"; then
        rm -rf "$stage"
        die "bundle không khớp manifest.json bên trong"
    fi
    mv -T "$stage" "$release"
fi

say "4/7 plugin docker compose"
if ! cmp -s tools/docker-compose "$plugin"; then
    install -D -m 0755 tools/docker-compose "$plugin" || die "không cài được $plugin"
fi
docker compose version >/dev/null || die "docker compose không chạy được sau khi cài $plugin"

say "5/7 khai registry nội bộ cho Docker daemon"
rc=0
python3 - "$registry" <<'PY' || rc=$?
import json, os, shutil, sys, tempfile
path, registry = "/etc/docker/daemon.json", sys.argv[1]
config = {}
if os.path.exists(path) and open(path).read().strip():
    config = json.load(open(path))
current = config.get("insecure-registries", [])
if registry in current:
    sys.exit(0)
config["insecure-registries"] = [*current, registry]
if os.path.exists(path):
    shutil.copy2(path, path + ".bak")
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".daemon.json.")
with os.fdopen(fd, "w") as handle:
    json.dump(config, handle, indent=2)
    handle.write("\n")
os.chmod(tmp, 0o644)
os.replace(tmp, path)
sys.exit(11 if config.get("live-restore") else 10)
PY
if [ "$rc" -eq 10 ] || [ "$rc" -eq 11 ]; then
    if [ "$rc" -eq 10 ]; then
        echo "install: CẢNH BÁO: restart Docker để nhận registry; live-restore tắt nên MỌI container trên máy sẽ dừng rồi chạy lại" >&2
        record "warning docker restart without live-restore"
        logged=0
    fi
    systemctl restart docker || die "restart docker lỗi sau khi sửa daemon.json (bản cũ: daemon.json.bak)"
elif [ "$rc" -ne 0 ]; then
    die "không đọc/ghi được /etc/docker/daemon.json"
fi
systemctl is-active --quiet docker || systemctl restart docker || die "Docker daemon không chạy và không restart được"

say "6/7 nạp image và đẩy lên $registry"
: > "$work/images"
for archive in "$release"/images/*.tar; do
    docker load -i "$archive" > "$work/load.log" || die "docker load $archive lỗi"
    loaded=$(awk '/^Loaded image: / {sub(/^Loaded image: /, ""); print; exit}' "$work/load.log")
    [ -n "$loaded" ] || die "docker load $archive không ra image có tag"
    path=$loaded
    first=${path%%/*}
    if [ "$first" != "$path" ] && { [[ $first == *.* ]] || [[ $first == *:* ]]; }; then
        path=${path#*/}
    fi
    docker tag "$loaded" "$registry/$path" || die "docker tag $loaded lỗi"
    docker push -q "$registry/$path" >/dev/null || die "push $registry/$path lỗi"
    printf '%s %s\n' "$loaded" "$registry/$path" >> "$work/images"
done

if [ ! -f "$config" ]; then
    install -d -m 0750 "$(dirname "$config")"
    (
        umask 077
        printf 'QUILLO_VERSION=%s\nQUILLO_ADMIN_TOKEN=%s\nQUILLO_DB_PASSWORD=%s\nQUILLO_BIND=0.0.0.0\nQUILLO_PORT=18080\n' \
            "$version" "$(openssl rand -hex 24)" "$(openssl rand -hex 24)" > "$config"
    )
fi
sed -i "s/^QUILLO_VERSION=.*/QUILLO_VERSION=$version/" "$config"
port=$(sed -n 's/^QUILLO_PORT=//p' "$config")

site=$prefix/site/$version
data=$prefix/data
install -d -m 0755 "$site"
install -d -o 10001 -g 10001 -m 0750 "$data/inbox"
base=(docker compose -p "$project" --project-directory "$release" --env-file "$config" -f "$release/compose.yaml")
"${base[@]}" config --format json > "$work/config.json" || die "compose.yaml của bundle không hợp lệ với $config"
python3 - "$work/config.json" "$work/images" "$site/compose.site.yaml" "$data/inbox" <<'PY' || die "không dựng được compose.site.yaml"
import json, sys
services = json.load(open(sys.argv[1]))["services"]
mapping = dict(line.split() for line in open(sys.argv[2]) if line.strip())
lines = ["services:"]
for name, service in sorted(services.items()):
    image = service.get("image", "")
    if image not in mapping:
        sys.exit(f"bundle không có image {image!r} mà dịch vụ {name} cần")
    lines.append(f"  {name}:\n    image: {mapping[image]}")
    if any(v.get("target") == "/data/inbox" for v in service.get("volumes", [])):
        lines.append(f"    volumes:\n      - {sys.argv[4]}:/data/inbox")
open(sys.argv[3], "w").write("\n".join(lines) + "\n")
PY
ln -sfn "$release" "$prefix/current.tmp"
mv -T "$prefix/current.tmp" "$prefix/current"

say "7/7 compose up"
compose=("${base[@]}" -f "$site/compose.site.yaml")
if ! "${compose[@]}" up -d --wait --wait-timeout 240; then
    "${compose[@]}" ps -a >&2 || true
    die "compose up không khoẻ; xem: docker compose -p $project logs"
fi
body=$(curl -q -fsS --noproxy '*' -m 10 "http://127.0.0.1:$port/healthz") || die "/healthz không trả 200"
say "healthz: $body"
record installed
say "xong: quillo $version chạy từ registry $registry"
