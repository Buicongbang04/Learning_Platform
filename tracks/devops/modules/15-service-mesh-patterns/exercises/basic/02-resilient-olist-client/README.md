---
title: Client Olist Shop có retry, backoff, jitter và circuit breaker, kiểm bằng server bơm lỗi
level: basic
services: []
files:
  - path: starter/resilient.py
    note: 7 TODO
  - path: tests/fixtures/fake_olist.py
    note: Server HTTP giả bơm lỗi theo kịch bản
  - path: tests/fixtures/driver.py
    note: Các kịch bản test chạy trong sandbox
  - path: tests/test_resilient_client.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/15-service-mesh-patterns/exercises/basic/02-resilient-olist-client -q
---

## Mục tiêu

Viết trong code những pattern mà mesh làm hộ ở tầng mạng: retry chỉ cho lỗi tạm thời, exponential backoff với full jitter, tôn trọng
`Retry-After`, deadline cho cả lời gọi, circuit breaker ba trạng thái, và retry an toàn cho POST bằng Idempotency-Key. Kiểm bằng một
server giả bơm lỗi, đồng hồ giả và seed cố định, nên test không bao giờ chập chờn.

## Đề bài

Hoàn thiện `starter/resilient.py`. `_send` (gửi một request, trả `(status, headers, body)`, ném `OSError` khi mất kết nối hay quá
timeout) và các lớp lỗi đã có sẵn.

**`backoff_delay(attempt, base, cap, rng)`**: full jitter, trả số ngẫu nhiên trong `[0, min(cap, base * 2^(attempt-1))]` lấy từ
`rng.uniform`, với `attempt` là số lần thử đã thất bại (1, 2, ...). Luôn dùng `rng` được truyền vào, không dùng module `random`.

**`CircuitBreaker(failure_threshold, reset_timeout, clock)`**:

| Trạng thái | `state` | `allow()` | Chuyển sang |
| --- | --- | --- | --- |
| Đóng | `"closed"` | `True` | Mở khi số lần thất bại **liên tiếp** đạt `failure_threshold`; `record_success()` đưa bộ đếm về 0 |
| Mở | `"open"` | `False` | Nửa mở khi `clock() - lúc mở >= reset_timeout` |
| Nửa mở | `"half_open"` | `True` cho đúng một request thử, `False` cho mọi lần gọi sau cho tới khi có kết quả | `record_success()` về Đóng; `record_failure()` về Mở, đếm lại thời gian từ lúc đó |

**`OlistClient._call(method, path, body, headers)`**, dùng cho `get_order` (`GET /orders/<id>`) và `create_payment`
(`POST /payments`, body `{"order_id", "amount"}`). Thử tối đa `max_attempts` lần; mỗi lần thử:

1. Có breaker mà `allow()` trả `False`: ném `CircuitOpenError` ngay, không gửi request, không ngủ.
2. Gửi bằng `_send` với timeout `min(timeout, phần deadline còn lại)`.
3. Phân loại kết quả:

   | Kết quả | Breaker | Hành động |
   | --- | --- | --- |
   | 2xx | `record_success()` | Trả JSON đã parse |
   | 4xx khác 429 (400, 404, 409...) | `record_success()` (upstream vẫn trả lời đúng) | Ném `UpstreamError(status)`, không thử lại |
   | 500 và 5xx khác 502, 503, 504 | `record_failure()` | Ném `UpstreamError(status)`, không thử lại (thường là bug, thử lại vô ích) |
   | 429, 502, 503, 504, hay `OSError` (timeout, mất kết nối) | `record_failure()` | Thử lại nếu còn lượt |

4. Trước khi thử lại: nếu breaker vừa rời trạng thái Đóng thì ném `CircuitOpenError` ngay (không ngủ). Thời gian chờ là giá trị
   `Retry-After` (số giây nguyên) khi response 429 hay 503 có header đó, ngược lại là `backoff_delay(attempt, base_delay, max_delay, rng)`.
   `Retry-After` được tôn trọng kể cả khi lớn hơn `max_delay`.
5. Deadline: chỉ ngủ khi `thời gian đã trôi + thời gian chờ < deadline` (đo bằng `clock`, tính từ đầu lời gọi). Không thì dừng.
6. Hết lượt hay dừng vì deadline: ném `UpstreamError` với status của lần thử cuối (`0` nếu lần cuối là `OSError`).

Ngủ bằng `self.sleep`, đo thời gian bằng `self.clock`; test truyền đồng hồ giả (ngủ là cộng giờ, không ngủ thật).

`create_payment` sinh **một** Idempotency-Key (ví dụ `uuid.uuid4().hex`) cho mỗi lần gọi và gửi đúng key đó ở header `Idempotency-Key`
cho mọi lần thử của lần gọi ấy; payment khác có key khác. `get_order` không gửi header này.

**Cách test chấm.** Mỗi test chạy `tests/fixtures/driver.py` trong sandbox bubblewrap (như module 02): driver nạp `resilient.py` của bạn,
dựng `FakeOlist` trên `127.0.0.1` cổng ngẫu nhiên với kịch bản cho từng path (mã HTTP, `Retry-After`, `"slow"` ngủ 0,6 giây,
`"reset"` đóng kết nối không trả lời), chạy một kịch bản với đồng hồ giả và `random.Random(7)`, rồi in JSON để test so: số request
server nhận, các lần chờ, lỗi ném ra, trạng thái breaker, Idempotency-Key. Kịch bản gồm: lỗi tạm thời rồi thành công, hết lượt, 404,
500, 429 kèm `Retry-After`, `Retry-After` vượt deadline, timeout và mất kết nối, deadline cắt chuỗi chờ, jitter (cận trên, seed khác
nhau, cùng seed), breaker mở và hồi phục, request thử ở nửa mở thất bại, nửa mở chỉ cho một request, breaker mở giữa vòng retry,
payment giữ key qua các lần thử, GET không có key, timeout mỗi lần thử co lại theo deadline, 409 của payment. Chạy dưới 5 giây.

## Tiêu chí đạt

- Mọi test pass.
- Giải thích được vì sao full jitter tốt hơn backoff cố định khi hàng nghìn client cùng lỗi một lúc.
- Nói được vì sao 404 không được làm mở breaker còn 500 thì có, và vì sao 500 vẫn không được thử lại.
- Giải thích được vì sao retry POST /payments mà không có Idempotency-Key có thể trừ tiền khách hai lần, và phía server phải làm gì
  với key đó.

## Gợi ý

### Gợi ý 1

Breaker chỉ cần ba biến: số lần thất bại liên tiếp, thời điểm mở (hay `None`), và cờ "đang có request thử". `state` tính từ thời
điểm mở và `clock()`, không cần lưu riêng trạng thái nửa mở.

### Gợi ý 2

Đọc header không phân biệt hoa thường: `{k.lower(): v for k, v in headers.items()}.get("retry-after")`. Viết vòng `for attempt in
range(1, max_attempts + 1)`, xử lý từng trường hợp trong bảng rồi `continue` hay `raise`; ngủ ở cuối vòng, sau khi đã kiểm breaker và
deadline.
