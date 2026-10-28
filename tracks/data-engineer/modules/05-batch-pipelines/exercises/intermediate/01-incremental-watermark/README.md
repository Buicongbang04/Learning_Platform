---
title: Incremental load bằng high-watermark và upsert
level: intermediate
services: []
files:
  - path: starter/incremental.py
    note: 4 TODO
  - path: tests/test_incremental.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/05-batch-pipelines/exercises/intermediate/01-incremental-watermark -q
---

## Mục tiêu

Cài đặt incremental load đúng cách: lưu watermark, lấy lùi một khoảng (lookback) để bắt dữ liệu đến
muộn, upsert để chạy lại không trùng, và chỉ tiến watermark khi load đã commit.

## Đề bài

Nguồn là bảng `orders` trong SQLite (đóng vai database OLTP), có cột `updated_at` dạng chuỗi
`YYYY-MM-DD HH:MM:SS`. Đích là DuckDB với bảng `stg_orders` (khoá chính `order_id`) và bảng trạng
thái `etl_state(source, watermark)`. Hàm `init_target` đã làm sẵn.

Hoàn thành trong `starter/incremental.py`:

1. `get_watermark(con, source="orders")`: trả về watermark (`datetime`) hoặc `None`.
2. `extract_since(src, watermark, lookback_minutes=10)`: nếu `watermark` là `None` lấy hết, ngược
   lại lấy dòng có `updated_at > watermark - lookback`. Trả về list tuple
   `(order_id, customer_id, order_status, updated_at)` sắp theo `updated_at`.
3. `upsert(con, rows)`: `INSERT ... ON CONFLICT (order_id) DO UPDATE`, **chỉ** ghi đè khi bản đến
   có `updated_at` mới hơn bản đang có. Không tự mở/đóng transaction. Trả về `len(rows)`.
4. `run_incremental(src_path, dst_path, lookback_minutes=10)`: một lượt chạy đầy đủ:
   `init_target` → đọc watermark → extract → `BEGIN` → `upsert` → ghi watermark mới
   (= max của watermark cũ và `updated_at` lớn nhất trong lô, không bao giờ lùi) → `COMMIT`.
   Có lỗi thì `ROLLBACK` và raise lại. Trả về `{"extracted": số dòng lấy được, "watermark": ...}`.
   Gọi `upsert(...)` bằng tên hàm toàn cục của module (test thay hàm này để giả lập warehouse lỗi).

## Tiêu chí đạt

- Lần đầu nạp hết, watermark bằng `updated_at` lớn nhất.
- Lần sau chỉ lấy dòng mới/cập nhật (cộng phần lookback), bản cập nhật ghi đè đúng.
- Dòng đến muộn có `updated_at` nhỏ hơn watermark nhưng trong cửa sổ lookback vẫn được nạp; chạy
  lại nhiều lần không sinh trùng; watermark không lùi.
- Upsert bản cũ hơn không ghi đè bản mới.
- Load lỗi thì không có dòng nào được ghi và watermark giữ nguyên; lần chạy sau bù đủ.

## Gợi ý

### Gợi ý 1

Chuỗi `YYYY-MM-DD HH:MM:SS` so sánh theo thứ tự từ điển trùng với thứ tự thời gian, nên trong
SQLite chỉ cần `WHERE updated_at > ?` với tham số là `since.strftime("%Y-%m-%d %H:%M:%S")`.

### Gợi ý 2

DuckDB hỗ trợ:

```sql
INSERT INTO stg_orders AS t (order_id, customer_id, order_status, updated_at)
VALUES (?, ?, ?, CAST(? AS TIMESTAMP))
ON CONFLICT (order_id) DO UPDATE SET order_status = excluded.order_status, ...
WHERE excluded.updated_at > t.updated_at
```

Dùng `con.executemany(sql, rows)`. Ghi watermark cũng bằng `INSERT ... ON CONFLICT (source) DO UPDATE`
trong **cùng transaction** với upsert.
