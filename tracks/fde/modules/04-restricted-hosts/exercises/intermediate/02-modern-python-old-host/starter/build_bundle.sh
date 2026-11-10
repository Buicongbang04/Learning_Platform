#!/bin/sh
set -eu

[ $# -eq 3 ] || { echo "Cách dùng: sh build_bundle.sh <thư mục app> <thư mục công cụ> <thư mục bundle>" >&2; exit 2; }
app=$(cd "$1" && pwd)
tools=$(cd "$2" && pwd)
out=$3
here=$(cd "$(dirname "$0")" && pwd)

# TODO 1: lấy runtime Python mang theo từ $tools, kiểm sha256 đã ghim trước khi dùng.
# TODO 2: xuất phụ thuộc đã ghim trong uv.lock (có hash) và dựng wheel của app.
# TODO 3: tải wheel khớp với runtime và máy đích (không phải máy bạn).
# TODO 4: chép install.sh vào bundle, ghi checksum cho mọi tệp.
echo "build_bundle.sh: chưa viết ($app, $tools -> $out, $here)" >&2
exit 1
