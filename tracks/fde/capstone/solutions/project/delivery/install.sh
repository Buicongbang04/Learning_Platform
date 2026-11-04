#!/bin/bash
set -euo pipefail

bundle=$(cd "$(dirname "$0")" && pwd)
prefix=/opt/quillo
config=/etc/quillo/quillo.env
log=/var/log/quillo-install.log
daemon=/etc/docker/daemon.json
compose_bin=$prefix/bin/docker-compose
project=quillo
version=?
logged=0
work=""
stage=""

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
    [ -z "$stage" ] || rm -rf "$stage"
    [ -z "$work" ] || rm -rf "$work"
    if [ "$rc" -ne 0 ] && [ "$logged" -eq 0 ]; then
        echo "install: LỖI: dừng bất ngờ (mã $rc); xem output phía trên" >&2
        record "failed mã $rc"
    fi
}
trap finish EXIT

[ "$(id -u)" -eq 0 ] || { echo "install: cần chạy bằng root: sudo bash $0" >&2; exit 1; }
work=$(mktemp -d)
cd "$bundle"

say "1/9 kiểm toàn vẹn bundle (SHA256SUMS)"
[ -f SHA256SUMS ] || die "thiếu $bundle/SHA256SUMS"
if ! sha256sum --strict -c SHA256SUMS > "$work/sums.log" 2>&1; then
    bad=$(sed -n 's/: FAILED.*$//p' "$work/sums.log" | tr '\n' ' ')
    die "tệp không khớp SHA256SUMS: ${bad:-xem $work/sums.log}; chép lại bundle từ bản gốc, đừng cài"
fi
listed=$(awk '{sub(/^\*/, "", $2); print $2}' SHA256SUMS)
release_tar=$(printf '%s\n' "$listed" | grep -E '^quillo-[0-9]+\.[0-9]+\.[0-9]+\.tar$' || true)
[ "$(printf '%s\n' "$release_tar" | grep -c .)" -eq 1 ] || die "SHA256SUMS phải liệt kê đúng một quillo-X.Y.Z.tar"
for need in tools/docker-compose site.conf REQUIREMENTS.yaml verify.sh install.sh; do
    printf '%s\n' "$listed" | grep -qx "$need" || die "SHA256SUMS không liệt kê $need"
