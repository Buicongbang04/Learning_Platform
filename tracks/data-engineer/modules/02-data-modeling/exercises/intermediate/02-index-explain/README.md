---
title: Tối ưu ba truy vấn đơn hàng bằng composite và covering index
level: intermediate
services: []
files:
  - path: starter/indexes.sql
    note: 3 TODO
  - path: tests/test_indexes.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/02-data-modeling/exercises/intermediate/02-index-explain -q
---

## Mục tiêu

Đọc `EXPLAIN QUERY PLAN`, chọn đúng cột và **thứ tự cột** cho composite index, biết khi nào index
trở thành covering, và tối ưu với số index tối thiểu.

## Đề bài

Test tạo trong SQLite hai bảng (khoảng 20.000 đơn, 40.000 item), **không có index nào ngoài khoá
chính `orders.order_id`**:

```sql
orders (order_id TEXT PRIMARY KEY, customer_id TEXT, order_status TEXT, order_purchase_timestamp TEXT)
order_items (order_id TEXT, order_item_id INTEGER, product_id TEXT, seller_id TEXT,
             shipping_limit_date TEXT, price REAL, freight_value REAL)
```

Ba truy vấn nóng của ứng dụng (tham số cụ thể có thể khác):

```sql
-- Q1: màn hình seller xem các item phải giao từ một ngày trở đi
SELECT shipping_limit_date, price FROM order_items
WHERE seller_id = ? AND shipping_limit_date >= ? ORDER BY shipping_limit_date;

-- Q2: hàng đợi xử lý đơn theo trạng thái trong một khoảng thời gian
SELECT order_id, order_purchase_timestamp FROM orders
WHERE order_status = ? AND order_purchase_timestamp >= ? AND order_purchase_timestamp < ?;

-- Q3: lịch sử mua hàng của một khách
SELECT o.order_id, SUM(i.price) FROM orders o JOIN order_items i ON i.order_id = o.order_id
WHERE o.customer_id = ? GROUP BY o.order_id;
```

Viết `starter/indexes.sql` (các câu `CREATE INDEX`) sao cho:

- Q1 dùng **covering index**, tìm theo cả `seller_id` và `shipping_limit_date`, không cần sort tạm.
- Q2 dùng một index tìm theo **cả hai** điều kiện (`order_status=?` và khoảng thời gian).
- Q3 không quét toàn bảng nào (không có bước `SCAN`) và truy cập `order_items` bằng covering index.
- Tổng cộng **không quá 4 index** do bạn tạo.

## Tiêu chí đạt

- Plan của Q1 chứa `COVERING INDEX`, `seller_id=? AND shipping_limit_date>`, không có `TEMP B-TREE`.
- Plan của Q2 là `SEARCH` có cả `order_status=?` và `order_purchase_timestamp>`/`<`.
- Plan của Q3 không có `SCAN`, bước truy cập `order_items` là `COVERING INDEX`.
- Kết quả ba truy vấn giữ nguyên như trước khi tạo index; tối đa 4 index.

## Gợi ý

### Gợi ý 1

Chạy thử bằng Python: `con.execute("EXPLAIN QUERY PLAN " + sql).fetchall()`, cột thứ 4 là mô tả
bước. `SCAN` là quét toàn bảng, `SEARCH ... USING INDEX` là tìm bằng index,
`USE TEMP B-TREE FOR ORDER BY` là phải sort.

### Gợi ý 2

Cột so sánh bằng trước, cột khoảng/sắp xếp sau: `(seller_id, shipping_limit_date)`. Thêm các cột
SELECT cần vào cuối index để thành covering: `(seller_id, shipping_limit_date, price)`. Q3 cần một
index để tìm đơn theo khách và một index để tìm item theo `order_id` (kèm `price`).
