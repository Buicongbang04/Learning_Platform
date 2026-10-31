#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 [-k số_bản_giữ] <thư_mục_backup>" >&2
  exit 2
}

keep=7
backup_date="${BACKUP_DATE:-$(date -u +%F)}"

# TODO 1: đọc -k bằng getopts (số nguyên >= 1), đúng một tham số vị trí là thư mục; kiểm BACKUP_DATE dạng YYYY-MM-DD
# TODO 2: export PGHOST/PGPORT/PGUSER/PGDATABASE (mặc định localhost/25432/olist/olist); umask để tệp chỉ chủ đọc được;
#         tạo thư mục nếu chưa có
# TODO 3: khoá bằng flock -n trên <thư mục>/.backup.lock; đang có bản khác chạy -> exit 75
# TODO 4: đã có olist-<ngày>.dump và checksum khớp -> "skip <đường dẫn>", exit 0
# TODO 5: pg_dump định dạng custom vào tệp tạm trong cùng thư mục; trap dọn tệp tạm khi lỗi hoặc bị INT/TERM;
#         dump rỗng là lỗi; ghi .sha256 rồi mv vào tên thật; in "created <đường dẫn>"
# TODO 6: chỉ khi thành công: giữ <keep> bản olist-YYYY-MM-DD.dump mới nhất, xoá bản cũ hơn cùng .sha256 của nó

echo "keep=$keep date=$backup_date" >&2
usage
