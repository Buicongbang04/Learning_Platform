#!/bin/sh
set -eu

die() { echo "fetch_compose: $*" >&2; exit 1; }

[ $# -eq 1 ] || die "cách dùng: [COMPOSE_BIN=<binary đã tải>] sh delivery/fetch_compose.sh <tệp đích>"
root=$(cd "$(dirname "$0")/.." && pwd)
dest=$1
version=v5.6.1
pinned=47737f4236e6d3ccea7291995203f8f018058783b4c3a9469119811a0b5db8c0
url=https://github.com/docker/compose/releases/download/$version/docker-compose-linux-x86_64

src=${COMPOSE_BIN:-}
if [ -z "$src" ]; then
    src=$root/.cache/docker-compose-$version-linux-x86_64
    if [ ! -f "$src" ] || [ "$(sha256sum "$src" | cut -d' ' -f1)" != "$pinned" ]; then
        mkdir -p "$root/.cache"
        curl -q -fsSL --proto '=https' --retry 2 -o "$src.partial" "$url" || die "tải $url lỗi"
        mv -f "$src.partial" "$src"
    fi
fi
[ -f "$src" ] || die "không thấy $src"

mkdir -p "$(dirname "$dest")"
cp "$src" "$dest.partial"
actual=$(sha256sum "$dest.partial" | cut -d' ' -f1)
if [ "$actual" != "$pinned" ]; then
    rm -f "$dest.partial"
    die "docker compose $version có sha256 $actual, khác bản ghim $pinned"
fi
chmod 0755 "$dest.partial"
mv -f "$dest.partial" "$dest"
