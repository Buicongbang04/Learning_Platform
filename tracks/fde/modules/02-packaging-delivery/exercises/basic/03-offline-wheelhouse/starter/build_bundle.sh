#!/bin/sh
set -eu

[ $# -eq 2 ] || { echo "Cách dùng: sh build_bundle.sh <thư mục app> <thư mục bundle>" >&2; exit 2; }
app=$(cd "$1" && pwd)
out=$2
here=$(cd "$(dirname "$0")" && pwd)

# TODO 1: lấy danh sách phụ thuộc đã ghim (kèm hash) từ uv.lock của app
# TODO 2: dựng wheel của chính app
# TODO 3: tải wheel của mọi phụ thuộc vào bundle, sao cho cài được trên MÁY ĐÍCH (không phải máy bạn)
# TODO 4: đưa install.sh (và những gì nó cần để chạy được ở máy đích) vào bundle

echo "build_bundle.sh: chưa viết ($app -> $out, install.sh ở $here)" >&2
exit 1
