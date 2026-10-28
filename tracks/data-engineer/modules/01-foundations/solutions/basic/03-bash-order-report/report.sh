#!/usr/bin/env bash
# Đếm số đơn theo order_status trong một CSV đơn hàng.
# Cách dùng: report.sh <orders.csv>
set -euo pipefail
export LC_ALL=C   # sort ổn định, không phụ thuộc locale máy

if [[ $# -lt 1 ]]; then
    echo "Usage: $(basename "$0") <orders.csv>" >&2
    exit 2
fi

file="$1"
if [[ ! -f "$file" ]]; then
    echo "Lỗi: không thấy tệp '$file'" >&2
    exit 1
fi

# Số thứ tự (1-based) của cột order_status trong header. tr -d '\r' để chịu được file CRLF.
col="$(head -n 1 "$file" | tr -d '\r' | tr ',' '\n' | grep -nx 'order_status' | cut -d: -f1 || true)"
if [[ -z "$col" ]]; then
    echo "Lỗi: header của '$file' không có cột order_status" >&2
    exit 1
fi

counts="$(
    tail -n +2 "$file" | tr -d '\r' \
        | awk -F, -v c="$col" 'NF > 0 { print $c }' \
        | sort | uniq -c \
        | sort -k1,1nr -k2,2 \
        | awk '{ print $2 "," $1 }'
)"

echo "order_status,count"
if [[ -n "$counts" ]]; then
    echo "$counts"
fi

total="$(printf '%s\n' "$counts" | awk -F, 'NF == 2 { s += $2 } END { print s + 0 }')"
echo "total=$total" >&2
