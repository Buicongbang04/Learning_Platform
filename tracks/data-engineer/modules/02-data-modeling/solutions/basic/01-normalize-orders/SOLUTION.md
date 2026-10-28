# Lời giải: Chuẩn hoá bảng đơn hàng phẳng về 3NF

## Cách làm

1. Liệt kê functional dependency:
   - `customer_id → customer_city, customer_state`
   - `seller_id → seller_city, seller_state`
   - `product_id → product_category_name`
   - `order_id → customer_id, order_status, order_purchase_timestamp`
   - `(order_id, order_item_id) → product_id, seller_id, price, freight_value`
2. Mỗi dependency thành một bảng, vế trái là khoá chính. Đây chính là 3NF: không còn phụ thuộc
   một phần khoá (2NF) hay bắc cầu (`order_id → customer_id → customer_city`).
3. Tạo bảng cha trước rồi mới tới bảng con vì `REFERENCES` cần bảng đích có sẵn.
4. `SELECT DISTINCT` cho bảng thực thể; `order_items` giữ nguyên số dòng vì grain của nó trùng grain
   bảng phẳng.

## Vì sao tách `CREATE TABLE` và `INSERT`

`CREATE TABLE ... AS SELECT` không khai báo được `PRIMARY KEY`/`FOREIGN KEY`. Khai báo constraint
có hai lợi ích: database **kiểm chứng** giả định của bạn (nếu dữ liệu có một `customer_id` với hai
thành phố khác nhau, `INSERT` sẽ báo lỗi trùng khoá thay vì âm thầm sinh hai dòng), và constraint
là tài liệu cho người đọc schema.

## Kiểm tra lossless join

Test join lại 5 bảng và so với `orders_flat` bằng `EXCEPT` theo cả hai chiều. Tách theo functional
dependency đảm bảo lossless join: không mất dòng, không sinh dòng "ma".

## Mở rộng

- Thêm `order_payments` để xử lý cột đa trị (1NF).
- Thêm `CHECK (order_status IN (...))`, `NOT NULL` cho các cột bắt buộc.
- Trên PostgreSQL nhớ tạo index cho các cột foreign key (`order_items.product_id`, ...), vì PG
  không tự tạo.
