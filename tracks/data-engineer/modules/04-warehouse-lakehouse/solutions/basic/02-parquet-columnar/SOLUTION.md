# Lời giải: Parquet và lưu trữ dạng cột

Xem `columnar.py`. Các điểm chính:

- **Ghi Parquet**: `pq.write_table(..., compression="zstd", row_group_size=1000)`. Row group là đơn vị đọc
  song song và đơn vị bỏ qua (skip) dữ liệu. Thực tế row group thường 64–512 MB hoặc vài trăm nghìn tới
  vài triệu dòng; ở đây để nhỏ cho dễ quan sát.
- **Column pruning**: `pq.read_table(path, columns=[...])` chỉ đọc các column chunk cần thiết khỏi đĩa.
  Với CSV bạn luôn phải đọc cả dòng.
- **Statistics**: mỗi column chunk trong footer có `min`, `max`, `null_count`. Engine (DuckDB, Spark, Trino)
  so điều kiện `WHERE` với min/max để bỏ qua cả row group. Đọc metadata không chạm vào dữ liệu nên rất rẻ.
- **Nén**: dữ liệu cùng kiểu đứng cạnh nhau nên dictionary encoding + RLE + zstd nén tốt hơn nhiều so với
  CSV dạng text. Tỉ lệ 5–10 lần là bình thường với dữ liệu thật.
- **Predicate pushdown**: `filters=[("price", ">=", x)]` giúp pyarrow bỏ qua row group có `max(price) < x`.
  Pushdown hiệu quả nhất khi dữ liệu được *sắp xếp* theo cột lọc: khi đó min/max của các row group ít chồng nhau.

Thử thêm: ghi lại tệp sau khi `table.sort_by("price")` rồi xem `row_group_stats` thay đổi thế nào.
