---
title: Mini lakehouse bronze/silver/gold bằng Delta Lake trên MinIO
level: advanced
services: [minio]
files:
  - path: starter/lakehouse.py
    note: 4 TODO
  - path: tests/test_lakehouse.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/04-warehouse-lakehouse/exercises/advanced/01-lakehouse-minio -q
  - docker compose -f setup/docker-compose.yml up -d minio
  - uv run pytest tracks/data-engineer/modules/04-warehouse-lakehouse/exercises/advanced/01-lakehouse-minio -q
---

## Mục tiêu

Tự dựng một lakehouse thu nhỏ đúng nghĩa: object storage (MinIO, tương thích S3) giữ dữ liệu, Delta Lake cho
ACID và time travel, DuckDB làm engine truy vấn. Cùng một code chạy được trên ổ đĩa local lẫn S3 chỉ bằng đổi URI
và `storage_options`. Đây là nền cho capstone milestone m04.

## Đề bài

Dữ liệu thô là các batch đơn hàng Olist rút gọn dạng `pyarrow.Table`, mọi cột là string:
`order_id`, `customer_state`, `order_status`, `order_purchase_timestamp`, `order_value`, `updated_at`.
Một đơn có thể xuất hiện ở nhiều batch (trạng thái thay đổi), batch có thể đến trễ, và có dòng hỏng.

Hoàn thiện `starter/lakehouse.py`. Mọi hàm nhận `root` (thư mục local hoặc `s3://bucket/prefix`) và
`storage_options` (None với local). Ba bảng Delta nằm ở `table_uri(root, layer, name)` (đã viết sẵn):

1. `ingest_bronze(root, raw, batch_id, storage_options=None) -> int`
   - append vào `bronze/orders`, giữ nguyên các cột string, thêm `_batch_id` (string) và `_ingested_at` (timestamp UTC);
   - **idempotent theo `batch_id`**: batch đã nạp thì không nạp lại, trả 0; ngược lại trả số dòng đã nạp.
2. `refresh_silver(root, storage_options=None) -> int`
   - đọc bronze, ép kiểu (`order_purchase_timestamp`, `updated_at` → timestamp; `order_value` → double; status `lower/trim`),
     bỏ dòng thiếu `order_id` hoặc timestamp hỏng;
   - mỗi `order_id` giữ bản `updated_at` mới nhất, rồi `MERGE` vào `silver/orders`:
     chỉ cập nhật khi bản mới có `updated_at` **lớn hơn** bản đang có, chèn nếu chưa có;
   - trả số dòng của silver sau khi merge.
3. `refresh_gold(root, storage_options=None) -> int`
   - ghi đè `gold/revenue_by_state_month` với cột `customer_state`, `year_month` (`'YYYY-MM'`), `delivered_orders`,
     `revenue`, chỉ tính đơn `delivered`; trả số dòng.
4. `query(root, sql, storage_options=None) -> list[tuple]`
   - mở DuckDB, đăng ký ba view `bronze_orders`, `silver_orders`, `gold_revenue` từ các bảng Delta (đọc qua `deltalake`
     → Arrow, không cần extension của DuckDB), chạy `sql`, trả `fetchall()`.

Test chạy offline trên thư mục tạm. Nếu MinIO đang chạy, test thêm một lượt trên bucket S3
(`AWS_ENDPOINT_URL=http://localhost:9000`, `minioadmin/minioadmin`, `AWS_ALLOW_HTTP=true`,
`AWS_S3_ALLOW_UNSAFE_RENAME=true`).

Ngoài code, viết thêm một đoạn ngắn ở đầu `lakehouse.py` (docstring) trả lời: vì sao bronze là append-only,
và vì sao gold được ghi đè toàn phần ở đây nhưng ở quy mô lớn thì không nên.

## Tiêu chí đạt

- Cả 3 tầng là bảng Delta hợp lệ (có `_delta_log`), silver có lịch sử `MERGE`.
- Nạp lại cùng `batch_id` không nhân đôi bronze; chạy lại `refresh_silver`/`refresh_gold` không đổi kết quả.
- Bản cập nhật đến trễ nhưng cũ hơn không ghi đè bản mới hơn trong silver.
- Gold khớp doanh thu tính tay; `query` đọc được cả ba view.
- Khi MinIO chạy, toàn bộ pipeline chạy được trên `s3://...` mà không đổi code.

## Gợi ý

### Gợi ý 1

Kiểm tra bảng tồn tại: `DeltaTable.is_deltatable(uri, storage_options=...)`. Idempotency theo batch: đọc cột
`_batch_id` của bronze (chỉ cột đó) trước khi append. Ép kiểu và khử trùng làm gọn nhất trong DuckDB trên Arrow table:
`con.register("bronze", arrow_table)` rồi `TRY_CAST` + `QUALIFY ROW_NUMBER() ...`.

### Gợi ý 2

MERGE có điều kiện:

```python
(dt.merge(source, predicate="t.order_id = s.order_id", source_alias="s", target_alias="t")
   .when_matched_update_all(predicate="s.updated_at > t.updated_at")
   .when_not_matched_insert_all()
   .execute())
```

Tạo bucket MinIO bằng `boto3.client("s3", endpoint_url=..., aws_access_key_id=..., aws_secret_access_key=...)`.
Giữ kiểu timestamp thống nhất (vd. `timestamp[us]` không timezone cho dữ liệu, `timestamp[us, tz=UTC]` cho `_ingested_at`)
để tránh lỗi schema khi append.
