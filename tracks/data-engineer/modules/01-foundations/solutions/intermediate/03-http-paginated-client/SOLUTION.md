# Lời giải: HTTP client có retry, backoff và phân trang cursor

## Cách làm

**Phân loại lỗi là phần quan trọng nhất.**

| Tình huống | Hành động | Lý do |
| --- | --- | --- |
| `ConnectionError`, `Timeout` | Retry | Mạng chập chờn, server đang khởi động lại |
| 429 | Retry, chờ `Retry-After` nếu có | Server nói rõ khi nào quay lại |
| 500, 502, 503, 504 | Retry với backoff | Lỗi tạm thời phía server/gateway |
| 400, 401, 403, 404, 422 | Raise ngay | Gọi lại cũng sai y như vậy; retry chỉ làm chậm phát hiện lỗi |

**`get_json`**: một vòng `for attempt in range(max_retries + 1)`. Ở lần thử cuối không sleep mà
raise (lỗi kết nối thì `raise` lại exception, lỗi HTTP thì `raise_for_status()`), để người gọi
(và Airflow) thấy lỗi thật. Mỗi lần retry ghi log `WARNING` với thời gian chờ, giúp debug khi job chậm
bất thường.

**Timeout**: `requests` mặc định chờ **vô hạn**. Một API treo sẽ giữ worker Airflow mãi mãi. Tuple
`(3.05, 30)` là (connect timeout, read timeout); connect ngắn vì bắt tay TCP thường mất vài chục ms.

**`Retry-After`** có thể là số giây hoặc một ngày giờ HTTP; lời giải xử lý dạng số, dạng còn lại
quay về backoff.

**`iter_orders`** là generator: chỉ gọi API khi người dùng duyệt tới, nên có thể
`for batch in batched(iter_orders(...), 1000): upsert(batch)` mà không giữ mọi trang trong RAM.
`try/finally` đóng session kể cả khi người dùng dừng giữa chừng (generator bị `close()`).
`Session` giữ kết nối TCP/TLS (keep-alive) giữa các trang, nhanh hơn mở kết nối mới mỗi request.

## Jitter (không yêu cầu trong bài, nhưng nên có ở production)

Nhiều worker cùng gặp 503 sẽ retry đúng cùng lúc (0.5s, 1s, 2s…) và đánh sập server lần nữa.
Thêm ngẫu nhiên: `sleep(random.uniform(0, backoff_delay(attempt)))` ("full jitter" theo bài viết
của AWS). Bài này không dùng jitter để test xác định được.

## Mở rộng

- Thay vòng retry tự viết bằng `urllib3.util.Retry` gắn vào `HTTPAdapter`, hoặc thư viện `tenacity`.
- Lưu `next_cursor` cuối cùng đã xử lý (checkpoint) để job chết giữa chừng chạy lại từ đó.
- Rate limit chủ động (token bucket) khi API công bố quota, thay vì đợi 429.
- Viết bản async bằng `httpx.AsyncClient` khi cần gọi nhiều endpoint song song.
