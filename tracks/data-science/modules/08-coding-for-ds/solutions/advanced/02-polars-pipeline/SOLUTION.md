# Hướng làm: polars lazy và chọn công cụ

## pipeline.py

```python
import polars as pl

COLUMNS = ["seller_id", "n_orders", "revenue", "late_rate", "review_score", "bad_review_rate"]


def _done(orders: pl.LazyFrame) -> pl.LazyFrame:
    return (orders
            .filter((pl.col("order_status") == "delivered") & pl.col("order_delivered_customer_date").is_not_null())
            .select("order_id", "order_purchase_timestamp",
                    late=pl.col("order_delivered_customer_date") > pl.col("order_estimated_delivery_date")))


def seller_scorecard(orders, items, reviews):
    done = _done(orders)
    latest = reviews.group_by("order_id").agg(
        pl.col("review_score").sort_by("review_answer_timestamp").last())
    revenue = (items.join(done.select("order_id"), on="order_id")
                    .group_by("seller_id").agg(revenue=pl.col("price").sum()))
    pairs = (items.select("seller_id", "order_id").unique()
                  .join(done, on="order_id")
                  .join(latest, on="order_id", how="left"))
    return (pairs.group_by("seller_id")
                 .agg(n_orders=pl.len(),
                      late_rate=pl.col("late").mean(),
                      review_score=pl.col("review_score").mean(),
                      bad_review_rate=(pl.col("review_score") <= 2).mean())
                 .join(revenue, on="seller_id")
                 .select(COLUMNS)
                 .sort("seller_id"))


def weekly_gmv(orders, items):
    return (items.join(_done(orders), on="order_id")
                 .group_by(week=pl.col("order_purchase_timestamp").dt.truncate("1w").dt.date())
                 .agg(gmv=pl.col("price").sum(), orders=pl.col("order_id").n_unique())
                 .sort("week")
                 .with_columns(wow_growth=pl.col("gmv") / pl.col("gmv").shift(1) - 1))
```

Điểm cần thấy:

- `sort_by(...).last()` **trong** `agg` chọn review mới nhất bất kể thứ tự dòng đầu vào. Sort cả bảng
  trước `group_by` rồi lấy `last()` cũng chạy, nhưng dựa vào việc `group_by` giữ thứ tự trong nhóm:
  đúng ở polars hiện tại nhưng là giả định ngầm, và test cố ý xáo thứ tự review.
- Null tự được bỏ qua trong `mean()`: `(null <= 2)` là null, nên `bad_review_rate` chỉ tính trên đơn có
  review, không cần `where` như bản pandas.
- Không có `collect()` nào bên trong: kế hoạch nguyên vẹn để optimizer làm việc. `explain()` cho thấy
  `order_items` chỉ đọc 3/7 cột, và `done` được dùng hai lần thì polars tự cache.
- `dt.truncate("1w")` cho thứ Hai đầu tuần. Tuần đầu (2016-09-12, 1 đơn) và tuần cuối (2018-08-27, 116
  đơn) là tuần dở dang; `wow_growth` ở hai đầu vô nghĩa (+27 436% và −91.6%). Một bảng điểm tốt bỏ hoặc
  đánh dấu chúng.

## Số liệu tham chiếu khi viết bài

Olist: 2 970 seller, tổng `n_orders` 97 811, doanh thu 13 220 248.93; 91 tuần, tuần cao nhất 2017-11-20
(Black Friday) với GMV 397 906.24 và 2 915 đơn, tăng 131% so với tuần trước.

Đo bảng điểm seller (dữ liệu đã nằm trong bộ nhớ, min của 3 lần, máy 16 nhân, tải trung bình 4–6):

| Dữ liệu | pandas vector hoá | polars lazy | DuckDB SQL |
| --- | --- | --- | --- |
| Olist ×1 (112 650 món) | 0.30 s | 0.035 s | 0.038 s |
| Olist ×10 (1 126 500 món) | 3.2 s | 0.50 s | 0.28 s |

Ba kết quả được kiểm bằng nhau trước khi so thời gian. Con số của bạn sẽ khác; điều được chấm là cách
đo và cách đọc, không phải con số.

## BENCHMARK.md tốt trông thế nào

- **Cách đo tái lập được**: máy, phiên bản, cỡ dữ liệu, đo gì (đọc file và biến đổi tách riêng), số
  lần lặp, min hay median và vì sao (min ít nhiễu bởi tải máy; median phản ánh trải nghiệm thường gặp).
- **Kiểm tính đúng trước tốc độ**: ba kết quả bằng nhau.
- **Giải thích có cơ chế**: pandas một luồng, mỗi `merge` tạo bản sao; polars và DuckDB đa luồng,
  vector hoá theo khối, optimizer đẩy projection/predicate xuống nguồn; khi đọc từ CSV/Parquet,
  lợi ích pushdown còn lớn hơn.
- **Khuyến nghị có điều kiện**: ở cỡ Olist mọi công cụ đều dưới một giây, nên đổi công cụ vì tốc độ là
  không đáng; đáng khi dữ liệu lớn hơn chục lần, khi pipeline chạy thường xuyên, hoặc khi bộ nhớ là
  nút thắt. Kèm chi phí chuyển đổi: học API, thư viện vẽ và sklearn nhận pandas/numpy (chuyển qua Arrow
  rẻ), review code của đồng nghiệp chưa quen polars. Lộ trình chuyển dần: bắt đầu từ bước nặng nhất,
  giữ test so kết quả với bản pandas.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Hàm đúng và lazy | 25 | Qua test; không `collect`/`to_pandas`/`map_elements` bên trong; review mới nhất không phụ thuộc thứ tự dòng |
| Phương pháp đo | 20 | Tái lập được; ít nhất 2 cỡ dữ liệu; lặp nhiều lần; tách đọc và biến đổi hoặc nói rõ; kiểm kết quả bằng nhau |
| Kết quả | 15 | Bảng thời gian (và bộ nhớ đỉnh nếu đo được) đúng với code đã chạy |
| Giải thích | 20 | Nêu đúng cơ chế (đa luồng, bản sao trung gian, pushdown), có dẫn chứng như `explain()` |
| Khuyến nghị | 20 | Có điều kiện và ngưỡng, nêu chi phí chuyển đổi và lộ trình; không kết luận "polars luôn tốt hơn" |

Đạt từ 70 điểm là đủ đem ra thảo luận với team.
