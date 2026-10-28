# Hướng dẫn và rubric: Mini lakehouse trên MinIO

Bài không có một đáp án duy nhất. Dưới đây là một hướng làm đạt mọi test, các quyết định cần cân nhắc và rubric chấm.

## Hướng làm

### Cấu trúc

```
<root>/
├── bronze/orders/                  # Delta, append-only, mọi cột string + _batch_id, _ingested_at
├── silver/orders/                  # Delta, một dòng/đơn, đã ép kiểu, cập nhật bằng MERGE
└── gold/revenue_by_state_month/    # Delta, ghi đè mỗi lần refresh
```

`root` là `/tmp/lake` hay `s3://bucket/olist` đều được: delta-rs dùng `object_store` nên chỉ cần truyền
`storage_options` (`AWS_ENDPOINT_URL`, khoá, `AWS_ALLOW_HTTP`, `AWS_S3_ALLOW_UNSAFE_RENAME`). Không có dòng code nào
phân nhánh theo local/S3, đó chính là điểm hay của lakehouse: tách storage khỏi compute.

### ingest_bronze

```python
uri = table_uri(root, "bronze", "orders")
if DeltaTable.is_deltatable(uri, storage_options=opts):
    seen = DeltaTable(uri, storage_options=opts).to_pyarrow_table(columns=["_batch_id"])
    if batch_id in set(seen.column("_batch_id").to_pylist()):
        return 0
t = raw.append_column("_batch_id", pa.array([batch_id] * n, pa.string()))
t = t.append_column("_ingested_at", pa.array([now_utc] * n, pa.timestamp("us", tz="UTC")))
write_deltalake(uri, t, mode="append", storage_options=opts)
```

Chỉ đọc cột `_batch_id` (column pruning). Ở quy mô lớn, lưu danh sách batch đã nạp vào một bảng control nhỏ thay vì
quét bronze, hoặc partition bronze theo ngày nạp.

### refresh_silver

1. Đọc bronze → Arrow → `con.register("bronze", table)` trong DuckDB.
2. `TRY_CAST` kiểu, `lower(trim(status))`, lọc `order_id` rỗng và timestamp hỏng.
3. `QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY updated_at DESC) = 1`: **bắt buộc** khử trùng source
   trước MERGE, vì MERGE với nhiều dòng source khớp cùng một dòng target sẽ lỗi.
4. Lần đầu: `write_deltalake` tạo bảng. Các lần sau:

```python
(DeltaTable(uri, storage_options=opts)
   .merge(src, predicate="t.order_id = s.order_id", source_alias="s", target_alias="t")
   .when_matched_update_all(predicate="s.updated_at > t.updated_at")
   .when_not_matched_insert_all()
   .execute())
```

Điều kiện `s.updated_at > t.updated_at` xử lý dữ liệu đến trễ/không theo thứ tự và làm MERGE idempotent.

Cải tiến: chỉ đọc các batch bronze chưa xử lý (lưu "watermark" `_ingested_at` hoặc danh sách batch đã đẩy sang silver),
thay vì quét toàn bộ bronze mỗi lần.

### refresh_gold

Tổng hợp trong DuckDB rồi `write_deltalake(..., mode="overwrite")`. Ghi đè toàn phần đơn giản và luôn đúng, còn Delta
vẫn giữ version cũ để time travel. Khi dữ liệu lớn: chỉ tính lại các partition (tháng) bị ảnh hưởng bởi batch mới và
ghi đè có `predicate` (xem bài advanced/02).

### query

Với mỗi tầng: `con.register(view, DeltaTable(uri, storage_options=opts).to_pyarrow_table())`. Có thể dùng
`to_pyarrow_dataset()` để DuckDB đẩy filter/projection xuống (đọc lười). Khi có mạng, extension `delta` của DuckDB
(`delta_scan`) là lựa chọn khác.

## Quyết định thiết kế cần nêu được

| Câu hỏi | Gợi ý trả lời |
| --- | --- |
| Vì sao bronze append-only? | Bản ghi gốc bất biến để replay khi sửa logic silver; audit; không mất dữ liệu nếu transform sai. |
| Vì sao bronze giữ string? | Không để lỗi ép kiểu chặn việc nạp; lỗi được xử lý (và đếm) ở silver. |
| Idempotency ở mỗi tầng? | Bronze: theo `batch_id`. Silver: MERGE có điều kiện thời gian. Gold: overwrite. |
| Concurrency trên S3? | S3 không có put-if-absent cổ điển; delta-rs cần locking provider (DynamoDB) hoặc `AWS_S3_ALLOW_UNSAFE_RENAME` khi chỉ có một writer. Nêu được rủi ro này là điểm cộng. |
| Small files? | Mỗi batch nhỏ sinh một tệp nhỏ; định kỳ `DeltaTable.optimize.compact()` và `vacuum()`. |
| Partition? | Bronze theo ngày nạp, silver có thể theo tháng mua; dữ liệu bài này quá nhỏ để partition. |

## Rubric (100 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| Test offline pass (`test_pipeline_local`, `test_silver_types`, `test_reruns_are_idempotent`) | 30 |
| Chạy được trên MinIO không đổi code (test MinIO pass khi bật dịch vụ) | 15 |
| Bronze idempotent theo batch, chỉ đọc cột cần thiết | 10 |
| Silver: khử trùng source trước MERGE, MERGE có điều kiện `updated_at` | 15 |
| Gold đúng và giải thích được khi nào nên đổi sang ghi đè theo partition | 10 |
| Docstring trả lời đủ hai câu hỏi, lập luận rõ | 10 |
| Code gọn: hàm phụ dùng chung (mở bảng, đăng ký view), không lặp `storage_options` lung tung, có type hint | 10 |

Điểm cộng (không bắt buộc): bảng quarantine cho dòng hỏng; `optimize.compact()` sau khi nạp; đọc tăng dần từ bronze bằng
watermark; dùng Change Data Feed thay vì quét toàn bộ.
