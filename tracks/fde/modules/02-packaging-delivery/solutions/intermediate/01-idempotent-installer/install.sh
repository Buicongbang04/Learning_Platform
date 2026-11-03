#!/usr/bin/env bash
set -euo pipefail

PREFIX=/opt/beacon
RELEASES=$PREFIX/releases
CONF=/etc/beacon/beacon.env
UNIT=/etc/systemd/system/beacon.service
LOG=/var/log/beacon/install.log
HEALTH_TIMEOUT=60

BUNDLE=${1:-}
VERSION=unknown
WORK=""
STAGE=""
NEW_RELEASE=0

say() {
    printf '%s %s\n' "$(date -Is)" "$*" >>"$LOG"
    printf '%s\n' "$*" >&2
}

finish() {
    printf '%s %s %s\n' "$(date -Is)" "$VERSION" "$1" >>"$LOG"
}

cleanup() {
    [ -n "$STAGE" ] && rm -rf -- "$STAGE"
    [ -n "$WORK" ] && rm -rf -- "$WORK"
    return 0
}
trap cleanup EXIT

die() {
    say "LỖI: $*"
    finish failed
    exit 1
}

manifest_py() {
    python3 - "$@" <<'PY'
import hashlib, json, os, stat, sys
from pathlib import PurePosixPath

command, manifest_path = sys.argv[1], sys.argv[2]
manifest = json.load(open(manifest_path))
files = manifest["files"]
for name in files:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or name == "manifest.json":
        sys.exit(f"đường dẫn lạ trong manifest: {name}")
if command == "info":
    if manifest.get("name") != "beacon":
        sys.exit(f"bundle không phải beacon: {manifest.get('name')!r}")
    print(manifest["version"], sum(int(f["size"]) for f in files.values()))
elif command == "verify":
    root = sys.argv[3]
    problems = []
    found = {}
    for top, dirs, names in os.walk(root):
        for name in dirs + names:
            path = os.path.join(top, name)
            mode = os.lstat(path).st_mode
            if stat.S_ISDIR(mode) and os.listdir(path):
                continue
            found[os.path.relpath(path, root)] = mode
    for name in sorted(set(found) - set(files) - {"manifest.json"}):
        problems.append(f"thừa: {name}")
    for name, meta in sorted(files.items()):
        path = os.path.join(root, name)
        if not stat.S_ISREG(found.get(name, 0)):
            problems.append(f"thiếu hoặc không phải tệp thường: {name}")
            continue
        sha = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                sha.update(chunk)
        if os.path.getsize(path) != int(meta["size"]) or sha.hexdigest() != meta["sha256"]:
            problems.append(f"sai sha256/kích thước: {name}")
    if problems:
        sys.exit("\n".join(problems))
PY
}

health() {
    python3 - "$1" "$2" "$3" <<'PY'
import json, sys, time, urllib.request

port, version, timeout = sys.argv[1], sys.argv[2], float(sys.argv[3])
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
deadline = time.monotonic() + timeout
while time.monotonic() < deadline:
    try:
        with opener.open(f"http://127.0.0.1:{port}/healthz", timeout=2) as response:
            if json.load(response).get("version") == version:
                sys.exit(0)
    except (OSError, ValueError):
        pass
    time.sleep(1)
sys.exit(1)
PY
}

port() {
    local value
    value=$(sed -n 's/^BEACON_PORT=//p' "$CONF" | tail -n 1)
    printf '%s\n' "${value:-8088}"
}

current_release() {
    readlink "$PREFIX/current" 2>/dev/null || true
}

switch_to() {
    ln -sfn "$1" "$PREFIX/.current.new"
    mv -T "$PREFIX/.current.new" "$PREFIX/current"
}

