#!/usr/bin/env bash
# Đếm số đơn theo order_status trong một CSV đơn hàng.
# Cách dùng: report.sh <orders.csv>
set -euo pipefail

# TODO 1: thiếu tham số => in "Usage: ..." ra stderr, exit 2

# TODO 2: tệp không tồn tại => báo lỗi ra stderr, exit 1

# TODO 3: tìm số thứ tự cột order_status trong header; không có => stderr, exit 1

# TODO 4: in "order_status,count" rồi các dòng "<status>,<count>" (count giảm dần, status tăng dần)
#         ra stdout; in "total=<n>" ra stderr

echo "TODO: chưa làm" >&2
exit 99
