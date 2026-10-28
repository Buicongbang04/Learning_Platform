# M01: Nạp dữ liệu Olist vào PostgreSQL

## Mục tiêu

Viết một script Python nạp 9 tệp CSV Olist vào schema `raw` của PostgreSQL. Script phải
**idempotent** (chạy lại không nhân đôi dữ liệu), có log, có kiểm tra số dòng, và chạy được bằng
một lệnh. Đây là nền cho mọi milestone sau.

## Việc cần làm

1. Sinh dữ liệu và bật Postgres:

   ```bash
   uv run python data/generate_olist.py --orders 50000
   docker compose -f setup/docker-compose.yml up -d postgres
   ```

2. Viết DDL `project/models/raw/00_raw_schema.sql`: `CREATE SCHEMA IF NOT EXISTS raw;` và 9 bảng
   (`raw.customers`, `raw.geolocation`, `raw.orders`, `raw.order_items`, `raw.order_payments`,
   `raw.order_reviews`, `raw.products`, `raw.sellers`, `raw.product_category_name_translation`)
   với kiểu dữ liệu đúng (timestamp cho cột ngày, numeric(10,2) cho tiền) và primary key
   (`order_items` dùng khoá ghép `(order_id, order_item_id)`).
3. Hoàn thiện `project/ingestion/load_postgres.py`:
   - Đọc từng CSV trong `data/raw/` (tham số `--data-dir`).
   - Nạp bằng `COPY` (psycopg 3 `cursor.copy`) vào bảng tạm, rồi `INSERT ... ON CONFLICT DO UPDATE`
     vào bảng đích (hoặc `TRUNCATE` + nạp trong **một transaction**). Ghi rõ bạn chọn cách nào và vì sao.
   - Thêm cột `_loaded_at timestamptz default now()` để biết lần nạp.
   - Log số dòng đọc / ghi cho mỗi bảng; thoát mã khác 0 nếu lệch.
4. Viết `project/tests/test_ingestion.py`: test hàm đọc CSV/ép kiểu không cần Docker; test nạp thật
   dùng `ex.require_service`-style skip (`testkit.service_up("postgres")`).
5. Viết 5 câu SQL kiểm tra trong `project/models/raw/checks.sql`: số đơn theo `order_status`,
   số `order_items` mồ côi (không có order), đơn `delivered` thiếu `order_delivered_customer_date`,
   tổng `payment_value` so với tổng `price + freight_value`, top 5 bang theo số khách.
6. Chạy:

   ```bash
   uv run python tracks/data-engineer/capstone/project/ingestion/load_postgres.py --data-dir data/raw
   uv run python tracks/data-engineer/capstone/project/ingestion/load_postgres.py --data-dir data/raw  # lần 2
   docker compose -f setup/docker-compose.yml exec postgres psql -U de -d de -c "select count(*) from raw.orders;"
   uv run pytest tracks/data-engineer/capstone/project/tests -q
   ```

## Kết quả nộp

- `project/models/raw/00_raw_schema.sql`, `project/models/raw/checks.sql`
- `project/ingestion/load_postgres.py` hoàn chỉnh
- `project/tests/test_ingestion.py`
- Đoạn trong `project/README.md` mô tả cách chạy và kết quả 5 câu SQL kiểm tra.

## Tiêu chí đạt

- [ ] Nạp đủ 9 bảng, số dòng mỗi bảng khớp số dòng CSV.
- [ ] Chạy script lần thứ hai: số dòng không đổi, không lỗi duplicate key.
- [ ] Mọi bảng có primary key; kiểu ngày là `timestamp`, kiểu tiền là `numeric`.
- [ ] Nếu một bảng lỗi giữa chừng, bảng đó không bị nạp dở (transaction rollback).
- [ ] Cấu hình kết nối lấy từ biến môi trường `POSTGRES_DSN` (mặc định `postgresql://de:de@localhost:5432/de`), không hard-code mật khẩu rải rác.
- [ ] `uv run pytest tracks/data-engineer/capstone/project/tests -q` pass (test cần Postgres được skip khi chưa bật).
