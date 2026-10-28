---
title: Window functions trên Spark - dedup, running total, xếp hạng
level: intermediate
services: []
files:
  - path: starter/windows.py
    note: 3 TODO
  - path: tests/test_windows.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/06-spark-big-data/exercises/intermediate/03-window-functions -q
---

## Mục tiêu

Dùng `Window` của PySpark cho ba bài toán hay gặp trong pipeline: lấy bản ghi mới nhất theo key
(dedup CDC), tổng luỹ kế theo thời gian và xếp hạng trong nhóm. Hiểu window cũng gây shuffle theo
`partitionBy`.

## Đề bài

Sửa `starter/windows.py`:

1. `latest_status(updates)`: `updates(order_id, order_status, updated_at timestamp)` chứa nhiều phiên
   bản trạng thái của mỗi đơn (giống bảng CDC). Trả về đúng một dòng mỗi `order_id`: dòng có
   `updated_at` lớn nhất. Nếu hai dòng cùng `updated_at`, ưu tiên `order_status` theo thứ tự chữ cái
   lớn hơn (để kết quả tất định). Cột giữ nguyên như đầu vào.
2. `running_revenue(daily)`: `daily(seller_id, order_date date, revenue double)`. Thêm cột
   `cumulative_revenue`: tổng `revenue` từ ngày đầu tới ngày hiện tại của từng seller (làm tròn 2).
3. `top_sellers_by_state(sales, n)`: `sales(seller_id, seller_state, revenue)`. Thêm cột `rank`
   (`dense_rank` theo `revenue` giảm dần trong từng `seller_state`) và chỉ giữ các dòng `rank <= n`.
   Sắp xếp kết quả theo `seller_state`, `rank`, `seller_id`.

## Tiêu chí đạt

- `latest_status` dùng `row_number()` trên window, không dùng `groupBy` + join ngược.
- `running_revenue` dùng frame `rowsBetween(Window.unboundedPreceding, Window.currentRow)`.
- Seller đồng hạng nhận cùng `rank`, hạng sau không bị nhảy số.
- Tất cả test pass.

## Gợi ý

### Gợi ý 1

`w = Window.partitionBy("order_id").orderBy(F.desc("updated_at"), F.desc("order_status"))`, rồi
`F.row_number().over(w)`, giữ `== 1`, `drop` cột phụ.

### Gợi ý 2

`dense_rank` khác `rank`: hai seller hạng 1 thì người tiếp theo là hạng 2 (dense) chứ không phải 3.
