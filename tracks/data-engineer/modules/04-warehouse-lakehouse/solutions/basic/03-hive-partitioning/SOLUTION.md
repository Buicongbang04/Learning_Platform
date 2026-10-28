# Lời giải: Partition kiểu Hive

Xem `partitioning.py`.

- `COPY ... PARTITION_BY (year, month)` tạo cây `year=2024/month=3/data_0.parquet`. Giá trị partition nằm ở
  **đường dẫn**, DuckDB mặc định bỏ hai cột này khỏi tệp để không lưu trùng.
- Khi đọc với `hive_partitioning = true`, DuckDB dựng lại cột `year`, `month` từ đường dẫn. Điều kiện
  `WHERE year = ? AND month = ?` được áp lên *danh sách tệp* trước khi mở tệp (partition pruning), nên chỉ
  thư mục khớp được đọc. Thử `EXPLAIN ANALYZE` để thấy số tệp được quét.
- **Idempotent**: chạy lại pipeline không được nhân đôi dữ liệu. Ở đây xoá cả thư mục rồi ghi lại. Với dữ liệu
  lớn, chỉ ghi đè *partition bị ảnh hưởng* (dynamic partition overwrite) hoặc dùng table format như Delta/Iceberg.
- Chọn cột partition: cột hay lọc, cardinality vừa phải. Partition theo ngày cho bảng nhỏ sẽ sinh hàng nghìn
  tệp tí hon (small files problem); partition theo `customer_id` là thảm hoạ. Quy tắc thô: mỗi partition nên
  có ít nhất vài trăm MB.
