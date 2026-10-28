---
title: Pipeline nạp Olist có kiểm tra khoá ngoại, audit và all-or-nothing
level: advanced
services: []
files:
  - path: starter/pipeline.py
    note: Khung CLI, bạn tự thiết kế phần còn lại
  - path: tests/test_pipeline.py
    note: Không sửa, kiểm tra hợp đồng tối thiểu
run:
  - uv run python data/generate_olist.py --help
  - uv run pytest tracks/data-engineer/modules/01-foundations/exercises/advanced/02-olist-ingest-pipeline -q
---

## Mục tiêu

Ghép mọi thứ trong module thành một pipeline ingest hoàn chỉnh: đọc streaming, validate, kiểm tra
toàn vẹn tham chiếu, upsert idempotent, ghi rejects và nhật ký chạy (audit), đảm bảo một lần chạy
hoặc thành công trọn vẹn hoặc không để lại gì. Đây là bản nháp trực tiếp cho milestone m01 của
capstone (nạp Olist vào PostgreSQL).

## Đề bài

`main(argv)` trong `starter/pipeline.py` nhận `data_dir` và `--db <tệp SQLite>`, nạp ba tệp Olist:

| Tệp | Bảng đích | Khoá chính | Khoá ngoại |
| --- | --- | --- | --- |
| `olist_customers_dataset.csv` | `customers` | `customer_id` | |
| `olist_orders_dataset.csv` | `orders` | `order_id` | `customer_id` → `customers` |
| `olist_order_items_dataset.csv` | `order_items` | `(order_id, order_item_id)` | `order_id` → `orders` |

Cột của mỗi bảng giữ nguyên tên trong CSV (xem `tests/test_pipeline.py`). Yêu cầu:

1. **Schema**: tạo bảng nếu chưa có, khai báo `PRIMARY KEY` và `FOREIGN KEY` (`REFERENCES`).
2. **Validate từng dòng**: id bắt buộc không rỗng; `order_status` thuộc 8 trạng thái của Olist;
   timestamp dạng `YYYY-MM-DD HH:MM:SS` (`order_delivered_customer_date` được rỗng);
   `order_item_id` là số nguyên; `price`, `freight_value` là số không âm.
3. **Toàn vẹn tham chiếu**: đơn có `customer_id` không tồn tại, item có `order_id` không tồn tại
   (kể cả vì đơn đó bị reject) không được nạp mà vào rejects.
4. **Rejects**: bảng `rejects` có ít nhất các cột `run_id`, `table_name`, `raw` (dòng gốc, ví dụ
   JSON), `reason` (không rỗng).
5. **Idempotent**: chạy lại cùng dữ liệu không đổi số dòng; dữ liệu mới hơn ghi đè (upsert).
6. **Audit**: bảng `load_runs(run_id, started_at, finished_at, status, rows_loaded, rows_rejected)`,
   mỗi lần chạy một dòng, `status` là `success` hoặc `failed`. `rows_loaded` là tổng số dòng hợp lệ
   đã ghi của ba bảng, `rows_rejected` là tổng số dòng bị từ chối.
7. **All-or-nothing**: nếu thiếu tệp hoặc header thiếu cột ở bất kỳ tệp nào, hoặc lỗi bất ngờ giữa
   chừng, không bảng dữ liệu nào thay đổi, `load_runs` vẫn ghi lần chạy đó với `status = 'failed'`,
   và `main` trả `1`.
8. Thư mục đầu vào không tồn tại: trả `1`.
9. Đọc theo lô (`--batch-size`), không nạp cả tệp vào bộ nhớ; có logging.

Ngoài code, viết vào docstring đầu `pipeline.py` (hoặc tệp `starter/DESIGN.md`) khoảng 10–20 dòng:
thứ tự nạp và lý do, cách bạn đảm bảo all-or-nothing, và bạn sẽ đổi gì khi chuyển sang PostgreSQL
với 100 triệu dòng.

Muốn thử với dữ liệu lớn hơn, sinh dữ liệu giả bằng `data/generate_olist.py` của repo.

## Tiêu chí đạt

- Toàn bộ test trong `tests/test_pipeline.py` pass.
- Không nạp cả tệp vào RAM (generator/lô), có logging và exit code đúng.
- Lần chạy thất bại không để lại dữ liệu dở dang nhưng vẫn có dấu vết trong `load_runs`.
- Có phần giải thích thiết kế như yêu cầu ở trên.
- Đạt ≥ 70 điểm theo rubric trong lời giải.

## Gợi ý

### Gợi ý 1

Nạp theo thứ tự cha trước con: `customers` → `orders` → `order_items`. Kiểm tra mọi header **trước**
khi ghi bất cứ gì. Với SQLite, `sqlite3.connect(db, isolation_level=None)` cho bạn tự điều khiển
`BEGIN` / `COMMIT` / `ROLLBACK`; nhớ `PRAGMA foreign_keys = ON` (SQLite mặc định tắt kiểm tra FK).

### Gợi ý 2

Dòng `load_runs` phải được ghi và commit **ngoài** transaction dữ liệu: tạo dòng `running` trước,
chạy transaction dữ liệu, rồi cập nhật thành `success` hoặc `failed` (sau `ROLLBACK`). Kiểm tra khoá
ngoại theo lô: `SELECT customer_id FROM customers WHERE customer_id IN (...)` cho cả lô thay vì từng
dòng một.
