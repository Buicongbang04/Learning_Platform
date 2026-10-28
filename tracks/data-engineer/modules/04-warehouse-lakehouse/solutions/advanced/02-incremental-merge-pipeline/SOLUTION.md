# Hướng dẫn và rubric: Nạp tăng dần idempotent

## Hướng làm

### 1. load_increment: tìm "thay đổi thật" trước khi MERGE

```python
con = duckdb.connect()
con.register("batch", batch)
con.register("silver", DeltaTable(silver_path).to_pyarrow_table(columns=["order_id", "updated_at"]))
changed = con.sql("""
    WITH dedup AS (
        SELECT *, CAST(order_purchase_timestamp AS DATE) AS order_date
        FROM batch
        QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY updated_at DESC) = 1
    )
    SELECT d.* FROM dedup d LEFT JOIN silver s USING (order_id)
    WHERE s.order_id IS NULL OR d.updated_at > s.updated_at
""").to_arrow_table()
```

- Khử trùng trong batch là bắt buộc: MERGE gặp hai dòng source khớp một dòng target sẽ lỗi.
- `changed` vừa là source cho MERGE, vừa cho ra tập `order_date` bị ảnh hưởng. Nếu rỗng thì dừng, không tạo commit
  rỗng (log Delta gọn hơn, không kích hoạt downstream vô ích).
- Lần đầu (bảng chưa tồn tại) thì `write_deltalake` tạo bảng; nhớ cho silver có schema rỗng tương đương để câu join chạy.
- MERGE vẫn giữ điều kiện `when_matched_update_all(predicate="s.updated_at > t.updated_at")` như lớp bảo vệ thứ hai,
  phòng khi có writer khác chen vào giữa bước đọc và bước MERGE.

### 2. refresh_gold: thay đúng các ngày bị ảnh hưởng

```python
new = <tổng hợp silver WHERE order_status = 'delivered' AND order_date IN (dates)>
DeltaTable(gold).delete("order_date IN ('2024-03-01', ...)")
write_deltalake(gold, new, mode="append")
```

Hai commit (delete rồi append) có một khoảng reader thấy gold thiếu ngày. Muốn nguyên tử, dùng
`write_deltalake(gold, new, mode="overwrite", predicate="order_date IN (...)")` (dữ liệu ghi phải thoả predicate), hoặc
MERGE với `when_not_matched_by_source_delete(predicate=...)`. Đây là "dynamic partition overwrite" phiên bản table format.

Ngày không còn đơn delivered phải *biến mất* khỏi gold. Cách "chỉ upsert dòng mới" bỏ sót trường hợp này: lỗi phổ biến.

### 3. Docstring: khi nào "ngày bị ảnh hưởng" sai

- Nếu một đơn **đổi `order_purchase_timestamp`** sang ngày khác, cả ngày cũ lẫn ngày mới đều bị ảnh hưởng, nhưng tập
  trả về chỉ có ngày mới. Sửa: lấy cả `order_date` cũ từ silver trước khi MERGE (join ra cột cũ và mới, hợp hai tập).
- Nếu gold có chỉ số không phân tách theo ngày (vd. khách hàng mới trong tháng, rolling 7 ngày, distinct count theo
  tháng), phạm vi cần tính lại rộng hơn "ngày bị ảnh hưởng". Phải suy ra phạm vi từ định nghĩa metric.
- Xoá cứng ở nguồn không xuất hiện trong batch CDC dạng upsert; cần cờ `is_deleted` hoặc tombstone.

## Quyết định thiết kế cần cân nhắc

| Vấn đề | Lựa chọn | Đánh đổi |
| --- | --- | --- |
| Thứ tự phiên bản | `updated_at` từ nguồn | Đồng hồ nguồn có thể lệch; tốt hơn là số thứ tự CDC (LSN, Kafka offset) |
| Phát hiện thay đổi | So `updated_at` | Rẻ; nếu nguồn không có `updated_at` thì so hash toàn dòng |
| Gold | Tính lại theo ngày | Nhanh, nhưng phải tính đúng phạm vi ảnh hưởng; định kỳ vẫn nên full refresh để sửa trôi số liệu |
| Commit | Delete + append | Đơn giản; overwrite có predicate / MERGE thì nguyên tử |
| Thay thế | Change Data Feed của Delta | Đọc thẳng các dòng thay đổi giữa hai version thay vì tự so |

## Rubric (100 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| 5 test pass | 40 |
| Khử trùng trong batch, MERGE có điều kiện thời gian | 15 |
| Không tạo commit khi batch không có thay đổi thật | 5 |
| Gold xoá được ngày không còn dữ liệu, chỉ chạm ngày được truyền | 15 |
| Docstring nêu đúng trường hợp đổi ngày mua và metric không phân tách theo ngày, kèm cách sửa | 15 |
| Code rõ ràng, kiểu `order_date` thống nhất (`date32`), không SQL injection khi dựng predicate (ngày được định dạng ISO) | 10 |
