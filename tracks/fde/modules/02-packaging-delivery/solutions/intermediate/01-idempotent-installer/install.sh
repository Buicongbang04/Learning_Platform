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
import hashlib, json, os, sys
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
    found = set()
    for top, _, names in os.walk(root):
        for name in names:
            found.add(os.path.relpath(os.path.join(top, name), root))
    for name in sorted(found - set(files) - {"manifest.json"}):
        problems.append(f"tệp thừa: {name}")
    for name, meta in sorted(files.items()):
        path = os.path.join(root, name)
        if not os.path.isfile(path) or os.path.islink(path):
            problems.append(f"thiếu tệp: {name}")
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
        say "đã giải nén và kiểm tra $release"
    fi

    id beacon >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin beacon
    if [ ! -f "$CONF" ]; then
        install -D -m 0640 -o root -g beacon "$release/config/beacon.env" "$CONF"
        say "tạo $CONF từ cấu hình mặc định"
    fi
    if ! cmp -s "$release/systemd/beacon.service" "$UNIT"; then
        install -m 0644 "$release/systemd/beacon.service" "$UNIT"
        systemctl daemon-reload
    fi
    systemctl is-enabled --quiet beacon || systemctl enable --quiet beacon

    local previous
    previous=$(current_release)
    if [ "$previous" != "$target" ]; then
        switch_to "$target"
    fi
    systemctl restart beacon
    if health "$(port)" "$VERSION" "$HEALTH_TIMEOUT"; then
        prune "$target" "$previous"
        say "beacon $VERSION đang chạy"
        finish installed
        return 0
    fi
    say "beacon $VERSION không trả lời /healthz sau ${HEALTH_TIMEOUT}s"
    if [ -n "$previous" ] && [ "$previous" != "$target" ] && [ -d "$PREFIX/$previous" ]; then
        switch_to "$previous"
        systemctl restart beacon
        local old=${previous#releases/}
        if health "$(port)" "$old" "$HEALTH_TIMEOUT"; then
            say "đã quay về $old"
            finish rolled-back
            exit 1
        fi
    fi
    die "beacon không lên và không có bản trước để quay về"
}

main "$@"
