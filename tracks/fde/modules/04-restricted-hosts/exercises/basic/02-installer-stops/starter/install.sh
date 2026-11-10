#!/bin/sh
set -eu

bundle=${1:?cách dùng: sh install.sh <fieldsync-x.y.z.tar>}
prefix=$HOME/fieldsync

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

echo "install.sh: giải nén $bundle" >&2
tar -xf "$bundle" -C "$work"
src=$(find "$work" -mindepth 1 -maxdepth 1 -type d -name 'fieldsync-*' | head -n 1)
[ -n "$src" ] || { echo "install.sh: bundle không có thư mục fieldsync-*" >&2; exit 1; }

echo "install.sh: lập chỉ mục tài liệu" >&2
"$src/bin/fieldsync" build-index --assets "$src/assets" --out "$src/index.json"

echo "install.sh: cài vào $prefix" >&2
rm -rf "$prefix.new"
mkdir -p "$prefix.new"
cp -a "$src/bin" "$src/assets" "$src/index.json" "$prefix.new/"
rm -rf "$prefix.old"
[ ! -d "$prefix" ] || mv "$prefix" "$prefix.old"
mv "$prefix.new" "$prefix"
rm -rf "$prefix.old"
echo "install.sh: xong" >&2
