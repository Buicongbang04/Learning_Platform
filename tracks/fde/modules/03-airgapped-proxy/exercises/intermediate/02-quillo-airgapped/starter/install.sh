#!/bin/bash
set -euo pipefail

usb=$(cd "$(dirname "$0")" && pwd)
registry=${QUILLO_REGISTRY:-10.0.2.101:5000}

die() { echo "install: LỖI: $*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "cần chạy bằng root: sudo bash $0"

# TODO 1: kiểm toàn vẹn mọi thứ trên USB TRƯỚC khi đụng vào Docker hay registry.
# TODO 2: preflight: lệnh cần có, Docker chạy, chỗ trống, registry nội bộ trả lời.
# TODO 3: giải nén bundle, kiểm theo manifest.json bên trong.
# TODO 4: nạp image và đẩy lên registry nội bộ $registry.
# TODO 5: cấu hình (bí mật sinh tại chỗ, không nằm trên USB), compose chạy image từ registry nội bộ,
#         project tên quillo, API nghe được qua cổng forward của lab.
# TODO 6: chờ /healthz, ghi log.
die "chưa viết"
