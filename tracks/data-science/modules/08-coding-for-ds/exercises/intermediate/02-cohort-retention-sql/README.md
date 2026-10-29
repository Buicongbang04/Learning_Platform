---
title: Cohort retention của Olist bằng SQL
level: intermediate
services: []
files:
  - path: starter/cohort.ipynb
    note: 4 hàm TODO + kết luận
  - path: tests/test_cohort.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/08-coding-for-ds/exercises/intermediate/02-cohort-retention-sql/starter/cohort.ipynb
  - uv run pytest tracks/data-science/modules/08-coding-for-ds/exercises/intermediate/02-cohort-retention-sql -q
---

## Mục tiêu

Làm trọn câu SQL kinh điển nhất của phỏng vấn DS, "retention theo cohort tháng", trên dữ liệu thật,
kèm ba chi tiết phân biệt ứng viên senior: đơn vị khách đúng, 0% khác "chưa quan sát được", và trung
bình có trọng số.

## Đề bài

Mở `starter/cohort.ipynb`. Bảng `orders`, `customers` được nạp vào DuckDB trong cell `explore`.
Định nghĩa: đơn giao xong (`delivered` và có `order_delivered_customer_date`), mua trước `2018-09-01`;
khách là `customer_unique_id`; cohort là tháng của đơn giao xong đầu tiên.

1. `COHORT_SQL` và `cohort_counts(con)`: DataFrame `cohort` (datetime), `month_index` (int),
   `customers` (số khách khác nhau có đơn giao xong ở tháng đó). Một câu SQL.
2. `retention_matrix(counts, last_month)`: index cohort, cột `month_index` 0..K, giá trị tỉ lệ; ô chưa
   quan sát được (cohort + k sau `last_month`) là NaN, ô đã quan sát mà không ai quay lại là 0.
3. `average_retention(counts, k, last_month)`: retention tháng k trung bình **có trọng số** theo cỡ
   cohort, chỉ trên các cohort đã quan sát được tháng k.
4. `repeat_customer_rate(con)`: tỉ lệ khách có từ 2 đơn giao xong.
5. Vẽ heatmap (cell `explore`) và viết kết luận 4–6 câu cho stakeholder ở cell cuối.

## Tiêu chí đạt

- `cohort_counts` đúng trên dữ liệu test: gộp khách theo `customer_unique_id`, đếm khách một lần mỗi
  tháng, loại đơn huỷ, đơn chưa giao xong, đơn sau 2018-08-31.
- `retention_matrix` phân biệt 0 và NaN; `average_retention` có trọng số và bỏ cohort chưa quan sát được.
- Trên Olist thật: 93 350 khách; cohort 2017-11 có 7 059 khách, 40 khách quay lại tháng 1; retention
  tháng 1 trung bình ≈ 0.483%; tỉ lệ khách mua lại ≈ 3.00%.
- Kết luận có số liệu và nêu ít nhất một hạn chế của dữ liệu (không chấm tự động).

## Gợi ý

### Gợi ý 1

Ba CTE: `delivered` (join `customers` để lấy `customer_unique_id`), `active` (`SELECT DISTINCT` khách,
`DATE_TRUNC('month', ...)::DATE`), `cohort` (`MIN(month)` mỗi khách). Cuối cùng join `active` với
`cohort`, `DATE_DIFF('month', cohort, month) AS month_index`, `COUNT(*)` theo hai cột. DuckDB trả cột
DATE về pandas dạng datetime; vẫn nên ép kiểu rõ ràng.

### Gợi ý 2

Số tháng đã quan sát được của cohort c: `(pd.Period(last_month, "M") − pd.Period(c, "M")).n`. Ô
`(c, k)` là NaN khi `k` lớn hơn số đó. Ma trận: `pivot` → `reindex` đủ cột → `fillna(0)` → chia cỡ
cohort → `mask`. Trung bình có trọng số: tổng `customers` ở tháng k chia tổng cỡ các cohort đủ điều
kiện, không phải `mean()` của cột. So hai cách trong cell `explore`: chênh lệch tới gần 10 lần.