done
extra=$(find . -type f ! -name SHA256SUMS | sed 's#^\./##' | sort | comm -23 - <(printf '%s\n' "$listed" | sort) || true)
[ -z "$extra" ] || say "CẢNH BÁO: tệp ngoài SHA256SUMS bị bỏ qua: $(echo $extra)"
version=${release_tar#quillo-}
version=${version%.tar}

conf_value() {
    local value
    value=$(sed -n "s/^$1=//p" site.conf | tail -n 1)
    [[ $value =~ ^($2)$ ]] || return 1
    printf '%s' "$value"
}
registry=$(conf_value QUILLO_REGISTRY '|[A-Za-z0-9.-]+(:[0-9]{1,5})?') || die "site.conf: QUILLO_REGISTRY không hợp lệ"
bind=$(conf_value QUILLO_BIND '[0-9]{1,3}(\.[0-9]{1,3}){3}') || die "site.conf: QUILLO_BIND phải là địa chỉ IPv4"
port=$(conf_value QUILLO_PORT '[0-9]{1,5}') || die "site.conf: QUILLO_PORT phải là số"

say "2/9 preflight theo REQUIREMENTS.yaml"
for tool in docker python3 curl openssl tar sha256sum ss; do
    command -v "$tool" >/dev/null || die "thiếu lệnh $tool"
done
systemctl is-active --quiet docker || die "Docker daemon không chạy"
requirement() { awk -F': *' -v key="$1" '$1 == key {print $2; exit}' REQUIREMENTS.yaml; }
min_cpus=$(requirement min_cpus)
min_mem=$(requirement min_mem_mb)
min_disk=$(requirement min_disk_free_gb)
cpus=$(nproc)
mem=$(awk '/^MemTotal:/ {printf "%d", $2 / 1024}' /proc/meminfo)
[ "$cpus" -ge "$min_cpus" ] || die "máy có $cpus CPU, quillo cần tối thiểu $min_cpus"
[ "$((mem * 10))" -ge "$((min_mem * 9))" ] || die "MemTotal $mem MB, quillo cần tối thiểu $min_mem MB"
need_mb=$(( $(stat -c %s "$release_tar") / 1048576 * 3 + min_disk * 1024 ))
existing() { local p=$1; while [ ! -e "$p" ]; do p=$(dirname "$p"); done; printf '%s' "$p"; }
free_opt=$(df -Pm "$(existing "$prefix")" | awk 'NR==2 {print $4}')
free_docker=$(df -Pm "$(existing /var/lib/docker)" | awk 'NR==2 {print $4}')
[ "$free_opt" -ge "$need_mb" ] || die "cần ~${need_mb} MB trống cho $prefix, còn ${free_opt} MB"
[ "$free_docker" -ge "$need_mb" ] || die "cần ~${need_mb} MB trống ở /var/lib/docker, còn ${free_docker} MB"
if [ -n "$registry" ]; then
    curl -q -fsS --noproxy '*' -m 10 -o /dev/null "http://$registry/v2/" || die "không tới được registry nội bộ http://$registry"
fi
if [ -n "$(ss -Hltn "sport = :$port")" ]; then
    owner=$(docker ps -q --filter "label=com.docker.compose.project=$project" --filter "label=com.docker.compose.service=api")
    [ -n "$owner" ] || die "cổng $port đã có tiến trình khác nghe; đổi QUILLO_PORT trong site.conf hoặc hỏi IT"
fi

say "3/9 kiểm manifest.json bên trong $release_tar (đọc luồng, chưa ghi gì ra đĩa)"
verify_stream() {
    python3 - "$release_tar" "$version" <<'PY'
import hashlib, json, sys, tarfile
path, version = sys.argv[1], sys.argv[2]
root = f"quillo-{version}/"
digests, manifest = {}, None
try:
    with tarfile.open(path, "r:") as tar:
        for member in tar:
            name = member.name
            if name.startswith("/") or ".." in name.split("/") or not (name + "/").startswith(root):
                sys.exit(f"đường dẫn lạ trong bundle: {name}")
            if member.isdir():
                continue
            if not member.isfile():
                sys.exit(f"phần tử không phải tệp thường: {name}")
            rel = name[len(root):]
            handle = tar.extractfile(member)
            if rel == "manifest.json":
                manifest = json.load(handle)
                continue
            digest = hashlib.sha256()
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
            digests[rel] = digest.hexdigest()
except (tarfile.TarError, OSError, ValueError) as error:
    sys.exit(f"không đọc được {path}: {error}")
if manifest is None or manifest.get("version") != version:
    sys.exit(f"thiếu manifest.json hoặc version khác {version}")
expected = manifest["files"]
problems = [f"thiếu {p}" for p in sorted(set(expected) - set(digests))]
problems += [f"thừa {p}" for p in sorted(set(digests) - set(expected))]
problems += [f"sha256 sai {p}" for p in sorted(set(expected) & set(digests)) if digests[p] != expected[p]]
if problems:
    sys.exit("manifest: " + "; ".join(problems))
PY
}
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
verify_stream 2> "$work/stream.log" || die "$release_tar không khớp manifest.json bên trong: $(tail -n 1 "$work/stream.log")"

say "4/9 giải nén bản $version vào $prefix/releases"
release=$prefix/releases/$version
if [ -d "$release" ]; then
    verify_tree "$release" 2> "$work/tree.log" \
        || die "$release đã có nhưng không còn khớp manifest.json ($(tail -n 1 "$work/tree.log")); kiểm tay trước khi cài lại"
else
    install -d -m 0755 "$prefix/releases"
    stage=$prefix/releases/.$version.partial
    rm -rf "$stage"
    mkdir -p "$stage"
    tar -xf "$release_tar" -C "$stage" --strip-components=1 --no-same-owner || die "giải nén $release_tar lỗi"
    verify_tree "$stage" 2> "$work/tree.log" || die "bản giải nén không khớp manifest.json: $(tail -n 1 "$work/tree.log")"
    mv -T "$stage" "$release"
    stage=""
fi

say "5/9 docker compose ($compose_bin, không đụng plugin của hệ thống)"
if ! cmp -s tools/docker-compose "$compose_bin"; then
    install -D -m 0755 tools/docker-compose "$compose_bin" || die "không cài được $compose_bin"
fi
"$compose_bin" version >/dev/null || die "$compose_bin không chạy được"

if [ -n "$registry" ]; then
    say "6/9 khai registry nội bộ $registry cho Docker daemon"
    rc=0
    python3 - "$daemon" "$registry" <<'PY' || rc=$?
import json, os, shutil, sys, tempfile
path, registry = sys.argv[1], sys.argv[2]
existed = os.path.exists(path)
config = {}
if existed and open(path).read().strip():
    config = json.load(open(path))
current = config.get("insecure-registries", [])
if registry in current:
    sys.exit(0)
config["insecure-registries"] = [*current, registry]
if existed:
    shutil.copy2(path, path + ".bak-quillo")
os.makedirs(os.path.dirname(path), exist_ok=True)
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".daemon.json.")
with os.fdopen(fd, "w") as handle:
    json.dump(config, handle, indent=2)
    handle.write("\n")