prune() {
    local keep_a=$1 keep_b=$2
    for dir in "$RELEASES"/*; do
        [ -d "$dir" ] || continue
        case "releases/$(basename "$dir")" in
            "$keep_a" | "$keep_b") ;;
            *) rm -rf -- "$dir"; say "đã xoá bản cũ $(basename "$dir")" ;;
        esac
    done
}

preflight() {
    [ "$(id -u)" -eq 0 ] || { printf 'Cần chạy bằng root (sudo bash install.sh <bundle.tar>)\n' >&2; exit 1; }
    mkdir -p "$(dirname "$LOG")"
    [ -n "$BUNDLE" ] || die "cách dùng: install.sh <bundle.tar>"
    [ -f "$BUNDLE" ] || die "không thấy bundle $BUNDLE"
    for tool in python3 tar systemctl useradd df; do
        command -v "$tool" >/dev/null || die "thiếu lệnh $tool"
    done
    [ -d /run/systemd/system ] || die "máy không chạy systemd"
}

main() {
    preflight
    WORK=$(mktemp -d)
    tar -xOf "$BUNDLE" --wildcards --occurrence=1 '*/manifest.json' >"$WORK/manifest.json" 2>/dev/null \
        || die "không đọc được manifest.json trong $BUNDLE (tệp hỏng hoặc chép thiếu?)"
    local info total
    info=$(manifest_py info "$WORK/manifest.json" 2>&1) || die "$info"
    read -r VERSION total <<<"$info"
    [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { VERSION=unknown; die "version lạ trong manifest"; }
    local release="$RELEASES/$VERSION" target="releases/$VERSION"
    say "bắt đầu cài beacon $VERSION từ $BUNDLE"

    if [ -d "$release" ] && cmp -s "$WORK/manifest.json" "$release/manifest.json" \
        && [ "$(current_release)" = "$target" ] && [ -f "$CONF" ] && id beacon >/dev/null 2>&1 \
        && cmp -s "$release/systemd/beacon.service" "$UNIT" \
        && systemctl is-enabled --quiet beacon && systemctl is-active --quiet beacon \
        && health "$(port)" "$VERSION" 30; then
        say "beacon $VERSION đã cài và đang chạy, không đổi gì"
        finish unchanged
        return 0
    fi

    if ! { [ -d "$release" ] && cmp -s "$WORK/manifest.json" "$release/manifest.json"; }; then
        mkdir -p "$RELEASES"
        local avail need
        avail=$(df -P -k "$RELEASES" | awk 'NR==2 {print $4 * 1024}')
        need=$((total + total / 20 + 64 * 1024 * 1024))
        [ "$avail" -ge "$need" ] || die "không đủ chỗ ở $RELEASES: cần $((need / 1048576)) MiB, còn $((avail / 1048576)) MiB"
        STAGE="$RELEASES/.$VERSION.partial"
        rm -rf -- "$STAGE"
        mkdir -p "$STAGE"
        tar -xf "$BUNDLE" -C "$STAGE" --strip-components=1 --no-same-owner --no-same-permissions \
            || die "giải nén $BUNDLE lỗi (tệp hỏng, chép thiếu, hay hết chỗ?)"
        local problems
        problems=$(manifest_py verify "$WORK/manifest.json" "$STAGE" 2>&1) || die "bundle không khớp manifest: $problems"
        chmod -R u=rwX,go=rX "$STAGE"
        rm -rf -- "$release"
        mv -T "$STAGE" "$release"
        STAGE=""
        NEW_RELEASE=1
        say "đã giải nén và kiểm tra $release"
    fi

    id beacon >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin beacon
    if [ ! -f "$CONF" ]; then
        install -D -m 0640 -o root -g beacon "$release/config/beacon.env" "$CONF"
        say "tạo $CONF từ cấu hình mặc định"
    fi
    local previous
    previous=$(current_release)
    if [ -f "$UNIT" ]; then
        cp -p "$UNIT" "$WORK/beacon.service.previous"
    fi
    if activate "$target" "$release" "$VERSION"; then
        prune "$target" "$previous"
        say "beacon $VERSION đang chạy"
        finish installed
        return 0
    fi
    say "beacon $VERSION không lên (unit, khởi động hoặc /healthz sau ${HEALTH_TIMEOUT}s)"
    rollback "$previous" "$target"
}

activate() {
    local target=$1 release=$2 version=$3
    if ! cmp -s "$release/systemd/beacon.service" "$UNIT"; then
        install -m 0644 "$release/systemd/beacon.service" "$UNIT" || return 1
        systemctl daemon-reload || return 1
    fi
    systemctl is-enabled --quiet beacon || systemctl enable --quiet beacon || return 1
    if [ "$(current_release)" != "$target" ]; then
        switch_to "$target" || return 1
    fi
    systemctl restart beacon || return 1
    health "$(port)" "$version" "$HEALTH_TIMEOUT"
}

clean_failed_first_install() {
    local failed=$1
    systemctl disable --now beacon 2>/dev/null || true
    rm -f -- "$UNIT" "$PREFIX/current"
    systemctl daemon-reload || true
    systemctl reset-failed beacon 2>/dev/null || true
    if [ "$NEW_RELEASE" = 1 ]; then
        rm -rf -- "${PREFIX:?}/$failed"
    fi
    die "lần cài đầu không lên: đã gỡ unit, current và bản vừa giải nén; máy trở về như trước khi cài"
}

restore_same() {
    local release=$1
    if [ -f "$WORK/beacon.service.previous" ]; then
        cp -p "$WORK/beacon.service.previous" "$UNIT" || die "không trả lại được unit cũ"
    else
        install -m 0644 "$PREFIX/$release/systemd/beacon.service" "$UNIT" || die "không trả lại được unit của $release"
    fi
    systemctl daemon-reload || die "daemon-reload lỗi"
    systemctl reset-failed beacon 2>/dev/null || true
    systemctl restart beacon || true
    die "${release#releases/} đã cài nhưng không lên khi chạy lại: giữ nguyên bản cài, unit và current; kiểm cấu hình $CONF và journalctl -u beacon"
}

rollback() {
    local previous=$1 failed=$2
    if [ -z "$previous" ]; then
        clean_failed_first_install "$failed"
    fi
    if [ "$previous" = "$failed" ]; then
        restore_same "$failed"
    fi
    [ -d "$PREFIX/$previous" ] || die "bản trước $previous không còn trên đĩa: không quay về được, không gỡ gì"
    if [ -f "$WORK/beacon.service.previous" ]; then
        cp -p "$WORK/beacon.service.previous" "$UNIT" || die "không trả lại được unit cũ"
    else
        install -m 0644 "$PREFIX/$previous/systemd/beacon.service" "$UNIT" || die "không trả lại được unit của $previous"
    fi
    systemctl daemon-reload || die "daemon-reload lỗi khi quay về"
    switch_to "$previous" || die "không trỏ lại được current về $previous"
    local old=${previous#releases/}
    if [ "$NEW_RELEASE" = 1 ]; then
        rm -rf -- "${PREFIX:?}/$failed"
        say "đã xoá bản lỗi $failed"
    fi
    systemctl reset-failed beacon 2>/dev/null || true
    if systemctl restart beacon && health "$(port)" "$old" "$HEALTH_TIMEOUT"; then
        say "đã quay về $old (cả unit lẫn mã)"
        finish rolled-back
        exit 1
    fi
    die "đã trỏ về $old nhưng $old cũng không lên: cần người xem ngay"
}

main "$@"
