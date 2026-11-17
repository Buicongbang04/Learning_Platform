#!/bin/sh
set -eu

die() { echo "install.sh: $*" >&2; exit 1; }

here=$(cd "$(dirname "$0")" && pwd)

# TODO 1: chép heartbeat.sh vào một chỗ cố định trong $HOME (không chạy thẳng từ thư mục bundle).
# TODO 2: đặt heartbeat.service vào đúng thư mục unit của systemd --user.
# TODO 3: nạp lại cấu hình systemd của user, bật dịch vụ để nó tự chạy và chạy ngay.
# TODO 4: dịch vụ phải sống cả khi không còn ai đăng nhập.
# TODO 5: chạy lại lần hai vẫn thoát 0, không nhân đôi gì.
die "chưa viết ($here)"
