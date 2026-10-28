---
title: Tối ưu workload PostgreSQL bằng index, partial index và partitioning
level: advanced
services: [postgres]
files:
  - path: starter/tune.sql
    note: Viết toàn bộ thay đổi schema
  - path: starter/report.md
    note: EXPLAIN trước/sau và lý do
  - path: tests/test_tuning.py
    note: Không sửa
run:
  - docker compose -f setup/docker-compose.yml up -d postgres
  - uv run pytest tracks/data-engineer/modules/02-data-modeling/exercises/advanced/02-postgres-query-tuning -q
---

## Mục tiêu

Tối ưu một workload thật trên PostgreSQL bằng cách đọc `EXPLAIN (ANALYZE, BUFFERS)`, chọn đúng
công cụ cho từng truy vấn (composite/covering index, partial index, declarative partitioning) và
cân nhắc cái giá phía ghi.

## Đề bài

Test tạo schema `ex_tuning` với ba bảng (200k đơn, 200k item, 400k sự kiện, dữ liệu năm 2018),
không có index nào ngoài khoá chính `orders.order_id`:

```sql
orders (order_id TEXT PRIMARY KEY, customer_id TEXT, order_status TEXT, order_purchase_timestamp TIMESTAMPTZ)
order_items (order_id TEXT, order_item_id INT, seller_id TEXT, shipping_limit_date DATE, price NUMERIC(10,2))
order_events (order_id TEXT, event_type TEXT, event_ts TIMESTAMPTZ)
```

Ba truy vấn nóng:

```sql
-- Q1: dashboard seller
SELECT shipping_limit_date, price FROM order_items
WHERE seller_id = $1 AND shipping_limit_date >= $2 ORDER BY shipping_limit_date;

-- Q2: đếm sự kiện của một ngày (bảng sự kiện tăng mãi, dữ liệu cũ hơn 12 tháng phải xoá định kỳ)
SELECT count(*) FROM order_events WHERE event_ts >= $1 AND event_ts < $1 + interval '1 day';

-- Q3: hàng đợi 50 đơn 'processing' mới nhất (chỉ ~1% đơn ở trạng thái này)
SELECT order_id, order_purchase_timestamp FROM orders
WHERE order_status = 'processing' ORDER BY order_purchase_timestamp DESC LIMIT 50;
```

1. Viết `starter/tune.sql` (chạy với `search_path = ex_tuning`). Được phép tạo index, tạo lại bảng
   (giữ nguyên tên, cột và **toàn bộ dữ liệu**), partition.
2. Viết `starter/report.md`: plan trước/sau (`EXPLAIN (ANALYZE, BUFFERS)`), thời gian, lý do chọn
   từng thay đổi, tác động lên INSERT và dung lượng (`pg_relation_size`, `pg_indexes_size`), và
   cách vận hành việc xoá dữ liệu cũ của `order_events`.

## Tiêu chí đạt

- Q1: plan không có `Seq Scan` và không có `Sort`, dùng `Index Only Scan`.
- Q2: `order_events` là bảng partitioned, plan chỉ chạm **một** partition (partition pruning).
- Q3: plan không có `Seq Scan` và không có `Sort`.
- Kết quả và số dòng giữ nguyên. Báo cáo đạt rubric trong lời giải.

## Gợi ý

### Gợi ý 1

Q1 giống bài index cấp intermediate nhưng PostgreSQL có `INCLUDE (...)`. Index-only scan cần
visibility map: test chạy `VACUUM ANALYZE` sau script của bạn.

### Gợi ý 2

Q3: `CREATE INDEX ... (order_purchase_timestamp DESC) WHERE order_status = 'processing'` — index
nhỏ, chỉ chứa 1% dòng. Q2: `ALTER TABLE order_events RENAME TO order_events_old`, tạo bảng mới
`PARTITION BY RANGE (event_ts)`, các partition theo tháng của 2018 (+ `DEFAULT`), `INSERT ... SELECT`,
rồi `DROP` bảng cũ, tất cả trong một transaction.
