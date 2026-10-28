---
title: Thiết kế bảng Cassandra theo truy vấn đơn hàng
level: intermediate
services: [cassandra]
files:
  - path: starter/schema.cql
    note: 3 TODO
  - path: starter/load.py
    note: 4 TODO
  - path: tests/test_cassandra_model.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/03-nosql/exercises/intermediate/02-cassandra-query-model -q
  - docker compose -f setup/docker-compose.yml up -d cassandra
  - uv run pytest tracks/data-engineer/modules/03-nosql/exercises/intermediate/02-cassandra-query-model -q
---

## Mục tiêu

Luyện query-first modeling: từ ba truy vấn cụ thể, chọn partition key, clustering key và thứ tự clustering cho
từng bảng; denormalize dữ liệu cho bảng theo seller; ghi bằng prepared statement và đọc đúng một partition. Phần
kiểm tra schema (parse CQL) và biến đổi dữ liệu chạy offline; phần chạy trên Cassandra thật tự skip nếu chưa bật.

## Đề bài

Ứng dụng Olist cần ba truy vấn, mỗi truy vấn phải đọc **đúng một partition**, không `ALLOW FILTERING`:

- **Q1**: lịch sử sự kiện vận chuyển của một đơn (`order_id`), mới nhất trước. Hai sự kiện khác loại có thể
  cùng thời điểm.
- **Q2**: các đơn của một seller trong **một ngày** (`seller_id`, `order_date`), mới nhất trước, kèm giá trị
  phần hàng của seller đó trong đơn. Seller lớn có hàng nghìn đơn mỗi ngày, nên partition chỉ theo `seller_id`
  sẽ phình vô hạn.
- **Q3**: các review mới nhất của một sản phẩm (`product_id`), kèm điểm.

### Phần 1: `starter/schema.cql`

Đã có sẵn cột của ba bảng `order_events_by_order`, `orders_by_seller_day`, `reviews_by_product` (không ghi
keyspace trong tên bảng; test tự tạo keyspace). Hoàn thiện `PRIMARY KEY` và `WITH CLUSTERING ORDER BY` cho từng
bảng, sao cho:

- partition key là đúng những gì ứng dụng biết khi truy vấn;
- clustering key cho thứ tự mới nhất trước và đảm bảo mỗi hàng là duy nhất (thêm cột định danh phía sau cột
  thời gian).

### Phần 2: `starter/load.py`

1. `seller_order_rows(orders)`: mỗi đơn có dạng
   `{"order_id", "purchased_at": datetime, "items": [{"seller_id", "price", "freight"}, ...]}`. Trả về một dòng
   cho mỗi cặp (đơn, seller): `{"seller_id", "order_date": date, "purchased_at", "order_id", "order_value"}` với
   `order_value` = tổng `price` các item của seller đó trong đơn (làm tròn 2 chữ số, không gồm freight). Sắp theo
   `(seller_id, purchased_at, order_id)`.
2. `insert_events(session, events)` và `insert_seller_orders(session, rows)`: ghi bằng **prepared statement**
   (`session.prepare` một lần, `session.execute(prepared, params)` cho từng dòng).
3. `order_history(session, order_id, limit=10)`: trả list `(event_time, event_type)` mới nhất trước.
4. `seller_orders(session, seller_id, day, limit=20)`: trả list `order_id` mới nhất trước.

Hàm `split_statements` (đã viết sẵn) tách tệp CQL thành từng câu lệnh.

## Tiêu chí đạt

- Q1: partition key `(order_id)`, clustering bắt đầu bằng `event_time DESC` và có `event_type`.
- Q2: partition key `(seller_id, order_date)`, clustering bắt đầu bằng `purchased_at DESC` và có `order_id`.
- Q3: partition key `(product_id)`, clustering bắt đầu bằng `created_at DESC` và có `review_id`.
- Không dùng cột có cardinality thấp (`event_type`, `score`) làm partition key.
- `seller_order_rows` tách đúng một đơn nhiều seller thành nhiều dòng, đúng `order_value`.
- Khi Cassandra chạy: schema tạo được, dữ liệu ghi bằng prepared statement, hai hàm đọc trả đúng thứ tự.

## Gợi ý

### Gợi ý 1

Cú pháp composite partition key: `PRIMARY KEY ((seller_id, order_date), purchased_at, order_id)`. Thứ tự lưu:
`WITH CLUSTERING ORDER BY (purchased_at DESC, order_id ASC)` — phải liệt kê clustering column theo đúng thứ tự
khai báo.

### Gợi ý 2

Driver dùng `?` làm placeholder trong prepared statement:
`session.prepare("INSERT INTO order_events_by_order (order_id, event_time, event_type, location) VALUES (?, ?, ?, ?)")`.
Đọc: `SELECT event_time, event_type FROM order_events_by_order WHERE order_id = ? LIMIT ?` — không cần
`ORDER BY` vì đã lưu sẵn theo thứ tự giảm dần. Cột `order_date` kiểu `date` nhận `datetime.date`.
