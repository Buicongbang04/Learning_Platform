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
    [ -f "$daemon" ] && cp -p "$daemon" "$daemon.bak.$(date +%Y%m%d%H%M%S)"
    install -D -m 0644 "$work/daemon.json" "$daemon" || die "không ghi được $daemon"
    say "đã thêm $registry vào insecure-registries trong $daemon"
    systemctl restart docker || die "restart docker lỗi; khôi phục $daemon từ bản .bak rồi xem journalctl -u docker"
fi

docker info --format '{{json .RegistryConfig.IndexConfigs}}' | grep -q "\"$registry\"" \
    || die "Docker daemon chưa nhận $registry là registry nội bộ"
curl -q -fsS --noproxy '*' -m 10 "http://$registry/v2/" >/dev/null || die "không tới được http://$registry/v2/"

loaded=$(docker load -i "$archive" | sed -n 's/^Loaded image: //p' | head -n 1)
[ -n "$loaded" ] || die "docker load không ra image có tag (tarball lưu theo ID?)"
ref="$registry/$target"
docker tag "$loaded" "$ref"
docker push "$ref" >"$work/push.log" 2>&1 || { cat "$work/push.log" >&2; die "push $ref lỗi"; }
digest=$(sed -n 's/.*digest: \(sha256:[0-9a-f]*\).*/\1/p' "$work/push.log" | tail -n 1)
say "đã đẩy $ref ($digest)"
