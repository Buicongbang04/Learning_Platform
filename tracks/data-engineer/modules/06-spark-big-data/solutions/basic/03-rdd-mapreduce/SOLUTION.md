# Lời giải: MapReduce bằng tay và bằng RDD

## Ba pha bằng Python thuần

- **Map** là hàm thuần trên từng dòng, không cần biết dòng khác: vì thế chia cho nhiều máy được.
- **Shuffle** là bước duy nhất cần nhìn toàn bộ dữ liệu: mọi value cùng key phải về một chỗ. Trên
  cluster đây là bước ghi đĩa và truyền mạng.
- **Reduce** chạy độc lập theo từng key, lại song song được.

## Bằng RDD

- `reduceByKey` cộng cục bộ trong mỗi partition trước (giống **combiner** của Hadoop), chỉ shuffle một
  cặp `(category, partial_count)` cho mỗi category mỗi partition. `groupByKey` thì shuffle từng số 1,
  tốn mạng và bộ nhớ hơn nhiều khi dữ liệu lớn.
- `takeOrdered(n, key=...)` lấy top-n trên từng partition rồi gộp ở driver, không phải sort toàn bộ.
- Hàm `parse` định nghĩa bên trong `_counts` nên cloudpickle gửi nguyên mã của nó sang Python worker.
  Hàm ở mức module bị pickle theo tham chiếu (tên module); worker phải import được module đó, điều
  không đúng với tệp do testkit nạp (trên cluster thật, bạn đóng gói code bằng `--py-files`). Không
  tham chiếu `sc` trong lambda.

## Liên hệ DataFrame

Cùng việc đó bằng DataFrame: `df.groupBy("category").count()`. Spark tự làm partial aggregation
(`HashAggregate` hai tầng quanh `Exchange` trong plan) và chạy trong JVM, nhanh hơn RDD trong PySpark.
