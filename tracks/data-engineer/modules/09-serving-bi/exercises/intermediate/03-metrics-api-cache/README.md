---
title: Lớp serving cho API metric có cache và phân trang
level: intermediate
services: []
files:
  - path: starter/serving.py
    note: 5 TODO
  - path: tests/test_serving.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/09-serving-bi/exercises/intermediate/03-metrics-api-cache -q
---

## Mục tiêu

Viết phần lõi của một API phục vụ dữ liệu từ bảng aggregate: validate tham số chặt chẽ, query tham số hoá, phân
trang, cache TTL với cache key có `data_version` để tự invalidate khi pipeline refresh, và adapter trả mã HTTP.

## Đề bài

Bảng `agg_daily_sales(order_date, customer_state, orders, revenue)` đã có trong DuckDB (test tạo). Hoàn thiện
`starter/serving.py`:

1. `TTLCache.get/set`: key hết hạn sau `ttl` giây theo `clock()` (truyền vào để test điều khiển thời gian); đếm
   `hits`, `misses`.
2. `MetricsService.validate(...)`: quy tắc trong docstring (state 2 chữ cái, ngày ISO, `start <= end`, khoảng tối đa
   366 ngày, `limit` 1..500, `offset >= 0`). Sai thì raise `ValidationError`.
3. `MetricsService.get_daily_sales(...)`: trả `data`, `total`, `limit`, `offset`, `data_version`. `order_date` trả về
   dạng chuỗi `YYYY-MM-DD`. Cache theo tham số **đã chuẩn hoá** cộng `data_version()`; chỉ tăng `queries_executed`
   khi phải xuống DB.
4. `handle_request(service, query)`: nhận dict chuỗi như query string của URL, trả `(200, body)` hoặc
   `(400, {"error": …})`.

Phần này không dùng web framework để test đơn giản. Bọc vào FastAPI chỉ cần vài dòng (xem Gợi ý 2).

## Tiêu chí đạt

- Phân trang đúng thứ tự `order_date, customer_state`; `total` là số dòng trước phân trang.
- `state="sp"` và `state="SP"` dùng chung cache entry.
- Đổi `data_version` thì lần gọi sau xuống DB và thấy dữ liệu mới; hết TTL cũng vậy.
- Mọi tham số sai (kể cả chuỗi kiểu `SP' OR '1'='1`) bị từ chối trước khi chạm DB.
- `handle_request` trả 400 khi `limit` không phải số.
- `uv run pytest … -q` pass 16 test.

## Gợi ý

### Gợi ý 1

Lưu `(expires_at, value)` trong dict của cache. Validate bằng whitelist: regex `^[A-Z]{2}$` cho state,
`datetime.date.fromisoformat` cho ngày (kiểm tra thêm định dạng bằng regex vì Python 3.11+ chấp nhận cả dạng
`20180801`). `isinstance(True, int)` là `True` trong Python, nên phải loại `bool` riêng.

### Gợi ý 2

DuckDB nhận tham số cho cả `LIMIT ? OFFSET ?`. Cache key nên là tuple bất biến, ví dụ
`("daily_sales", state, start, end, limit, offset, version)`. Bọc FastAPI:

```python
from fastapi import FastAPI, HTTPException
app = FastAPI()
@app.get("/daily-sales")
def daily_sales(start: str, end: str, state: str | None = None, limit: int = 100, offset: int = 0):
    try:
        return service.get_daily_sales(state, start, end, limit, offset)
    except ValidationError as e:
        raise HTTPException(400, str(e))
```
