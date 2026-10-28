# M04: Lakehouse trên MinIO + DuckDB

## Mục tiêu

Dựng data lake theo kiến trúc medallion (bronze / silver / gold) trên MinIO (S3-compatible), lưu
Parquet và Delta Lake, truy vấn trực tiếp bằng DuckDB. Hiểu partitioning và chi phí scan.

## Việc cần làm

1. Bật MinIO và tạo bucket:

   ```bash
   docker compose -f setup/docker-compose.yml up -d minio
   # Console: http://localhost:9001 (minioadmin / minioadmin), tạo bucket "olist"
   ```

   Hoặc tạo bucket bằng `boto3` trong script (`endpoint_url="http://localhost:9000"`).
2. **Bronze** – `project/ingestion/to_bronze.py`: upload nguyên trạng CSV vào
   `s3://olist/bronze/<table>/ingest_date=YYYY-MM-DD/<file>.csv`.
3. **Silver** – `project/ingestion/to_silver.py`: đọc bronze, ép kiểu, bỏ trùng, chuẩn hoá tên cột,
   ghi Parquet vào `s3://olist/silver/<table>/`. Bảng `orders` và `order_items` partition theo
   `year/month` của `order_purchase_timestamp`. Bảng `orders` ghi thêm dạng Delta
   (`deltalake.write_deltalake`, mode `overwrite` theo partition) vào `s3://olist/silver_delta/orders`.
4. **Gold** – `project/models/gold/*.sql` chạy bằng DuckDB (extension `httpfs`):
   - `gold.daily_revenue` (ngày, bang, doanh thu, số đơn)
   - `gold.seller_delivery` (seller, số đơn, tỉ lệ trễ, điểm review trung bình)
   Ghi kết quả về `s3://olist/gold/`.
5. Cấu hình DuckDB đọc MinIO:

   ```sql
   INSTALL httpfs; LOAD httpfs;
   SET s3_endpoint='localhost:9000'; SET s3_use_ssl=false; SET s3_url_style='path';
   SET s3_access_key_id='minioadmin'; SET s3_secret_access_key='minioadmin';
   SELECT count(*) FROM read_parquet('s3://olist/silver/orders/**/*.parquet', hive_partitioning=true);
   ```

6. So sánh: truy vấn doanh thu tháng 2018-01 trên CSV bronze và trên Parquet silver có
   partition pruning (dùng `EXPLAIN ANALYZE`). Thử Delta time travel: đọc version trước của `orders`.
7. Chạy:

   ```bash
   uv run python tracks/data-engineer/capstone/project/ingestion/to_bronze.py --data-dir data/raw
   uv run python tracks/data-engineer/capstone/project/ingestion/to_silver.py
   uv run python tracks/data-engineer/capstone/project/ingestion/build_gold.py
   ```

## Kết quả nộp

- `to_bronze.py`, `to_silver.py`, `build_gold.py`, `project/models/gold/*.sql`
- Mục "Lakehouse" trong `project/README.md`: sơ đồ medallion, quy ước đường dẫn, bảng so sánh
  thời gian/bytes scan CSV vs Parquet.

## Tiêu chí đạt

- [ ] Bucket có đủ 3 tầng, đường dẫn theo quy ước thống nhất.
- [ ] Silver không còn dòng trùng khoá chính; kiểu dữ liệu đúng (kiểm bằng `DESCRIBE` trong DuckDB).
- [ ] Truy vấn lọc một tháng chỉ đọc partition của tháng đó.
- [ ] Đọc được ít nhất 2 version của bảng Delta `orders`.
- [ ] Số liệu gold khớp truy vấn tương đương trên `dw` của M02 (sai lệch = 0).
- [ ] Chạy lại toàn bộ cho cùng `ingest_date` không sinh tệp trùng.
