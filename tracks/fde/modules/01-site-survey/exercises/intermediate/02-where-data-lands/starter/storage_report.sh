#!/bin/sh
set -u

free_gb=$(df -P -k / | awk 'NR==2 {printf "%.2f", $4 / 1048576}')

# TODO 1: runtime nào user này dùng được, và nó thật sự ghi image/container vào thư mục nào (data_root)
# TODO 2: data_mount, data_free_gb, inodes_free_pct phải đo cho đúng thư mục đó, không phải cho /
# TODO 3: in đúng một object JSON 5 khoá như README

echo "storage_report.sh: chưa viết (mới đo / còn $free_gb GiB)" >&2
exit 1
