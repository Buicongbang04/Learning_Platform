#!/bin/sh
set -eu

die() { echo "fetch_release: $*" >&2; exit 1; }

[ $# -eq 1 ] || die "cách dùng: QUILLO_RELEASE_DIR=<thư mục bản phát hành> sh delivery/fetch_release.sh <thư mục đích>"
here=$(cd "$(dirname "$0")" && pwd)
dest=$1
version=$(sed -n 's/^QUILLO_VERSION=//p' "$here/release.lock")
pinned=$(sed -n 's/^QUILLO_SHA256=//p' "$here/release.lock")
expected=${QUILLO_RELEASE_SHA256:-$pinned}
name=quillo-$version.tar

printf '%s' "$version" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' || die "release.lock: QUILLO_VERSION không hợp lệ"
printf '%s' "$expected" | grep -Eq '^[0-9a-f]{64}$' || die "sha256 mong đợi của $name không hợp lệ: '$expected'"
[ -n "${QUILLO_RELEASE_DIR:-}" ] || die "đặt QUILLO_RELEASE_DIR=<thư mục chứa $name> (bản phát hành team product giao)"
src=$QUILLO_RELEASE_DIR/$name
[ -f "$src" ] || die "không thấy $src"

mkdir -p "$dest"
part=$dest/.$name.partial
trap 'rm -f "$part"' EXIT
cp --reflink=auto "$src" "$part"
actual=$(sha256sum "$part" | cut -d' ' -f1)
[ "$actual" = "$expected" ] || die "$name có sha256 $actual, khác bản đã ghim $expected: hỏi lại team product, đừng giao"
tar -xOf "$part" "quillo-$version/manifest.json" | grep -q "\"version\": \"$version\"" \
    || die "$name không có quillo-$version/manifest.json đúng version $version"
mv -f "$part" "$dest/$name"
trap - EXIT
echo "fetch_release: $name sha256 $actual"
