# Lời giải: CLI nạp đơn hàng vào SQLite

## Cách làm

**`validate`** chuẩn hoá (`strip`) rồi kiểm tra theo thứ tự, mỗi lỗi một thông điệp riêng để file
reject có ích cho người sửa dữ liệu. `strptime` vừa kiểm định dạng vừa kiểm giá trị (tháng 13 bị từ
chối). `raise ... from None` giấu traceback gốc vì thông điệp mới đã đủ ý.

**`ensure_schema`** dùng `CREATE TABLE IF NOT EXISTS` nên gọi bao nhiêu lần cũng được (idempotent).
Ở dự án lớn, schema được quản lý bằng migration (Alembic, Flyway, dbt) thay vì tạo trong script.

**`upsert`** dùng `INSERT ... ON CONFLICT(order_id) DO UPDATE SET col = excluded.col`. `excluded` là
dòng *định chèn*. Cú pháp này giống hệt PostgreSQL, nên chuyển sang Postgres (capstone m01) gần như
không phải sửa SQL. `with conn:` mở transaction cho cả lô: hoặc ghi hết, hoặc không ghi gì. Không có
transaction, script chết giữa chừng để lại nửa lô, và lần chạy lại vẫn đúng nhờ upsert, nhưng dữ
liệu tạm thời không nhất quán.

**`main`**:

- Kiểm tra đầu vào *trước khi* mở DB, nên thiếu file thì không tạo DB rỗng (test kiểm tra điều này).
- Header thiếu cột là lỗi cấu trúc của cả file, khác lỗi từng dòng: fail cả job (`return 1`) thay vì
  reject mọi dòng.
- Dòng lỗi: ghi nguyên dòng gốc + `reason` (để sửa rồi nạp lại), log `WARNING` kèm số dòng.
- Lô cuối ngắn hơn `batch-size` được gửi sau vòng lặp, lỗi kinh điển là quên bước này.
- `logging.basicConfig` chỉ gọi trong `main` (entrypoint). Logger của module là
  `logging.getLogger("ingest")`; nếu đây là thư viện, nó không được cấu hình logging.
- `main(argv)` nhận danh sách tham số nên test gọi trực tiếp, không cần subprocess.

## Vì sao idempotent quan trọng

Scheduler sẽ chạy lại job (retry khi lỗi mạng, backfill khi sửa logic). Với upsert theo khoá chính,
chạy lại cùng file cho cùng kết quả, file mới hơn cập nhật trạng thái đơn (o8 từ `approved` sang
`canceled`). Nếu dùng `INSERT` thuần, lần chạy thứ hai sẽ lỗi trùng khoá hoặc (khi không có khoá
chính) nhân đôi dữ liệu.

## Mở rộng

- Thêm ngưỡng: nếu `rejected / total > 5%` thì `return 1` (dữ liệu nguồn có vấn đề, đừng nạp tiếp).
- Log dạng JSON (`python-json-logger`) để hệ thống log parse được.
- Đổi sang PostgreSQL bằng `psycopg` và `executemany`/`COPY` vào staging table rồi
  `INSERT ... SELECT ... ON CONFLICT` (nhanh hơn nhiều với hàng triệu dòng).
- Thêm cột `_loaded_at`, `_source_file` để truy vết (lineage) mỗi dòng đến từ đâu.