os.chmod(tmp, 0o644)
os.replace(tmp, path)
sys.exit((10 if existed else 12) + (1 if config.get("live-restore") else 0))
PY
    case $rc in
        0) ;;
        10|11|12|13)
            if [ "$rc" -eq 10 ] || [ "$rc" -eq 12 ]; then
                echo "install: CẢNH BÁO: restart Docker để nhận registry; live-restore tắt nên MỌI container trên máy dừng rồi chạy lại" >&2
                record "warning docker restart without live-restore"
                logged=0
            fi
            if ! systemctl restart docker; then
                if [ "$rc" -le 11 ]; then cp -p "$daemon.bak-quillo" "$daemon"; else rm -f "$daemon"; fi
                systemctl restart docker || true
                die "restart Docker lỗi sau khi sửa $daemon; đã trả $daemon về như trước"
            fi
            ;;
        *) die "không đọc/ghi được $daemon (JSON hỏng?)" ;;
    esac
    systemctl is-active --quiet docker || die "Docker daemon không chạy sau khi đổi cấu hình"
else
    say "6/9 site không có registry nội bộ: dùng image nạp tại chỗ"
fi

say "7/9 nạp image${registry:+ và đẩy lên $registry}"
: > "$work/images"
for archive in "$release"/images/*.tar; do
    docker load -i "$archive" > "$work/load.log" || die "docker load $archive lỗi"
    loaded=$(awk '/^Loaded image: / {sub(/^Loaded image: /, ""); print; exit}' "$work/load.log")
    [ -n "$loaded" ] || die "docker load $archive không ra image có tag"
    target=$loaded
    if [ -n "$registry" ]; then
        path=$loaded
        first=${path%%/*}
        if [ "$first" != "$path" ] && { [[ $first == *.* ]] || [[ $first == *:* ]]; }; then
            path=${path#*/}
        fi
        target=$registry/$path
        docker tag "$loaded" "$target" || die "docker tag $loaded lỗi"
        docker push -q "$target" >/dev/null || die "push $target lỗi"
    fi
    printf '%s %s\n' "$loaded" "$target" >> "$work/images"
done

say "8/9 cấu hình $config và compose của site"
if [ ! -f "$config" ]; then
    install -d -m 0750 "$(dirname "$config")"
    (
        umask 077
        printf 'QUILLO_VERSION=%s\nQUILLO_ADMIN_TOKEN=%s\nQUILLO_DB_PASSWORD=%s\nQUILLO_BIND=%s\nQUILLO_PORT=%s\n' \
            "$version" "$(openssl rand -hex 24)" "$(openssl rand -hex 24)" "$bind" "$port" > "$config"
    )
fi
sed -i -e "s/^QUILLO_VERSION=.*/QUILLO_VERSION=$version/" -e "s/^QUILLO_BIND=.*/QUILLO_BIND=$bind/" \
    -e "s/^QUILLO_PORT=.*/QUILLO_PORT=$port/" "$config"
site=$prefix/site/$version
data=$prefix/data
install -d -m 0755 "$site"
install -d -o 10001 -g 10001 -m 0750 "$data/inbox"
base=("$compose_bin" -p "$project" --project-directory "$release" --env-file "$config" -f "$release/compose.yaml")
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

say "9/9 compose up và /healthz"
compose=("${base[@]}" -f "$site/compose.site.yaml")
if ! "${compose[@]}" up -d --wait --wait-timeout 200; then
    "${compose[@]}" ps -a >&2 || true
    die "compose up không khoẻ; xem: $compose_bin -p $project logs"
fi
body=$(curl -q -fsS --noproxy '*' -m 10 "http://127.0.0.1:$port/healthz") || die "/healthz không trả 200"
say "healthz: $body"
record installed
say "xong: quillo $version${registry:+ chạy từ registry $registry}"
