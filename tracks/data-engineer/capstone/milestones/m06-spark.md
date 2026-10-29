# M06: Xử lý batch lớn bằng Spark trên NYC TLC

## Mục tiêu

Olist chỉ ~99 nghìn đơn, pandas hay DuckDB xử lý trong một giây: dùng Spark cho nó là chọn sai công cụ. Nền
tảng của bạn vì vậy có **nguồn thứ hai đủ lớn**: Yellow Taxi New York năm 2019 của NYC TLC (12 tệp Parquet,
~1,2 GB, 84,6 triệu chuyến). Viết một job PySpark đưa nguồn này vào lakehouse: làm sạch, tính bảng gold
`nyc_zone_daily`, ghi lên MinIO cạnh dữ liệu Olist, và tối ưu partition/shuffle/join có số đo.

## Việc cần làm

1. Làm trước bài [06/intermediate/04: Spark trên NYC Yellow Taxi 2019](../../modules/06-spark-big-data/exercises/intermediate/04-nyc-taxi-real/README.md).
   Milestone này **dùng lại** logic của bài đó (`load_trips`, luật loại `reject_reason`, `clean_trips`,
   broadcast bảng zone, ghi một tệp mỗi partition), không viết lại từ đầu. Tải dữ liệu (bỏ qua nếu đã có):

   ```bash
   uv run python data/download_dataset.py nyc-tlc
   ```

2. Viết `project/ingestion/spark_nyc_trips.py` (PySpark local, `local[*]`), chuyển các hàm từ notebook của
   bài 06 thành module có tham số dòng lệnh:
   - `--input` (mặc định `data/raw/nyc-tlc`), `--output` (đường dẫn local hoặc `s3a://olist/gold`),
     `--month YYYY-MM` (tuỳ chọn: chỉ tính lại một tháng).
   - Đọc cả 12 tệp một lần rồi lọc theo **tháng đón khách**, không chỉ đọc tệp của tháng đó: tệp tháng 2 có
     chuyến của 31/01 và các tháng khác (bản ghi gửi trễ).
   - Tính `build_zone_daily(trips, zones) -> DataFrame` theo `pickup_date` và zone đón: borough, zone, số chuyến,
     tổng cước, tỉ lệ tip chuyến trả thẻ, thời gian chuyến trung vị (`percentile_approx`); join zone bằng
     `F.broadcast`. Thêm cột `year_month`.
   - Ghi Parquet partition theo `year_month` vào `s3a://olist/gold/nyc_zone_daily/` (bucket của lakehouse M04,
     prefix `gold/` để policy M08 vẫn đúng). Cấu hình S3A tới MinIO:
     `spark.jars.packages=org.apache.hadoop:hadoop-aws:3.3.4`,
     `spark.hadoop.fs.s3a.endpoint=http://localhost:9000`, `path.style.access=true`, access/secret `minioadmin`.
     Chưa bật MinIO thì ghi local `data/clean/nyc-tlc/gold/`.
   - Ghi kèm bảng `reject_counts` (số chuyến mỗi `reject_reason`) để M10 theo dõi chất lượng nguồn.
3. Tối ưu và ghi lại trong `project/ingestion/SPARK_NOTES.md`:
   - So sánh `spark.sql.shuffle.partitions` mặc định (200) với giá trị hợp lý cho máy bạn.
   - Broadcast join với bảng zone (265 dòng); xem kế hoạch bằng `df.explain("formatted")`.
   - Bật/tắt AQE (`spark.sql.adaptive.enabled`), ghi thời gian.
   - Bộ nhớ: mỗi tệp TLC là một row group ~100 MB; ghi lại heap driver và số task song song bạn dùng
     (bài 06 giải thích vì sao 16 task với heap 1 GB bị `OutOfMemoryError`).
   - Dùng Spark UI (http://localhost:4040) chụp stage có shuffle lớn nhất.
4. Test logic bằng DataFrame nhỏ trong `project/tests/test_spark_job.py` (SparkSession local): luật loại chuyến,
   `build_zone_daily` trên vài chuyến tự dựng, plan có `BroadcastHashJoin`.
5. Thêm task Spark vào DAG M05 (`BashOperator` gọi `spark-submit` hoặc `uv run python ...`), truyền
   `--month` từ `data_interval_start` để mỗi lần chạy tính lại đúng một tháng.
6. Chạy:

   ```bash
   docker compose -f setup/docker-compose.yml up -d minio
   uv run python tracks/data-engineer/capstone/project/ingestion/spark_nyc_trips.py --input data/raw/nyc-tlc --output s3a://olist/gold
   uv run python tracks/data-engineer/capstone/project/ingestion/spark_nyc_trips.py --input data/raw/nyc-tlc --output s3a://olist/gold --month 2019-03
   uv run pytest tracks/data-engineer/capstone/project/tests/test_spark_job.py -q
   ```

## Kết quả nộp

- `spark_nyc_trips.py`, `test_spark_job.py`, `SPARK_NOTES.md`
- Bảng thời gian chạy theo các cấu hình đã thử; ảnh Spark UI.
- Mục "Nguồn thứ hai: NYC TLC" trong `project/README.md`: vì sao nguồn này cần Spark còn Olist thì không,
  sơ đồ luồng raw → gold, quy ước đường dẫn trên MinIO.

## Tiêu chí đạt

- [ ] Job chạy thành công trên đủ 12 tháng 2019 (84 598 444 chuyến gốc) với Java 17/21 local.
- [ ] Tổng số chuyến trong `nyc_zone_daily` bằng số chuyến sạch (khoảng 83,38 triệu theo luật của bài 06), cộng
  `reject_counts` bằng số chuyến gốc.
- [ ] Số chuyến của một ngày trong gold khớp truy vấn DuckDB tương đương trên Parquet gốc cùng luật lọc (sai lệch = 0).
- [ ] Plan có `BroadcastHashJoin` cho join với bảng zone.
- [ ] Đầu ra partition theo `year_month`, không có hàng nghìn tệp nhỏ (dùng `coalesce`/`repartition` hợp lý).
- [ ] Chạy lại với `--month` ghi đè đúng partition đó (`partitionOverwriteMode=dynamic`), các tháng khác giữ nguyên, không nhân đôi.
- [ ] Test Spark pass.
