# Lời giải: CTE đệ quy, date spine và gaps-and-islands

## category_tree.sql

CTE đệ quy gồm anchor (các gốc, `parent_id IS NULL`, `depth = 0`, `path = name`) và bước đệ quy nối
`categories` với các dòng sinh ở vòng trước qua `c.parent_id = t.category_id`, tăng `depth` và nối
`path`. Engine lặp tới khi bước đệ quy không sinh dòng mới, nên đúng với cây sâu bao nhiêu cũng được.

- `CAST(name AS VARCHAR)` ở anchor: kiểu của cột được quyết định bởi anchor. Trên PostgreSQL, nếu
  `name` là `varchar(50)` mà `path` dài hơn sẽ lỗi, nên ép sang `text`.
- `WHERE t.depth < 50` là chốt chặn chống vòng lặp vô hạn khi dữ liệu bẩn có chu trình (A là cha
  B, B là cha A). PostgreSQL 14+ có cú pháp `CYCLE category_id SET is_cycle USING path_ids`.

## category_rollup.sql

Ba bước:

1. `own`: doanh thu trực tiếp của mỗi danh mục. `LEFT JOIN` từ `categories` để danh mục không có
   sản phẩm/đơn vẫn xuất hiện, `COALESCE(..., 0)` đổi `NULL` thành `0`.
2. `closure`: bảng bắc cầu (transitive closure) `(ancestor_id, descendant_id)`. Anchor ghép mỗi
   danh mục với chính nó, bước đệ quy thêm con của descendant hiện tại. Kết quả có mọi cặp tổ
   tiên – con cháu, kể cả chính nó.
3. Join `own` (tổ tiên) → `closure` → `own` (con cháu) và cộng `own_revenue` của con cháu.

Closure table cũng là một cách *lưu* cây trong OLTP (cùng với adjacency list `parent_id`, nested set,
materialized path như `ltree` của PostgreSQL). Nó đổi dung lượng lấy truy vấn "mọi con cháu" nhanh.

Sai lầm thường gặp: cộng doanh thu dọc theo đường đi từ con lên cha bằng đệ quy rồi `SUM`, dễ đếm
trùng khi một danh mục có nhiều con. Closure + `SUM` theo cặp không đếm trùng vì mỗi cặp
(ancestor, descendant) xuất hiện đúng một lần trong cây.

## daily_sales_filled.sql

Date spine sinh mọi ngày từ `MIN` tới `MAX` rồi `LEFT JOIN` với tổng theo ngày. Gộp theo ngày
**trước** khi join, nếu không ngày có 2 giao dịch sẽ nhân dòng. `COALESCE(amount, 0)` cho ngày trống.

Trong DuckDB/PostgreSQL, cách ngắn hơn:

```sql
SELECT CAST(d AS DATE) AS sale_date
FROM generate_series(DATE '2018-01-01', DATE '2018-01-06', INTERVAL 1 DAY) AS t(d)
```

Trong warehouse thật, người ta thường có sẵn bảng `dim_date` (module 02) thay vì sinh mỗi lần.

## customer_streaks.sql

Mẹo gaps-and-islands: với dãy tháng liên tiếp, `month_idx - ROW_NUMBER()` là hằng số.

| tháng | month_idx | row_number | hiệu |
| --- | --- | --- | --- |
| 2017-11 | 24215 | 1 | 24214 |
| 2017-12 | 24216 | 2 | 24214 |
| 2018-01 | 24217 | 3 | 24214 |
| 2018-03 | 24219 | 4 | 24215 |

- `DISTINCT` trước khi đánh số: c1 có hai đơn tháng 1/2018, nếu không loại trùng thì dãy bị gãy.
- `year * 12 + month` biến tháng thành số nguyên liên tục qua ranh giới năm (12/2017 → 1/2018 cách
  nhau 1). Trừ trực tiếp số tháng (`month(...)`) sẽ sai ở chỗ này.
- Cùng mẫu này giải được: chuỗi ngày đăng nhập liên tiếp, khoảng thời gian máy chủ down, gom các
  khoảng giá không đổi.
