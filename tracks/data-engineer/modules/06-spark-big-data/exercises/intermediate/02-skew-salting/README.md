---
title: Phát hiện data skew và xử lý bằng salting
level: intermediate
services: []
files:
  - path: starter/skew.py
    note: 5 TODO
  - path: tests/test_skew.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/06-spark-big-data/exercises/intermediate/02-skew-salting -q
---

## Mục tiêu

Đo được skew (phân bố key, kích thước từng partition), hiểu vì sao một key nóng dồn hết vào một task,
và dùng salting cho cả join lẫn aggregation mà kết quả không đổi.

## Đề bài

Bảng `order_items(order_id, seller_id, price)` trong đó một seller "nóng" chiếm phần lớn dòng, và bảng
`sellers(seller_id, seller_state)` nhỏ. Sửa `starter/skew.py`:

1. `key_distribution(df, key)`: list tuple `(key_value, count)` sắp xếp count giảm dần, hoà thì key tăng dần.
2. `partition_sizes(df)`: list số dòng của từng partition **không rỗng** của `df` (theo
   `spark_partition_id()`), sắp xếp giảm dần.
3. `add_salt(df, n_salt)`: thêm cột `salt` kiểu int trong `[0, n_salt)`, phân bố gần đều.
4. `salted_join(big, small, key, n_salt)`: inner join `big` và `small` theo `key` bằng kỹ thuật salting
   (salt bên lớn, nhân bản bên nhỏ `n_salt` lần). Kết quả có đúng các cột như `big.join(small, key)`
   (không còn cột `salt`) và cùng tập dòng.
5. `salted_count(df, key, n_salt)`: đếm số dòng theo `key` bằng aggregation hai tầng (theo
   `key, salt` rồi theo `key`). Cột `key`, `cnt`.

## Tiêu chí đạt

- `partition_sizes(big.repartition(4, "seller_id"))` cho thấy một partition chứa toàn bộ seller nóng.
- Sau `add_salt` rồi `repartition(4, "seller_id", "salt")`, partition lớn nhất nhỏ hơn hẳn.
- `salted_join` và `salted_count` cho kết quả giống hệt phiên bản không salt.
- Tất cả test pass.

## Gợi ý

### Gợi ý 1

`df.groupBy(F.spark_partition_id().alias("pid")).count()`. Salt: `(F.rand(seed) * n).cast("int")`
hoặc `F.pmod(F.monotonically_increasing_id(), F.lit(n))`.

### Gợi ý 2

Bên nhỏ: `small.crossJoin(spark.range(n_salt).select(F.col("id").cast("int").alias("salt")))`. Lấy
SparkSession từ DataFrame bằng `big.sparkSession`. Join theo `[key, "salt"]` rồi `.drop("salt")`, cuối
cùng `select(*big.columns, *[c for c in small.columns if c != key])` để giữ thứ tự cột.
