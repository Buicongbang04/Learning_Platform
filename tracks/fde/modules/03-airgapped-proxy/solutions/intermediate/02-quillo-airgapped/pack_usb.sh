#!/bin/sh
set -eu

usage() { echo "Cách dùng: sh pack_usb.sh <quillo-X.Y.Z.tar> <thư mục công cụ> <thư mục USB>" >&2; exit 2; }
die() { echo "pack_usb: $*" >&2; exit 1; }

[ $# -eq 3 ] || usage
bundle=$1
tools=$2
usb=$3
here=$(cd "$(dirname "$0")" && pwd)
compose_version=v5.6.1
compose_sha256=47737f4236e6d3ccea7291995203f8f018058783b4c3a9469119811a0b5db8c0
compose=$tools/docker-compose-$compose_version/docker-compose-linux-x86_64

name=$(basename "$bundle")
case $name in
    quillo-[0-9]*.[0-9]*.[0-9]*.tar) ;;
    *) die "tên bundle phải dạng quillo-X.Y.Z.tar, nhận $name" ;;
esac
[ -f "$bundle" ] || die "không thấy $bundle"
tar -tf "$bundle" "${name%.tar}/manifest.json" >/dev/null 2>&1 || die "$bundle không có ${name%.tar}/manifest.json"
[ -f "$compose" ] || die "thiếu $compose; tải theo README module (phần 0)"
echo "$compose_sha256  $compose" | sha256sum -c --quiet - || die "sha256 của $compose không khớp bản đã ghim"
[ ! -e "$usb" ] || [ -z "$(ls -A "$usb")" ] || die "$usb không rỗng"

created=0
[ -e "$usb" ] || created=1
cleanup() { [ $? -eq 0 ] || [ "$created" -eq 0 ] || rm -rf "$usb"; }
trap cleanup EXIT
mkdir -p "$usb/tools"
usb=$(cd "$usb" && pwd)
cp "$bundle" "$usb/$name"
cp "$compose" "$usb/tools/docker-compose"
cp "$here/install.sh" "$usb/install.sh"
cd "$usb"
sha256sum "$name" tools/docker-compose install.sh > SHA256SUMS
echo "USB sẵn sàng: $usb"
echo "Gửi riêng cho IT khách (email/điện thoại), không để chung USB:"
echo "  sha256(SHA256SUMS) = $(sha256sum SHA256SUMS | cut -d' ' -f1)"
