#!/bin/sh
set -eu

usage() { echo "Cách dùng: sudo sh configure_proxy.sh <proxy url> <ca.pem>" >&2; exit 2; }
die() { echo "configure_proxy: $*" >&2; exit 1; }

[ $# -eq 2 ] || usage
proxy=$1
ca=$2

# TODO 1: kiểm đầu vào (chạy bằng root, proxy dạng http://host:port, $ca là chứng chỉ PEM đọc được).
# TODO 2: để mọi chương trình trên máy tin chứng chỉ CA của bệnh viện.
# TODO 3: biến môi trường cho shell đăng nhập mới (đủ cả chữ thường lẫn chữ hoa, kèm danh sách đi thẳng).
# TODO 4: apt chạy bằng sudo cũng đi qua proxy.
# TODO 5: Docker daemon đi qua proxy; chỉ restart khi cấu hình thật sự đổi.
# TODO 6: chạy lại lần hai không nhân đôi dòng nào, vẫn thoát 0.
die "chưa viết"
