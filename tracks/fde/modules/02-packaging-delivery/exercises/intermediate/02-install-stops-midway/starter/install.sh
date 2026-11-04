#!/usr/bin/env bash
set -euo pipefail

BUNDLE=${1:?cách dùng: install.sh <bundle.tar>}
PREFIX=/opt/beacon
CONF=/etc/beacon/beacon.env
UNIT=/etc/systemd/system/beacon.service
LOG=/var/log/beacon/install.log

mkdir -p "$(dirname "$LOG")"
exec 2> >(tee -a "$LOG" >&2)

log() {
    printf '%s %s\n' "$(date -Is)" "$*" >&2
}

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT

log "giải nén $BUNDLE"
tar -xf "$BUNDLE" -C "$work"
src=$(find "$work" -mindepth 1 -maxdepth 1 -type d -name 'beacon-*' | head -n 1)
[ -n "$src" ] || { log "bundle không có thư mục beacon-*"; exit 1; }

log "kiểm sha256 theo manifest"
python3 - "$src" <<'PY'
import hashlib, json, sys
from pathlib import Path

root = Path(sys.argv[1])
manifest = json.loads((root / "manifest.json").read_text())
for name, meta in manifest["files"].items():
    sha = hashlib.sha256()
    with open(root / name, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            sha.update(chunk)
    if sha.hexdigest() != meta["sha256"]:
        sys.exit(f"sai sha256: {name}")
PY
version=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["version"])' "$src/manifest.json")

log "dừng beacon, thay bằng bản $version"
systemctl stop beacon 2>/dev/null || true
rm -rf -- "$PREFIX/current"
mkdir -p "$PREFIX/current"
cp -a "$src"/. "$PREFIX/current/"

id beacon >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin beacon
[ -f "$CONF" ] || install -D -m 0640 -o root -g beacon "$src/config/beacon.env" "$CONF"
install -m 0644 "$src/systemd/beacon.service" "$UNIT"
systemctl daemon-reload
systemctl enable --now beacon
systemctl restart beacon

log "chờ /healthz"
for _ in $(seq 60); do
    if python3 -c 'import json, sys, urllib.request
r = urllib.request.build_opener(urllib.request.ProxyHandler({})).open("http://127.0.0.1:8088/healthz", timeout=2)
sys.exit(json.load(r)["version"] != sys.argv[1])' "$version" 2>/dev/null; then
        log "beacon $version đang chạy"
        exit 0
    fi
    sleep 1
done
log "beacon $version không trả lời /healthz"
exit 1
