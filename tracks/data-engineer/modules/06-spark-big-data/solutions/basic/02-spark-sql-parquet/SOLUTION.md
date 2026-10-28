# Lời giải: Spark SQL và Parquet

## Cách làm

- Temp view chỉ là tên gắn với plan của DataFrame trong SparkSession, không copy dữ liệu.
  `createOrReplaceTempView` cho phép chạy lại notebook/test nhiều lần.
- `monthly_gmv` viết bằng SQL; Catalyst sinh ra cùng plan như DataFrame API. `GROUP BY 1` gom theo
  biểu thức tháng. `COUNT(DISTINCT ...)` vì một đơn có nhiều item.
- `write_partitioned`: `year`/`month` là số nguyên nên thư mục là `month=1` chứ không phải `month=01`.
  `repartition("year", "month")` trước khi ghi làm mỗi thư mục chỉ có một file (dữ liệu nhỏ) thay vì
  nhiều file nhỏ từ mỗi partition trong bộ nhớ.
- `read_month`: lọc trên cột partition ngay sau khi đọc, Spark đưa điều kiện vào `PartitionFilters` và
  chỉ đọc thư mục khớp. `explain()` cho thấy `PartitionFilters: [isnotnull(year), (year = 2018), ...]`.
  Lưu ý `inputFiles()` liệt kê mọi file của relation (trước pruning) nên không dùng để kiểm tra pruning.

## Lưu ý

- `mode("overwrite")` với partitionOverwriteMode mặc định (`static`) xoá toàn bộ `path`. Khi chạy lại
  một tháng ở production, đặt `spark.sql.sources.partitionOverwriteMode=dynamic` (xem bài advanced).
- Khi đọc lại, Spark suy kiểu cột partition từ tên thư mục (`year` thành int).
