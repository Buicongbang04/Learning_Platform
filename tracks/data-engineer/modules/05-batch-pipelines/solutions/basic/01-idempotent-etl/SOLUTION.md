# Lời giải: Pipeline ETL idempotent

## Ý chính

1. **Tham số hoá theo `ds`**: mọi bước nhận `ds` từ bên ngoài, không dùng `datetime.now()`. Nhờ vậy
   chạy lại ngày cũ (backfill) xử lý đúng dữ liệu của ngày đó.
2. **Transform thuần (pure function)**: `transform` chỉ nhận DataFrame trả về DataFrame, không I/O,
   nên test dễ và chạy lại luôn cho cùng kết quả.
3. **Delete-insert trong một transaction** là cách đơn giản nhất để load idempotent cho bảng fact
   theo ngày. Người đọc không bao giờ thấy partition rỗng giữa chừng, và nếu `INSERT` lỗi thì
   `ROLLBACK` trả lại dữ liệu cũ.

## Các điểm dễ sai

- Đọc CSV không có `dtype=str`: pandas tự đoán kiểu, `order_id` dạng số có thể mất số 0 ở đầu,
  timestamp bị đổi format. Extract nên "ngu", transform mới quyết định kiểu.
- Dedup trước khi lọc ngày hay sau? Ở đây khoá `order_id` chỉ thuộc một ngày nên thứ tự không quan
  trọng; với dữ liệu thật hãy dedup theo `updated_at` mới nhất (`ROW_NUMBER`).
- `DELETE ... WHERE ds = ?` truyền chuỗi: ép `CAST(? AS DATE)` để so sánh đúng kiểu.
- Phải `ROLLBACK` rồi `raise` lại: nuốt lỗi thì orchestrator tưởng task thành công.
- `con.register` tạo view tạm trỏ tới DataFrame; `unregister` để không rò tên giữa các lần gọi.

## Mở rộng

- Ghi vào `fct_orders__staging`, chạy kiểm tra chất lượng, rồi mới delete-insert (write-audit-publish).
- Với Spark/Hive dùng `INSERT OVERWRITE ... PARTITION (ds=...)` hoặc
  `spark.sql.sources.partitionOverwriteMode=dynamic` để có cùng hiệu ứng.
