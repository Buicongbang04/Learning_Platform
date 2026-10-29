---
title: Spark trên NYC Yellow Taxi 2019 - làm sạch 84 triệu chuyến, partition theo ngày, tối ưu join
level: intermediate
services: []
files:
  - path: starter/nyc_taxi.ipynb
    note: 8 hàm TODO + cell đo tối ưu
  - path: starter/report.md
    note: Báo cáo 4 mục, đang là TODO
  - path: tests/test_nyc_taxi_real.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py nyc-tlc
  - uv run pytest tracks/data-engineer/modules/06-spark-big-data/exercises/intermediate/04-nyc-taxi-real -q
---

## Mục tiêu

Chạy một job PySpark trọn vẹn trên dữ liệu thật đủ lớn để thấy Spark khác pandas: đọc 12 tệp Parquet
(~1,2 GB, ~84,6 triệu chuyến taxi New York năm 2019), loại chuyến vô lý có ghi lý do, ghi Parquet partition
theo ngày không sinh small files, rút insight có số, và **đo** được ba tối ưu kinh điển: broadcast join,
gom tệp khi ghi, partition pruning.

## Đề bài

Bộ `nyc-tlc` gồm 12 tháng Yellow Taxi 2019 (`yellow_tripdata_2019-01..12.parquet`) và
`taxi_zone_lookup.csv`. Cell đầu notebook tự tải nếu chưa có (`ensure("nyc-tlc")`, ~1,2 GB).

Mở `starter/nyc_taxi.ipynb` (nút **Mở trong VS Code**), làm lần lượt:

1. `load_trips(spark, paths)`: đọc các tệp một lần, chỉ giữ 10 cột trong `COLUMNS`, đổi tên và ép kiểu.
2. `flag_rejects(df)` và `clean_trips(df)`: gắn `reject_reason` theo 5 luật trong notebook (ngoài năm 2019,
   thời gian `<= 0` hoặc quá 3 giờ, quãng đường `<= 0` hoặc quá 100 dặm, tiền âm/0/quá lớn, nhanh hơn
   80 dặm/giờ), luật đứng trước thắng, `null` tính là vi phạm; giữ chuyến tốt và thêm
   `duration_min`, `pickup_hour`, `pickup_date`.
3. `write_clean(df, out_dir)`: Parquet partition theo `pickup_date` ở `data/clean/nyc-tlc/yellow_2019/`,
   ghi đè, **mỗi ngày đúng một tệp** dù dữ liệu vào đang rải nhiều partition.
4. `peak_hours`, `tip_by_payment`, `tip_rate_by_borough` (broadcast bảng zone), `airport_summary`.
5. Chạy ba cell đo ở mục 5 (broadcast vs sort-merge join, small files, partition pruning), ghi lại thời gian.
6. Vẽ ít nhất 2 biểu đồ trong các cell `explore` (lý do loại, đường cầu theo giờ, tip theo borough).
7. Viết `starter/report.md`: 4 mục **Bộ dữ liệu**, **Làm sạch**, **Insight** (có số), **Giới hạn**.

Cả notebook chạy khoảng 1,5–2 phút trên máy 16 nhân, 31 GB RAM, nên bài dùng đủ 12 tháng. Máy yếu hơn
có thể tạm cắt `MONTHS` ở cell đầu khi thử, nhưng test trên bộ thật luôn chạy đủ 12 tháng (khoảng 1,5 phút;
chạy chung với test của bài khác thì JVM đã có heap 1 GB, test tự giảm số task song song nên chậm hơn một chút).

## Tiêu chí đạt

- Test trên DataFrame nhỏ (luôn chạy, không cần mạng) pass: đúng lý do loại cho từng luật, luật đứng trước
  thắng, cột thêm đúng, phân tích đúng trên mẫu.
- Plan của `tip_rate_by_borough` có `BroadcastHashJoin` kể cả khi tắt broadcast tự động.
- `write_clean` gọi hai lần vẫn đúng số dòng; mỗi thư mục `pickup_date=...` có đúng 1 tệp Parquet.
- Trên bộ thật: 84 598 444 chuyến gốc, khoảng 83,38 triệu chuyến sạch; giờ cao điểm là 18h với khoảng
  5,48 triệu chuyến; tip chuyến thẻ khoảng 22,8% tiền cước, tiền mặt gần 0.
- Notebook có ít nhất 2 cell `explore` vẽ biểu đồ.
- `report.md` đủ 4 mục, không còn TODO, mục Insight có ít nhất 3 con số.

## Gợi ý

### Gợi ý 1

`pickup_at` là `TIMESTAMP_NTZ` (giờ đồng hồ New York, không múi giờ): `cast("long")` báo lỗi, dùng hàm
`duration_minutes()` viết sẵn. Lý do loại: viết một `dict` tên luật -> điều kiện **chuyến tốt**, rồi
duyệt `REASONS` từ cuối lên đầu, mỗi bước `F.when(~F.coalesce(ok, F.lit(False)), tên).otherwise(lý_do_trước)`.

### Gợi ý 2

Small files: `df.repartition("pickup_date").write.mode("overwrite").partitionBy("pickup_date")` (hash theo
cột partition nên mỗi ngày nằm trọn trong một task). Broadcast: `trips.join(F.broadcast(zones), ...)`;
kiểm tra bằng `df.explain()`. `airport_summary`: zone sân bay chỉ có 3 dòng, `collect()` lấy id rồi
`isin(ids)`, tính cả 4 số trong một `agg` để chỉ quét dữ liệu một lần.
