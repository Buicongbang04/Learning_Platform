---
title: MapReduce bằng tay và bằng RDD
level: basic
services: []
files:
  - path: starter/mapreduce.py
    note: 5 TODO
  - path: tests/test_mapreduce.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/06-spark-big-data/exercises/basic/03-rdd-mapreduce -q
---

## Mục tiêu

Hiểu ba pha map, shuffle, reduce bằng cách tự cài bằng Python thuần, rồi viết lại cùng logic bằng RDD
API (`map`, `reduceByKey`, `takeOrdered`) để thấy Spark làm gì thay bạn.

## Đề bài

Đầu vào là danh sách dòng CSV `order_id,product_category` (không có header), ví dụ
`"o1,health_beauty"`. Category có thể viết hoa/thường lẫn lộn, có khoảng trắng, hoặc rỗng.

Sửa `starter/mapreduce.py`:

1. `map_phase(lines)`: trả về list cặp `(category, 1)`. Category chuẩn hoá: `strip()` + `lower()`.
   Dòng có category rỗng thì bỏ qua (không sinh cặp nào).
2. `shuffle_phase(pairs)`: gom thành `dict` `{category: [1, 1, ...]}`, key sắp xếp tăng dần.
3. `reduce_phase(groups)`: trả về `dict` `{category: tổng}`.
4. `rdd_category_count(sc, lines)`: cùng kết quả nhưng dùng RDD (`sc.parallelize`, `map`/`filter`,
   `reduceByKey`), trả về list tuple `(category, count)` sắp xếp theo category.
5. `top_categories(sc, lines, n)`: `n` category nhiều nhất, sắp theo count giảm dần, hoà thì theo
   tên tăng dần. Dùng RDD.

## Tiêu chí đạt

- Ba hàm map/shuffle/reduce chỉ dùng Python thuần.
- Hai hàm RDD dùng `reduceByKey` (không dùng `groupByKey`, không `collect()` rồi đếm bằng Python).
- Tất cả test pass.

## Gợi ý

### Gợi ý 1

`collections.defaultdict(list)` cho shuffle. Với RDD: `sc.parallelize(lines, 3)` để có nhiều partition.

### Gợi ý 2

`rdd.takeOrdered(n, key=lambda kv: (-kv[1], kv[0]))`. Hàm truyền vào `map`/`filter` được pickle gửi
sang Python worker: không tham chiếu `sc` hay SparkSession trong đó. Vì test nạp tệp của bạn như một
module mà worker không import được, hàm phụ trợ (vd. `parse`) phải là lambda hoặc định nghĩa **bên trong**
hàm RDD, không gọi hàm ở mức module.
