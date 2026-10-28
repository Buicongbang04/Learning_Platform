---
title: Ước tính hoá đơn cloud - lưu trữ, egress, scan
level: basic
services: []
files:
  - path: starter/cost.py
    note: 4 TODO
  - path: tests/test_cloud_cost.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/11-cloud/exercises/basic/02-cloud-cost-estimate -q
---

## Mục tiêu

Tự tính được ba khoản chi phí hay gây "sốc hoá đơn" nhất của một data platform: lưu trữ object
storage, **egress** (dữ liệu đi ra internet) và **scan** của warehouse serverless.

## Đề bài

Giá trong `starter/cost.py` là giá **minh hoạ** gần với AWS/GCP vùng US (không phải bảng giá
chính thức, luôn tra pricing calculator khi làm thật). Hoàn thiện 4 hàm:

1. `storage_cost(gb, price_per_gb_month=0.023, months=1) -> float`: `gb * giá * số tháng`.
   `gb` hoặc `months` âm thì `ValueError`.
2. `egress_cost(gb, tiers=EGRESS_TIERS) -> float`: tính **lũy tiến theo bậc** như thuế thu nhập.
   `EGRESS_TIERS` là list `(giới hạn trên của bậc tính bằng GB, giá mỗi GB)`, giới hạn cộng dồn,
   bậc cuối có giới hạn `math.inf`. Mặc định 100 GB đầu miễn phí, tới 10 TB giá 0.09, tới 50 TB
   giá 0.085, tới 150 TB giá 0.07, phần còn lại 0.05 (1 TB = 1024 GB).
   Vd. 1124 GB = 100 x 0 + 1024 x 0.09 = 92.16.
3. `scan_cost(tb_scanned, price_per_tb=6.25, free_tb=1.0) -> float`: kiểu BigQuery on-demand,
   mỗi tháng `free_tb` TB đầu miễn phí, phần vượt nhân giá. Không bao giờ âm.
4. `monthly_bill(storage_gb, egress_gb, scanned_tb, storage_price=0.023) -> dict`: trả dict có
   đúng các khoá `storage`, `egress`, `scan`, `total`, mỗi giá trị **làm tròn 2 chữ số**, `total`
   là tổng của ba khoản (đã làm tròn).

## Tiêu chí đạt

- `storage_cost(1000) == 23.0`, `storage_cost(1000, 0.0125, months=12) == 150.0`.
- `egress_cost(100) == 0`, `egress_cost(1124) == 92.16`, đúng ở ranh giới các bậc và với bậc tự định nghĩa.
- `scan_cost(0.5) == 0`, `scan_cost(3) == 12.5`.
- `monthly_bill` đúng khoá, đúng giá trị, `total` khớp tổng.
- Tham số âm ném `ValueError`.

## Gợi ý

### Gợi ý 1

Với egress, giữ biến `lower = 0`; mỗi bậc `(upper, price)` lấy phần `min(gb, upper) - lower` nếu
dương, cộng `phần * price`, rồi gán `lower = upper`. Dừng khi `gb <= upper`.

### Gợi ý 2

`round(x, 2)` trước khi đưa vào dict; `total` cộng ba số đã làm tròn rồi làm tròn lại lần nữa để
tránh `0.30000000000000004`.
