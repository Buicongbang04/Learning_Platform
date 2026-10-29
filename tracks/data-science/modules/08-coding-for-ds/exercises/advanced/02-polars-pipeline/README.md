---
title: Viết lại pipeline bằng polars lazy và chọn công cụ
level: advanced
services: []
files:
  - path: starter/pipeline.py
    note: 2 hàm trả LazyFrame
  - path: starter/BENCHMARK.md
    note: Báo cáo đo và khuyến nghị
  - path: tests/test_pipeline.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run pytest tracks/data-science/modules/08-coding-for-ds/exercises/advanced/02-polars-pipeline -q
---

## Mục tiêu

Viết lại bảng điểm seller (bài Intermediate 03) và GMV theo tuần bằng polars lazy, rồi tự thiết kế
một phép đo công bằng giữa pandas, polars và DuckDB và đưa ra khuyến nghị công cụ cho team, có điều
kiện và chi phí chuyển đổi.

## Đề bài

1. `seller_scorecard(orders, items, reviews)` trong `starter/pipeline.py`: nhận ba `pl.LazyFrame`, trả
   `pl.LazyFrame` (chưa `collect`) với cột `seller_id`, `n_orders`, `revenue`, `late_rate`,
   `review_score`, `bad_review_rate`, cùng định nghĩa với `slow_seller_report` của bài Intermediate 03,
   sắp theo `seller_id`. Seller không có đơn nào có review: hai cột review là null.
2. `weekly_gmv(orders, items)`: `pl.LazyFrame` cột `week` (Date, thứ Hai đầu tuần), `gmv` (tổng `price`
   của đơn giao xong theo tuần mua), `orders` (số đơn khác nhau), `wow_growth` (gmv chia gmv của dòng
   trước, trừ 1; null ở dòng đầu), sắp theo `week`.
3. `starter/BENCHMARK.md`: đo cả ba công cụ trên Olist thật ở ít nhất hai cỡ dữ liệu (ví dụ ×1 và
   ×10), viết cách đo, bảng kết quả (thời gian, bộ nhớ đỉnh nếu đo được), giải thích chênh lệch, và
   khuyến nghị.

Không dùng `.to_pandas()`, `map_elements` hay lặp theo dòng bên trong hai hàm.

## Tiêu chí đạt

- Hai hàm trả `LazyFrame`; kết quả đúng trên dữ liệu tay (review mới nhất khi bảng review không sắp
  theo thời gian, tuần bắt đầu thứ Hai) và khớp một bản pandas tham chiếu trên 3 bộ dữ liệu ngẫu nhiên.
- `seller_scorecard` chạy xong 1 000 000 món hàng trong 20 giây.
- Trên Olist thật: 2 970 seller, tổng `n_orders` 97 811, tổng doanh thu 13 220 248.93; tuần GMV cao
  nhất là tuần 2017-11-20 (Black Friday) với 2 915 đơn.
- `BENCHMARK.md` không còn TODO, có bảng, ít nhất 300 từ; chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Review mới nhất: `reviews.group_by("order_id").agg(pl.col("review_score").sort_by("review_answer_timestamp").last())`.
Cặp (seller, đơn): `items.select("seller_id", "order_id").unique()`. `pl.len()` đếm dòng mỗi nhóm.
`(pl.col("review_score") <= 2).mean()` tự bỏ qua null. Tuần: `pl.col("order_purchase_timestamp")
.dt.truncate("1w").dt.date()`; tăng trưởng: `pl.col("gmv") / pl.col("gmv").shift(1) - 1`.

### Gợi ý 2

Đo công bằng: tách thời gian đọc file khỏi thời gian biến đổi (hoặc đo cả hai, nói rõ); chạy mỗi cách
vài lần, lấy min hoặc median và nói vì sao; kiểm ba kết quả bằng nhau trước khi so thời gian; ghi số
nhân CPU và tải máy. Xem `plan.explain()` để thấy projection pushdown. Nhân Olist lên 10 lần bằng cách
nối 10 bản sao và thêm hậu tố vào khoá (`order_id`, `seller_id`) để không bị trùng.
