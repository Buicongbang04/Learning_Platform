#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <thư mục>" >&2
  exit 2
}

[[ $# -eq 1 ]] || usage
root="$1"

# TODO 1: thư mục không tồn tại -> báo lỗi ra stderr, exit 2
# TODO 2: tìm 6 loại phát hiện, in "<loại> <đường dẫn tương đối>" đã sắp xếp
# TODO 3: exit 1 nếu có phát hiện, 0 nếu sạch; không sửa quyền của tệp nào

echo "TODO: chưa viết perm_audit.sh ($root)" >&2
exit 99
