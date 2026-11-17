#!/bin/sh
set -eu

die() { echo "deploy.sh: $*" >&2; exit 1; }
log() { echo "deploy.sh: $*" >&2; }

here=$(cd "$(dirname "$0")" && pwd)
uid=$(id -u)
[ "$uid" -ne 0 ] || die "chạy bằng user dịch vụ, không phải root"
[ -n "${XDG_RUNTIME_DIR:-}" ] || export XDG_RUNTIME_DIR=/run/user/$uid
socket=$XDG_RUNTIME_DIR/podman/podman.sock

command -v podman >/dev/null 2>&1 || die "máy không có podman"
[ -x "$here/docker-compose" ] || die "bundle thiếu binary docker-compose"
[ -r "$here/config/notice.conf" ] || die "thiếu $here/config/notice.conf"

if ! systemctl --user is-enabled --quiet podman.socket 2>/dev/null; then
    log "bật podman.socket của user $(id -un)"
    systemctl --user enable podman.socket >/dev/null 2>&1 || die "không bật được podman.socket (systemctl --user)"
fi
systemctl --user start podman.socket
[ -S "$socket" ] || die "không thấy socket Podman ở $socket"
if [ "$(loginctl show-user "$(id -un)" -p Linger --value 2>/dev/null)" != yes ]; then
    log "cảnh báo: linger chưa bật, container sẽ dừng khi bạn đăng xuất (nhờ IT: loginctl enable-linger $(id -un))"
fi

log "nạp image"
podman load -q -i "$here/notice-image.tar" >/dev/null
podman image exists localhost/notice:1.0 || die "image localhost/notice:1.0 không có sau khi nạp"

log "chạy compose qua $socket"
DOCKER_HOST=unix://$socket "$here/docker-compose" -f "$here/compose.yaml" up -d --force-recreate --pull never
log "xong"
