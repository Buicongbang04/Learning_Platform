# Hướng dẫn chấm: Bảng serving incremental luôn khớp full rebuild

Bài không có đáp án duy nhất. Dưới đây là hướng làm tham khảo, các quyết định thiết kế và rubric.

## Hướng làm

1. **Chung một câu SELECT aggregate** cho cả full và incremental, chỉ khác điều kiện lọc ngày. Hai đường code tách
   rời là nguồn gốc của lệch số.
2. **Watermark** lưu trong `_refresh_state(table_name, watermark)`. Đầu mỗi lần chạy, trong một transaction:
   - Đọc `wm` cũ; `since = wm - lookback`.
   - Đọc `new_wm = GREATEST(MAX(orders.updated_at), MAX(orders_deleted.deleted_at))` **trước** khi tính, trong cùng
     transaction, để thay đổi xảy ra trong lúc chạy không bị bỏ sót ở lần sau.
   - Tạo bảng tạm `_dates`: ngày đặt của đơn có `updated_at > since` hợp với ngày của tombstone có `deleted_at > since`.
   - `DELETE FROM agg_daily_sales WHERE order_date IN (SELECT d FROM _dates)` rồi `INSERT … SELECT` aggregate chỉ cho
     các ngày đó. Ngày không còn đơn thì `INSERT` không sinh dòng, nên dòng cũ biến mất.
   - Ghi `max(new_wm, wm)` vào state, `COMMIT`. Lỗi thì `ROLLBACK`, cả dữ liệu và watermark giữ nguyên, lần sau chạy lại
     đúng phần đó (idempotent).
3. Lần đầu (chưa có state) gọi `full_rebuild`.

```python
since = wm - lookback
con.execute("""CREATE OR REPLACE TEMP TABLE _dates AS
    SELECT DISTINCT CAST(order_purchase_timestamp AS DATE) AS d FROM orders WHERE updated_at > ?
    UNION
    SELECT DISTINCT CAST(order_purchase_timestamp AS DATE) FROM orders_deleted WHERE deleted_at > ?""",
    [since, since])
```

## Quyết định cần cân nhắc

- **Tính lại partition thay vì cộng/trừ delta.** Delta cộng được cho `SUM`, nhưng không cho `COUNT DISTINCT`, và rất
  dễ sai khi một đơn đổi trạng thái hai lần giữa hai lần chạy. Tính lại cả ngày đơn giản, idempotent, chi phí tỉ lệ
  với số ngày bị đụng.
- **Nguồn của watermark.** Lấy từ dữ liệu, không lấy từ đồng hồ của job. Dùng `>` với watermark cũ kết hợp
  `lookback` để chấp nhận quét trùng thay vì bỏ sót.
- **Chọn `lookback`.** Dựa trên độ trễ tối đa quan sát được của replica/CDC (ví dụ p99 + biên). Quét trùng an toàn
  nhờ tính lại cả ngày, chỉ tốn thêm compute.
- **Xoá cứng.** Watermark trên `updated_at` không thấy được dòng đã biến mất. Cần tombstone (soft delete, bảng
  `_deleted`, hoặc sự kiện delete từ CDC như Debezium).
- **Vi phạm hợp đồng** (item đổi mà không bump `updated_at`): incremental không thấy. Biện pháp: full rebuild định kỳ
  (đêm hoặc cuối tuần) kèm reconcile (bài basic/02) để phát hiện trôi số, và data contract/test ở nguồn.
- **Thay đổi làm đơn đổi ngày** (nếu `order_purchase_timestamp` có thể sửa): phải tính lại cả ngày cũ và ngày mới,
  nên cần lưu ngày cũ (bảng mapping order → ngày đã aggregate, hoặc CDC có before-image).
- **Đối chiếu với công cụ**: dbt `incremental` với `incremental_strategy='delete+insert'` hoặc `insert_overwrite` theo
  partition; materialized view incremental của BigQuery/Snowflake/Databricks tự làm phần này nhưng hạn chế loại SQL.

## Rubric (10 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| 7 test pass, kết quả incremental bằng full rebuild trong mọi kịch bản | 3 |
| Một câu aggregate dùng chung cho full và incremental, không lặp logic | 1 |
| Watermark lấy từ dữ liệu nguồn, cập nhật nguyên tử cùng dữ liệu, có xử lý lỗi/rollback | 2 |
| Xử lý xoá cứng qua tombstone và ngày không còn đơn | 1 |
| `lookback` đúng ngữ nghĩa, giải thích cách chọn giá trị | 1 |
| Ghi chú thiết kế: vì sao tính lại partition, vi phạm hợp đồng, full rebuild định kỳ + reconcile | 2 |
