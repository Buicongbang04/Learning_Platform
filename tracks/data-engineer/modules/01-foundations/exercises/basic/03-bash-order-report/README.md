---
title: Báo cáo trạng thái đơn hàng bằng Bash
level: basic
services: []
files:
  - path: starter/report.sh
    note: 4 TODO
  - path: tests/test_report.py
    note: Không sửa
run:
  - bash tracks/data-engineer/modules/01-foundations/exercises/basic/03-bash-order-report/starter/report.sh tracks/data-engineer/modules/01-foundations/exercises/basic/03-bash-order-report/tests/fixtures/orders.csv
  - uv run pytest tracks/data-engineer/modules/01-foundations/exercises/basic/03-bash-order-report -q
---

## Mục tiêu

Viết một script Bash "đàng hoàng": kiểm tra tham số, báo lỗi ra stderr với exit code có nghĩa, xử lý
text bằng pipe (`awk`, `sort`, `uniq`), tách dữ liệu (stdout) khỏi thông điệp (stderr).

## Đề bài

Hoàn thành `starter/report.sh`. Đầu vào là một CSV đơn hàng kiểu Olist (không có dấu phẩy trong
ngoặc kép), dòng đầu là header. Vị trí cột `order_status` **không cố định**: phải tìm theo tên trong
header.

Hành vi yêu cầu:

1. Gọi không có tham số: in dòng bắt đầu bằng `Usage:` ra **stderr**, exit code `2`.
2. Tệp không tồn tại: in thông báo lỗi ra stderr, exit code `1`.
3. Header không có cột `order_status`: thông báo lỗi ra stderr, exit code `1`.
4. Bình thường: in ra **stdout** một CSV:
   - dòng đầu `order_status,count`,
   - mỗi trạng thái một dòng `<status>,<số đơn>`,
   - sắp theo `count` giảm dần, bằng nhau thì theo tên trạng thái tăng dần,
   - bỏ qua dòng trống (kể cả dòng trống cuối file).
5. In ra **stderr** một dòng `total=<tổng số đơn>`, exit code `0`.

Ví dụ:

```bash
$ bash starter/report.sh tests/fixtures/orders.csv 2>/dev/null
order_status,count
delivered,5
shipped,2
canceled,1
invoiced,1
```

## Tiêu chí đạt

- Đúng nội dung stdout trên fixture và trên file có cột `order_status` ở vị trí khác.
- Đúng exit code `2` khi thiếu tham số, `1` khi thiếu file hoặc thiếu cột.
- Thông điệp lỗi và dòng `total=` đi ra stderr, stdout chỉ chứa CSV.
- Script có `set -euo pipefail`.

## Gợi ý

### Gợi ý 1

Lấy số thứ tự cột từ header:
`head -n 1 "$file" | tr ',' '\n' | grep -nx 'order_status' | cut -d: -f1`.
Nếu `grep` không thấy, nó trả mã 1; với `set -e` hãy bắt bằng `|| true` rồi kiểm tra biến rỗng.

### Gợi ý 2

```bash
tail -n +2 "$file" | awk -F, -v c="$col" 'NF > 0 {print $c}' \
  | sort | uniq -c | sort -k1,1nr -k2,2 | awk '{print $2 "," $1}'
```

`uniq -c` in `   5 delivered`; `sort -k1,1nr -k2,2` sắp số giảm dần rồi tên tăng dần.
