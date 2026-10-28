---
title: CLI nạp đơn hàng vào SQLite có validate, logging và upsert
level: intermediate
services: []
files:
  - path: starter/ingest.py
    note: 4 TODO
  - path: tests/test_ingest.py
    note: Không sửa
run:
  - uv run python tracks/data-engineer/modules/01-foundations/exercises/intermediate/02-ingest-cli/starter/ingest.py --help
  - uv run pytest tracks/data-engineer/modules/01-foundations/exercises/intermediate/02-ingest-cli -q
---

## Mục tiêu

Viết script ingest đầu tiên đạt chuẩn production: tham số qua CLI, đọc streaming, validate từng dòng,
dòng lỗi vào file reject kèm lý do, ghi idempotent theo lô trong transaction, log có level, exit code
đúng. Đây là bản thu nhỏ của milestone m01 trong capstone.

## Đề bài

Đầu vào: CSV `orders` kiểu Olist với header
`order_id,customer_id,order_status,order_purchase_timestamp` (có thể có thêm cột khác, bỏ qua).

Hoàn thành `starter/ingest.py`:

1. **`validate(row) -> Order`**: trả `Order` (dataclass đã khai báo) hoặc raise `ValueError` với
   thông điệp nêu lý do. Quy tắc:
   - `order_id`, `customer_id` không rỗng (sau khi `strip()`);
   - `order_status` thuộc `VALID_STATUSES`;
   - `order_purchase_timestamp` đúng định dạng `YYYY-MM-DD HH:MM:SS`, lưu dạng `datetime`.
2. **`ensure_schema(conn)`**: tạo bảng `orders(order_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL,
   order_status TEXT NOT NULL, order_purchase_timestamp TEXT NOT NULL)` nếu chưa có. Timestamp lưu
   dạng chuỗi ISO `YYYY-MM-DD HH:MM:SS`.
3. **`upsert(conn, orders) -> int`**: ghi một lô bằng `INSERT ... ON CONFLICT(order_id) DO UPDATE`
   trong **một transaction**, trả số dòng đã ghi. Chạy lại không tạo trùng; bản ghi mới ghi đè bản
   cũ (cùng `order_id` xuất hiện sau thì thắng).
4. **`main(argv) -> int`**:
   - tham số: `csv_path`, `--db` (bắt buộc), `--rejects` (đường dẫn CSV reject, mặc định
     `<csv_path>.rejects.csv`), `--batch-size` (mặc định 500), `--log-level` (mặc định `INFO`);
   - đọc CSV từng dòng, dòng hợp lệ gom lô `--batch-size` rồi `upsert`;
   - dòng lỗi ghi vào file reject: giữ nguyên các cột gốc + cột `reason`, và log `WARNING` qua logger
     tên `"ingest"`;
   - cuối cùng log `INFO` chứa `loaded=<số dòng hợp lệ> rejected=<số dòng lỗi>`;
   - trả `0` khi thành công, `1` khi không thấy `csv_path` (log `ERROR`, không tạo DB), `1` khi
     header thiếu cột bắt buộc.

## Tiêu chí đạt

- `validate` chấp nhận dòng đúng, từ chối từng loại lỗi với `ValueError`.
- Chạy `main` hai lần trên cùng file: số dòng trong DB không đổi (idempotent).
- File thứ hai cập nhật trạng thái đơn đã có: DB phản ánh trạng thái mới.
- File reject có header gốc + `reason`, đúng số dòng lỗi.
- Log có `WARNING` cho dòng lỗi và `INFO` chứa `loaded=... rejected=...`.
- Exit code `1` khi thiếu file hoặc thiếu cột.

## Gợi ý

### Gợi ý 1

`datetime.strptime(value, "%Y-%m-%d %H:%M:%S")` raise `ValueError` khi sai định dạng. Dùng
`with conn:` của `sqlite3` để có transaction: tự `commit` khi thoát bình thường, `rollback` khi
có exception.

### Gợi ý 2

```sql
INSERT INTO orders (order_id, customer_id, order_status, order_purchase_timestamp)
VALUES (?, ?, ?, ?)
ON CONFLICT(order_id) DO UPDATE SET
    customer_id = excluded.customer_id,
    order_status = excluded.order_status,
    order_purchase_timestamp = excluded.order_purchase_timestamp
```

Ghi reject bằng `csv.DictWriter(f, fieldnames=reader.fieldnames + ["reason"])`. Nhớ gửi lô cuối
(ngắn hơn `batch-size`) sau vòng lặp.
