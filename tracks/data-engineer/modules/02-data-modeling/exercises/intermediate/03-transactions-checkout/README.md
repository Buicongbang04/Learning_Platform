---
title: Đặt hàng nguyên tử và chống bán quá tồn kho
level: intermediate
services: [postgres]
files:
  - path: starter/checkout.py
    note: 2 TODO
  - path: tests/test_checkout.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/02-data-modeling/exercises/intermediate/03-transactions-checkout -q
  - docker compose -f setup/docker-compose.yml up -d postgres
  - uv run pytest tracks/data-engineer/modules/02-data-modeling/exercises/intermediate/03-transactions-checkout -q
---

## Mục tiêu

Dùng transaction để một nghiệp vụ nhiều bước "tất cả hoặc không gì cả", và dùng atomic conditional
update để không bị lost update khi nhiều request cùng trừ tồn kho.

## Đề bài

Trong `starter/checkout.py`:

1. `place_order(con, order_id, customer_id, items)` với `con` là `sqlite3.Connection`. Schema
   (do `create_schema(con)` tạo sẵn):

   ```sql
   stock (product_id TEXT PRIMARY KEY, qty INTEGER NOT NULL CHECK (qty >= 0))
   orders (order_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, total REAL NOT NULL)
   order_items (order_id TEXT, product_id TEXT, qty INTEGER, price REAL)
   ```

   `items` là danh sách tuple `(product_id, qty, price)`. Hàm phải, trong **một transaction**:
   trừ tồn kho từng sản phẩm, chèn `orders` với `total = Σ qty × price` (làm tròn 2 chữ số), chèn
   các dòng `order_items`, rồi trả về `total`.
   - `qty <= 0` hoặc `items` rỗng: raise `ValueError`, không đổi gì.
   - Một sản phẩm không đủ hàng hoặc không tồn tại: raise `OutOfStock` (đã định nghĩa), **không
     thay đổi gì** (kể cả sản phẩm đã trừ trước đó trong cùng đơn).
   - `order_id` đã tồn tại: để lỗi `sqlite3.IntegrityError` bay ra, tồn kho phải được hoàn lại.

2. `reserve_pg(dsn, product_id, qty) -> bool` trên PostgreSQL thật, bảng `ex_stock(product_id TEXT PRIMARY KEY, qty INTEGER)`:
   trừ `qty` nếu đủ hàng và trả `True`, ngược lại trả `False`. Test gọi đồng thời từ 20 thread
   (mỗi thread mở kết nối riêng) trên tồn kho 10: phải có đúng 10 lần `True` và tồn kho cuối cùng là 0.
   Phần này tự skip nếu PostgreSQL chưa chạy.

## Tiêu chí đạt

- Đơn hợp lệ: tồn kho giảm đúng, có 1 dòng `orders` và đủ dòng `order_items`, trả về `total` đúng.
- Đơn thiếu hàng, trùng `order_id`, dữ liệu sai: database y nguyên như trước khi gọi.
- `reserve_pg` không bán quá dưới tải đồng thời (khi có PostgreSQL).

## Gợi ý

### Gợi ý 1

`with con:` trên `sqlite3.Connection` tự commit khi khối chạy xong và rollback khi có exception.
Kiểm tra hợp lệ đầu vào trước khi ghi gì cả.

### Gợi ý 2

Đừng `SELECT qty` rồi tính trong Python rồi `UPDATE qty = ?` — đó chính là lost update. Hãy để
database làm: `UPDATE stock SET qty = qty - ? WHERE product_id = ? AND qty >= ?` và kiểm tra
`cursor.rowcount`. Với psycopg: `with psycopg.connect(dsn) as conn:` tự commit khi thoát khối.
