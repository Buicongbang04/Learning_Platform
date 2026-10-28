# M06: Xử lý batch lớn bằng Spark

## Mục tiêu

Khi dữ liệu vượt quá RAM một máy, chuyển transform nặng sang Spark. Viết job PySpark đọc silver
trên MinIO, tính bảng gold `seller_performance`, và tối ưu partition/shuffle/join.

## Việc cần làm

1. Sinh bộ dữ liệu lớn hơn để thấy khác biệt:

   ```bash
   uv run python data/generate_olist.py --orders 500000 --out data/raw_big
   ```

2. Viết `project/ingestion/spark_seller_performance.py` (PySpark local, `local[*]`):
   - Cấu hình S3A tới MinIO: `spark.jars.packages=org.apache.hadoop:hadoop-aws:3.3.4`,
     `spark.hadoop.fs.s3a.endpoint=http://localhost:9000`, `path.style.access=true`,
     access/secret `minioadmin`.
   - Đọc `orders`, `order_items`, `order_reviews`, `sellers` (silver Parquet; hoặc CSV local nếu
     chưa có MinIO, qua tham số `--input`).
   - Tính theo `seller_id` và tháng: số đơn, doanh thu, tỉ lệ giao trễ, điểm review trung bình,
     xếp hạng trong bang bằng window function.
   - Ghi Parquet partition theo `year_month` vào `s3://olist/gold/seller_performance/`.
3. Tối ưu và ghi lại trong `project/ingestion/SPARK_NOTES.md`:
   - So sánh `spark.sql.shuffle.partitions` mặc định (200) với giá trị hợp lý cho local (vd. 8).
   - Broadcast join với `sellers` (bảng nhỏ); xem kế hoạch bằng `df.explain("formatted")`.
   - Bật/tắt AQE (`spark.sql.adaptive.enabled`), ghi thời gian.
   - Dùng Spark UI (http://localhost:4040) chụp stage có shuffle lớn nhất.
4. Test logic bằng DataFrame nhỏ trong `project/tests/test_spark_job.py` (SparkSession local,
   tách hàm `build_seller_performance(orders, items, reviews, sellers) -> DataFrame`).
5. Thêm task Spark vào DAG M05 (`BashOperator` gọi `spark-submit` hoặc `uv run python ...`).
6. Chạy:

   ```bash
   uv run python tracks/data-engineer/capstone/project/ingestion/spark_seller_performance.py --input data/raw_big --output data/raw_big/gold
   uv run pytest tracks/data-engineer/capstone/project/tests/test_spark_job.py -q
   ```

## Kết quả nộp

- `spark_seller_performance.py`, `test_spark_job.py`, `SPARK_NOTES.md`
- Bảng thời gian chạy theo các cấu hình đã thử; ảnh Spark UI.

## Tiêu chí đạt

- [ ] Job chạy thành công trên 500k đơn với Java 17/21 local.
- [ ] Kết quả khớp DuckDB gold `seller_delivery` của M04 với cùng dữ liệu (sai lệch = 0).
- [ ] Plan có `BroadcastHashJoin` cho join với `sellers`.
- [ ] Đầu ra partition theo `year_month`, không có hàng nghìn tệp nhỏ (dùng `coalesce`/`repartition` hợp lý).
- [ ] Chạy lại ghi đè đúng partition (`partitionOverwriteMode=dynamic`), không nhân đôi.
- [ ] Test Spark pass.
