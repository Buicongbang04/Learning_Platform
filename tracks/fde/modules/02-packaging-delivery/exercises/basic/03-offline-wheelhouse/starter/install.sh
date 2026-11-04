#!/bin/sh
set -eu

here=$(cd "$(dirname "$0")" && pwd)
dest=$HOME/intake

# TODO 1: kiểm bundle còn nguyên vẹn trước khi cài
# TODO 2: tạo môi trường Python riêng ở $dest bằng /usr/bin/python3 của máy
# TODO 3: cài phụ thuộc và app chỉ từ $here, không cần mạng
# TODO 4: thử import app trước khi báo xong

echo "install.sh: chưa viết ($here -> $dest)" >&2
exit 1
