#!/bin/sh
set -eu

usage() { echo "Cách dùng: sudo sh publish.sh <image.tar> <registry host:port> <repo:tag>" >&2; exit 2; }
die() { echo "publish: $*" >&2; exit 1; }
say() { echo "publish: $*"; }

[ $# -eq 3 ] || usage
archive=$1
registry=$2
target=$3
[ "$(id -u)" -eq 0 ] || die "cần chạy bằng root (sudo) để sửa /etc/docker/daemon.json"
[ -r "$archive" ] || die "không đọc được $archive"
case $registry in
    */*|"") die "registry phải dạng host:port, nhận '$registry'" ;;
esac
case $target in
    *:*) ;;
    *) die "đích phải dạng repo:tag, nhận '$target'" ;;
esac

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
daemon=/etc/docker/daemon.json

python3 - "$daemon" "$registry" "$work/daemon.json" <<'PY' || die "$daemon hiện có không phải JSON hợp lệ; sửa tay với IT trước"
import json, sys
from pathlib import Path

path, registry, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
config = json.loads(path.read_text()) if path.exists() and path.read_text().strip() else {}
if not isinstance(config, dict):
    sys.exit(f"{path} không phải object JSON")
current = config.get("insecure-registries", [])
if registry not in current:
    config["insecure-registries"] = [*current, registry]
out.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n")
PY

if [ -f "$daemon" ] && python3 -c 'import json,sys; sys.exit(json.load(open(sys.argv[1])) != json.load(open(sys.argv[2])))' "$daemon" "$work/daemon.json"; then
    say "$daemon đã có $registry"
    systemctl is-active --quiet docker || systemctl restart docker || die "Docker daemon không chạy và không restart được"
else
    backup=""
    if [ -f "$daemon" ]; then
        backup="$daemon.bak.$(date +%Y%m%d%H%M%S)"
        cp -p "$daemon" "$backup" || die "không sao lưu được $daemon"
    fi
    install -D -m 0644 "$work/daemon.json" "$daemon.tmp.$$" || die "không ghi được $daemon"
    mv -f "$daemon.tmp.$$" "$daemon" || die "không thay được $daemon"
    say "đã thêm $registry vào insecure-registries trong $daemon"
    if ! grep -q '"live-restore": true' "$daemon"; then
        echo "publish: CẢNH BÁO: live-restore tắt, restart Docker sẽ dừng rồi chạy lại MỌI container trên máy" >&2
    fi
    if ! systemctl restart docker; then
        if [ -n "$backup" ]; then
            cp -p "$backup" "$daemon"
            echo "publish: restart lỗi, đã khôi phục $daemon từ $backup" >&2
        else
            rm -f "$daemon"
            echo "publish: restart lỗi, đã xoá $daemon vừa tạo" >&2
        fi
        systemctl restart docker || true
        die "restart docker với cấu hình mới lỗi; xem journalctl -u docker"
    fi
fi

docker info --format '{{json .RegistryConfig.IndexConfigs}}' | grep -q "\"$registry\"" \
    || die "Docker daemon chưa nhận $registry là registry nội bộ"
curl -q -fsS --noproxy '*' -m 10 "http://$registry/v2/" >/dev/null || die "không tới được http://$registry/v2/"

docker load -i "$archive" > "$work/load.log" 2>&1 || { cat "$work/load.log" >&2; die "docker load $archive lỗi (tệp hỏng hay không phải image tarball?)"; }
loaded=$(awk '/^Loaded image: / {sub(/^Loaded image: /, ""); print; exit}' "$work/load.log")
[ -n "$loaded" ] || die "docker load không ra image có tag (tarball lưu theo ID?)"
ref="$registry/$target"
docker tag "$loaded" "$ref" || die "docker tag $loaded $ref lỗi"
docker push "$ref" >"$work/push.log" 2>&1 || { cat "$work/push.log" >&2; die "push $ref lỗi"; }
digest=$(sed -n 's/.*digest: \(sha256:[0-9a-f]*\).*/\1/p' "$work/push.log" | tail -n 1)
say "đã đẩy $ref ($digest)"
