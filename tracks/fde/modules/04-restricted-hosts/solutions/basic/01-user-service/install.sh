#!/bin/sh
set -eu

die() { echo "install.sh: $*" >&2; exit 1; }
log() { echo "install.sh: $*" >&2; }

here=$(cd "$(dirname "$0")" && pwd)
lib=$HOME/.local/lib/heartbeat
units=${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user
user=$(id -un)

[ "$(id -u)" -ne 0 ] || die "chạy bằng user dịch vụ, không phải root"
for f in heartbeat.sh heartbeat.service; do
    [ -r "$here/$f" ] || die "bundle thiếu $f"
done
[ -n "${XDG_RUNTIME_DIR:-}" ] || export XDG_RUNTIME_DIR=/run/user/$(id -u)
systemctl --user show-environment >/dev/null 2>&1 \
    || die "không nói chuyện được với systemd --user (đăng nhập bằng SSH/console của chính user này, không qua su)"

mkdir -p "$lib" "$units"
changed=0
if ! cmp -s "$here/heartbeat.sh" "$lib/heartbeat.sh"; then
    cp "$here/heartbeat.sh" "$lib/heartbeat.sh.new"
    chmod 0755 "$lib/heartbeat.sh.new"
    mv -f "$lib/heartbeat.sh.new" "$lib/heartbeat.sh"
    changed=1
fi
if ! cmp -s "$here/heartbeat.service" "$units/heartbeat.service"; then
    cp "$here/heartbeat.service" "$units/heartbeat.service.new"
    mv -f "$units/heartbeat.service.new" "$units/heartbeat.service"
    changed=1
fi

systemctl --user daemon-reload
systemctl --user enable heartbeat.service >/dev/null 2>&1
if [ "$changed" -eq 1 ]; then
    systemctl --user restart heartbeat.service
else
    systemctl --user start heartbeat.service
fi

if [ "$(loginctl show-user "$user" -p Linger --value 2>/dev/null)" != yes ]; then
    if loginctl enable-linger "$user" 2>/dev/null; then
        log "đã bật linger cho $user"
    else
        die "không tự bật được linger cho $user; nhờ IT chạy: loginctl enable-linger $user"
    fi
fi

systemctl --user is-active --quiet heartbeat.service || die "heartbeat.service không active; xem: journalctl --user -u heartbeat.service"
log "xong: $(systemctl --user show -p MainPID heartbeat.service)"
