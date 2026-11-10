#!/bin/sh
set -eu

here=$(cd "$(dirname "$0")" && pwd)

# TODO 1: kiểm bundle còn nguyên vẹn trước khi cài.
# TODO 2: đặt runtime Python vào $HOME, không đụng Python của hệ thống.
# TODO 3: tạo môi trường cho app, cài phụ thuộc và app chỉ từ $here, không cần mạng.
# TODO 4: ~/.local/bin/census chạy được ở mọi phiên, kể cả khi PATH tối thiểu; chạy lại lần hai vẫn thoát 0.
echo "install.sh: chưa viết ($here)" >&2
exit 1
