---
title: Flow Prefect có retry, idempotent và backfill bằng subflow
level: intermediate
services: []
files:
  - path: starter/flow.py
    note: 9 TODO
  - path: tests/test_flow.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/05-batch-pipelines/exercises/intermediate/03-prefect-flow -q
---

## Mục tiêu

Viết orchestration bằng Python thuần với Prefect 3: `@task` có retry, `@flow` tham số hoá theo
ngày, load idempotent, và backfill bằng cách gọi flow con (subflow) cho từng ngày.

## Đề bài

Nguồn là CSV `order_id, order_status, order_purchase_timestamp, amount`. Hàm `fetch_rows(path)`
đọc nguồn (đã làm sẵn); trong test nó bị thay bằng bản "chập chờn" lỗi `ConnectionError` 2 lần đầu.

Hoàn thành `starter/flow.py`:

1. `extract(path, ds)`: `@task(name="extract", retries=3, retry_delay_seconds=0, cache_policy=NO_CACHE)`.
   Gọi `fetch_rows(path)` qua tên hàm của module, giữ dòng có `order_purchase_timestamp` thuộc `ds`.
2. `transform(rows)`: `@task`. Bỏ dòng không có `order_id`, dedup theo `order_id` giữ dòng sau
   cùng, `order_status` strip + lower, `amount` float. Trả về list tuple
   `(order_id, order_status, amount)` sắp theo `order_id`.
3. `load(db_path, rows, ds)`: `@task`. Delete-insert partition `ds` vào bảng DuckDB
   `daily_orders(order_id VARCHAR, order_status VARCHAR, amount DOUBLE, ds DATE)` trong một
   transaction. Trả về số dòng đã chèn.
4. `olist_daily(path, db_path, ds)`: `@flow(name="olist-daily")`, trả về `{"ds": ds, "rows": n}`.
5. `backfill(path, db_path, start, end)`: `@flow(name="olist-backfill")`, gọi `olist_daily` cho từng
   ngày từ `start` tới `end` (gồm cả hai đầu), trả về list kết quả theo thứ tự ngày.

Dùng `cache_policy=NO_CACHE` cho các task: Prefect 3 mặc định tính cache key từ input, không cần ở
bài này. Test chạy flow trên Prefect server tạm (`prefect_test_harness`), mất khoảng 10–20 giây.
Muốn xem UI: `uv run prefect server start`, rồi chạy `uv run python starter/flow.py <csv> <ds>` ở
terminal khác với `PREFECT_API_URL=http://127.0.0.1:4200/api`.

## Tiêu chí đạt

- `extract`, `transform`, `load` là Prefect `Task`; `olist_daily`, `backfill` là `Flow` đúng tên.
- `extract` có ít nhất 3 retry; flow vượt qua 2 lần lỗi nguồn và hoàn thành.
- `transform` đúng quy tắc làm sạch.
- Chạy `olist_daily` hai lần cùng ngày không sinh trùng.
- `backfill` 3 ngày trả về đúng số dòng từng ngày; chạy lại một phần không làm đổi tổng số dòng.

## Gợi ý

### Gợi ý 1

```python
@task(name="extract", retries=3, retry_delay_seconds=0, cache_policy=NO_CACHE)
def extract(path, ds):
    return [r for r in fetch_rows(path) if r["order_purchase_timestamp"][:10] == ds]
```

Hàm gốc vẫn gọi được bằng `extract.fn(...)`, tiện để test logic không cần Prefect.

### Gợi ý 2

Trong flow, gọi task như hàm bình thường: `n = load(db_path, transform(extract(path, ds)), ds)`.
Gọi một flow bên trong flow khác tạo ra subflow, có run riêng trong UI. Duyệt ngày:
`date.fromisoformat(start) + timedelta(days=i)`.
