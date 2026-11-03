#!/bin/sh
set -eu

usage() { echo "Cách dùng: sh pack_usb.sh <quillo-X.Y.Z.tar> <thư mục công cụ> <thư mục USB>" >&2; exit 2; }
die() { echo "pack_usb: $*" >&2; exit 1; }

[ $# -eq 3 ] || usage
bundle=$1
tools=$2
usb=$3
here=$(cd "$(dirname "$0")" && pwd)

# TODO 1: kiểm bundle và mọi công cụ bạn mang theo (phiên bản + sha256 đã ghim) trước khi chép.
# TODO 2: chép vào $usb: bundle (giữ tên quillo-X.Y.Z.tar), công cụ, và $here/install.sh.
# TODO 3: ghi tệp checksum cho toàn bộ USB để phía khách kiểm trước khi cài.
die "chưa viết"
