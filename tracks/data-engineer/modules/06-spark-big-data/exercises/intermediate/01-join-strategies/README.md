---
title: Join strategies - broadcast và sort-merge
level: intermediate
services: []
files:
  - path: starter/joins.py
    note: 3 TODO
  - path: tests/test_joins.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/06-spark-big-data/exercises/intermediate/01-join-strategies -q
---

## Mục tiêu

Điều khiển chiến lược join của Spark (Broadcast Hash Join và Sort-Merge Join), đọc physical plan để
xác nhận, và thay đổi cấu hình SparkSession một cách an toàn (khôi phục lại sau khi dùng).

## Đề bài

Có `order_items` (lớn, cột `order_id, product_id, price`) và `products` (nhỏ, cột
`product_id, product_category_name`). Hàm `plan_string(df)` đã viết sẵn, trả về physical plan dạng chuỗi.

Sửa `starter/joins.py`:

1. `broadcast_join(items, products)`: inner join theo `product_id` với hint broadcast cho `products`.
   Plan phải có `BroadcastHashJoin`.
2. `sort_merge_join(spark, items, products)`: inner join theo `product_id` **không** dùng hint, và tắt
   broadcast tự động (`spark.sql.autoBroadcastJoinThreshold = -1`) trong lúc lập plan và chạy. Trả về
   tuple `(rows, plan)`: `rows` là list `Row` đã `collect()`, `plan` là `plan_string(...)` của DataFrame
   join. Plan phải có `SortMergeJoin`. **Sau khi hàm trả về** (kể cả khi có lỗi), giá trị cấu hình
   `spark.sql.autoBroadcastJoinThreshold` phải trở lại như trước khi gọi.
3. `revenue_by_category(items, products)`: doanh thu (`sum(price)`, làm tròn 2) theo
   `product_category_name`, dùng broadcast join; cột `product_category_name`, `revenue`, sắp xếp
   `revenue` giảm dần. Sản phẩm không có trong `products` bị loại (inner join).

## Tiêu chí đạt

- `plan_string(broadcast_join(...))` chứa `BroadcastHashJoin`.
- `sort_merge_join` trả plan chứa `SortMergeJoin`, kết quả cùng tập dòng với broadcast join.
- Cấu hình được khôi phục, kể cả khi người gọi đã đặt giá trị riêng (vd. `"20MB"`).
- Tất cả test pass.

## Gợi ý

### Gợi ý 1

`from pyspark.sql.functions import broadcast`; `items.join(broadcast(products), "product_id")`.

### Gợi ý 2

Plan được chọn khi DataFrame được lập kế hoạch lần đầu (lúc gọi action hoặc `explain`), nên phải lấy
plan và `collect()` **trong khi** cấu hình còn là `-1`. Dùng `try/finally` với
`old = spark.conf.get(key)` ... `spark.conf.set(key, old)`.
