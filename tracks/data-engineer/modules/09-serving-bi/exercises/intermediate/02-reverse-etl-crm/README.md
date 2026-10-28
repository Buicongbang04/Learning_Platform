---
title: Job Reverse ETL đồng bộ khách hàng sang CRM giả
level: intermediate
services: []
files:
  - path: starter/sync.py
    note: 6 TODO
  - path: tests/test_sync.py
    note: Không sửa (chứa FakeCRM)
  - path: tests/fixtures/olist_small.sql
    note: Dữ liệu Olist thu nhỏ, không sửa
run:
  - uv run pytest tracks/data-engineer/modules/09-serving-bi/exercises/intermediate/02-reverse-etl-crm -q
---

## Mục tiêu

Tự viết một job Reverse ETL đúng chuẩn production: tính hồ sơ khách hàng (LTV, segment) từ warehouse, chỉ gửi bản
ghi thay đổi, chia batch theo giới hạn API, retry lỗi tạm thời bằng exponential backoff, không retry lỗi vĩnh viễn,
và chạy lại an toàn (idempotent).

## Đề bài

CRM được giả lập bằng `FakeCRM` trong test: method `upsert(batch)` lưu contact theo `external_id`, từ chối batch lớn
hơn `max_batch` bằng `PermanentError`, và có thể được cài sẵn chuỗi lỗi (`TransientError`, `PermanentError`) cho từng
lần gọi. Hoàn thiện `starter/sync.py`:

1. `build_customer_payload(con)`: mỗi `customer_unique_id` một record gồm `external_id`, `state` (state của đơn gần
   nhất), `total_orders`, `lifetime_value`, `last_order_date`, `segment` (`vip` nếu LTV ≥ 300, `repeat` nếu từ 2 đơn,
   còn lại `new`). Chỉ tính đơn không `canceled`/`unavailable`. Lưu ý trong dữ liệu, một `customer_unique_id` có thể
   ứng với nhiều `customer_id`.
2. `record_hash(record)`: SHA-256 không phụ thuộc thứ tự key.
3. `diff_records(records, state)`: chỉ record mới hoặc đổi so với `state` (`external_id → hash`).
4. `batched(items, size)`.
5. `send_with_retry(client, batch, max_retries, base_delay, sleep)`: retry `TransientError` với độ trễ
   `base_delay * 2**attempt`; `PermanentError` raise ngay. `sleep` được truyền vào để test không phải chờ thật.
6. `run_sync(records, client, state, …)`: diff, batch, gửi; chỉ cập nhật `state` cho batch thành công; batch lỗi thì
   ghi nhận và chạy tiếp; trả bảng tổng kết.

## Tiêu chí đạt

- Payload từ DuckDB đúng 3 khách như test.
- Chạy `run_sync` lần hai với cùng dữ liệu không gọi CRM lần nào.
- Đổi một khách thì chỉ khách đó được gửi.
- Lỗi tạm thời được retry đúng lịch `0.5, 1.0, 2.0`; lỗi vĩnh viễn không retry.
- Batch lỗi không được ghi vào state; lần chạy sau tự gửi bù, CRM không có bản ghi trùng.
- `uv run pytest … -q` pass 12 test.

## Gợi ý

### Gợi ý 1

`json.dumps(record, sort_keys=True, default=str)` cho chuỗi chuẩn hoá trước khi băm. Trong DuckDB,
`arg_max(customer_state, order_purchase_timestamp)` lấy state của đơn mới nhất. Tính tổng tiền mỗi đơn trong một CTE
riêng rồi mới join, để `COUNT(DISTINCT order_id)` và `SUM` không bị ảnh hưởng lẫn nhau.

### Gợi ý 2

Vòng retry: `attempt = 0`, trong `while True` gọi `client.upsert`; bắt `TransientError`, nếu `attempt >= max_retries`
thì `raise`, ngược lại `sleep(base_delay * 2 ** attempt)` và tăng `attempt`. Trong `run_sync`, bắt cả hai loại lỗi
quanh từng batch để một batch hỏng không chặn các batch sau. Production nên cộng thêm jitter ngẫu nhiên vào độ trễ.
