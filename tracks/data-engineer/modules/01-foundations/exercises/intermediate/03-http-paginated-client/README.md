---
title: HTTP client có retry, backoff và phân trang cursor
level: intermediate
services: []
files:
  - path: starter/client.py
    note: 3 TODO
  - path: tests/test_client.py
    note: Không sửa, test tự chạy một API giả trên 127.0.0.1
run:
  - uv run pytest tracks/data-engineer/modules/01-foundations/exercises/intermediate/03-http-paginated-client -q
---

## Mục tiêu

Viết lớp extract từ API đủ bền cho production: luôn có timeout, phân biệt lỗi tạm thời (retry) với
lỗi thật (fail ngay), exponential backoff, tôn trọng `Retry-After`, và duyệt mọi trang bằng cursor
dưới dạng generator.

## Đề bài

API đối tác trả đơn hàng ở `GET {base_url}/orders?limit=<n>&cursor=<c>` với header
`Authorization: Bearer <token>`. Response:

```json
{"data": [{"order_id": "o1", "order_status": "delivered"}], "next_cursor": "3"}
```

`next_cursor` là `null` ở trang cuối. Trang đầu không gửi `cursor`.

Hoàn thành `starter/client.py` (dùng `requests`):

1. **`backoff_delay(attempt, base=0.5, cap=30.0)`** trả `min(cap, base * 2**attempt)`.
2. **`get_json(session, url, params=None, *, headers=None, max_retries=3, base_delay=0.5, sleep=time.sleep)`**:
   - gọi `session.get(url, params=..., headers=..., timeout=DEFAULT_TIMEOUT)`;
   - status trong `RETRYABLE_STATUS` (429, 500, 502, 503, 504), `requests.ConnectionError` hoặc
     `requests.Timeout`: gọi `sleep(...)` rồi thử lại, tối đa `max_retries` lần (tức tối đa
     `max_retries + 1` request);
   - thời gian chờ: với 429 có header `Retry-After: <số giây>` thì chờ đúng số đó, còn lại chờ
     `backoff_delay(attempt, base_delay)` với `attempt` = 0 cho lần retry đầu;
   - status lỗi khác (401, 404…): raise `requests.HTTPError` ngay, không retry, không sleep;
   - hết lượt: raise lỗi cuối (`HTTPError` hoặc lỗi kết nối);
   - thành công: trả `resp.json()`.
3. **`iter_orders(base_url, token, *, page_size=100, session=None, max_retries=3, sleep=time.sleep)`**:
   **generator** trả từng đơn của mọi trang, dùng `get_json`. Không gọi API trước khi được duyệt.
   Tự tạo `requests.Session()` nếu không được truyền vào (và đóng nó khi xong).

Tham số `sleep` để test thay `time.sleep` bằng hàm ghi lại thời gian chờ, nên test chạy tức thì.

## Tiêu chí đạt

- `backoff_delay` đúng công thức và có trần.
- 503, 502 rồi 200: trả kết quả, đã chờ `[0.5, 1.0]`.
- 429 với `Retry-After: 2`: chờ `[2.0]`.
- Lỗi mãi: đúng `max_retries + 1` request rồi raise `HTTPError`.
- 404 và 401: một request duy nhất, raise `HTTPError`, không chờ.
- Lỗi kết nối (cổng đóng) được retry rồi raise `requests.ConnectionError`.
- Mọi request có `timeout`.
- `iter_orders` lấy đủ 7 đơn qua 3 trang (`page_size=3`), gửi đúng `limit`/`cursor`/`Authorization`,
  và là generator lazy.

## Gợi ý

### Gợi ý 1

Cấu trúc vòng lặp: `for attempt in range(max_retries + 1):`, trong đó `try: resp = session.get(...)`
`except (requests.ConnectionError, requests.Timeout)`. Ở lần cuối (`attempt == max_retries`) thì
raise thay vì sleep. `resp.raise_for_status()` raise `HTTPError` cho mọi status ≥ 400.

### Gợi ý 2

```python
cursor = None
while True:
    params = {"limit": page_size} | ({"cursor": cursor} if cursor else {})
    page = get_json(session, url, params, headers=headers, max_retries=max_retries, sleep=sleep)
    yield from page["data"]
    cursor = page.get("next_cursor")
    if not cursor:
        break
```

Đặt việc đóng session trong `try/finally` quanh vòng lặp để generator bị bỏ dở vẫn đóng kết nối.
