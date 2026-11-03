#!/usr/bin/env bash
set -euo pipefail

BUNDLE=${1:-}
LOG=/var/log/beacon/install.log

# TODO 1: preflight — chạy bằng root, có bundle, có các lệnh cần dùng; đọc manifest.json trong bundle (version, danh sách tệp)
# TODO 2: nếu đúng bản này đã cài và đang chạy khoẻ thì không đụng vào gì, ghi log "unchanged", thoát 0
# TODO 3: giải nén + kiểm sha256 theo manifest TRƯỚC khi đụng vào bản đang chạy; bundle hỏng thì không để lại gì
# TODO 4: user hệ thống, cấu hình /etc/beacon/beacon.env (không ghi đè sửa đổi của khách), unit systemd, enable
# TODO 5: chuyển sang bản mới, khởi động lại, chờ /healthz đúng version; bước nào lỗi thì quay về bản trước (cả unit)
# TODO 6: mỗi lần chạy, dòng cuối của $LOG là "<thời điểm> <version> <kết quả>"

echo "install.sh: chưa viết (bundle: ${BUNDLE:-thiếu})" >&2
exit 1
