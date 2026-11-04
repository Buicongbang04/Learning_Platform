#!/bin/sh
set -eu

usage() { echo "Cách dùng: sudo sh publish.sh <image.tar> <registry host:port> <repo:tag>" >&2; exit 2; }
die() { echo "publish: $*" >&2; exit 1; }

[ $# -eq 3 ] || usage
archive=$1
registry=$2
target=$3

# TODO 1: kiểm đầu vào (root, tệp đọc được, registry dạng host:port, đích dạng repo:tag).
# TODO 2: để Docker daemon của máy này làm việc được với registry nội bộ $registry,
#         giữ nguyên mọi cấu hình IT đã có; chỉ restart daemon khi cấu hình thật sự đổi.
# TODO 3: nạp image từ $archive, gắn tên $registry/$target rồi đẩy lên.
# TODO 4: chạy lại lần hai vẫn thoát 0, không nhân đôi cấu hình.
die "chưa viết"
