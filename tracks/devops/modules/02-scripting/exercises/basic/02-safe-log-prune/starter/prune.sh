#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 -d <thư mục> -a <số ngày> [-p <glob>] [-n]" >&2
  exit 2
}

dir=""
days=""
pattern='*.log.*'
dry_run=0

# TODO 1: đọc -d, -a, -p, -n bằng getopts; thiếu -d hoặc -a, -a không phải số nguyên >= 1,
#         option lạ hoặc tham số thừa thì usage
# TODO 2: thư mục không tồn tại -> exit 1; đường dẫn thật (đã giải symlink) là / hoặc chỉ một cấp dưới /
#         (như /var, /tmp, /home) -> từ chối, exit 1, không gọi find hay rm
# TODO 3: tìm tệp thường (không theo symlink) khớp glob, cũ hơn số ngày theo đúng -mtime +<số ngày>;
#         xử lý được tên có dấu cách và tên bắt đầu bằng dấu gạch ngang
# TODO 4: in "deleted <đường dẫn>" (hoặc "would delete <đường dẫn>" khi -n) cho từng tệp, rồi "total=<n>" ra stderr

echo "dir=$dir days=$days pattern=$pattern dry_run=$dry_run" >&2
usage
