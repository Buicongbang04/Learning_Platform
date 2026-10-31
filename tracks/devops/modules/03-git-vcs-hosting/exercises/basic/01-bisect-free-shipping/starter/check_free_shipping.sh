#!/usr/bin/env bash
set -uo pipefail

# TODO 1: chạy trong thư mục gốc repo (git bisect run đặt sẵn), gọi shipping_fee(200, "SP")
#         bằng python3 mà không ghi __pycache__ vào repo (python3 -B hoặc PYTHONDONTWRITEBYTECODE=1)
# TODO 2: không import được hoặc gọi hàm lỗi (SyntaxError, thiếu rates.json...) -> exit 125
# TODO 3: phí bằng 0 -> exit 0 (good); phí khác 0 -> exit 1 (bad)

exit 255
