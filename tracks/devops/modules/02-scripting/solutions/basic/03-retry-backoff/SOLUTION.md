# Lời giải: retry có exponential backoff

Script đầy đủ ở `retry.sh` cạnh tệp này.

## Cách làm

1. **`set -uo pipefail`, không có `-e`.** Wrapper này tồn tại để xử lý lệnh thất bại; với `-e`, lần thất bại đầu tiên
   giết luôn wrapper. Đây là ví dụ điển hình: strict mode là mặc định tốt, không phải luật bất di bất dịch. Bỏ `-e` thì
   mọi chỗ cần dừng khi lỗi phải tự kiểm.
2. **`getopts` dừng ở từ đầu tiên không phải option**, nên `retry.sh -n 3 curl -f url` hiểu `curl` là lệnh và `-f`
   thuộc về curl. `--` vẫn nên viết khi lệnh của bạn có thể bắt đầu bằng `-`.
3. **`"$@"` nguyên vẹn.** Viết `$*` hay `$@` không ngoặc là tách lại theo khoảng trắng và mở glob: `"a b"` thành hai
   tham số, `*` thành danh sách tệp trong thư mục hiện tại.
4. **Danh sách mã tạm thời là tham số**, không đoán. Chỉ người gọi biết lệnh của mình dùng mã nào cho lỗi tạm thời.
5. **Trần trước, nhân đôi sau.** `delay=$((delay * 2 < max ? delay * 2 : max))` không bao giờ vượt `max`, nên không
   tràn số kể cả với `-n 1000`.
6. **Seam cho thời gian.** `RETRY_SLEEP_CMD` cho test thay `sleep` bằng một script ghi lại số giây: test chạy tức thì
   và kiểm được chính xác dãy backoff. Đây là cùng một ý với tham số `sleep=time.sleep` trong code Python, hay
   `clock` giả trong Go: mọi thứ phụ thuộc thời gian thật hoặc mạng thật cần một chỗ để thay.

## Lỗi nào nên retry

| Loại | Ví dụ | Retry? |
| --- | --- | --- |
| Mạng chập chờn | Connection refused khi service đang khởi động, timeout, DNS tạm lỗi | Có |
| Server quá tải, tạm không phục vụ | HTTP `429`, `502`, `503`, `504`; Postgres `too many connections` | Có, tôn trọng `Retry-After` nếu có |
| Lỗi của chính request | HTTP `400`, `404`, `422`; tham số sai; SQL sai cú pháp | Không: lần sau vẫn sai |
| Xác thực | HTTP `401`, `403`; mật khẩu sai | Không: retry còn làm khoá tài khoản |
| Thao tác không idempotent đã có thể thành công | `POST /orders` timeout sau khi server đã ghi | Chỉ khi có idempotency key |

Timeout là trường hợp khó nhất: bạn không biết request đã tới server chưa. Retry an toàn khi thao tác **idempotent**
(GET, PUT ghi đè, `pg_dump`, `mkdir -p`) hoặc có **idempotency key** (Stripe, AWS dùng header hoặc client token để
server nhận ra request lặp lại).

## Jitter và thundering herd

100 worker cùng mất kết nối Redis lúc 10:00:00. Không jitter, cả 100 thử lại đúng 10:00:01, 10:00:03, 10:00:07...:
Redis vừa lên lại bị đánh một đợt 100 kết nối cùng lúc, có thể ngã lần nữa. Full jitter (`random(0, backoff)`) trải
đều các lần thử trong cả khoảng, tổng tải giống nhau nhưng không có đỉnh. Bài "Exponential Backoff And Jitter" của AWS
Architecture Blog đo cho thấy full jitter giảm tổng số lời gọi và thời gian hoàn thành so với không jitter.

Retry nhiều tầng còn nhân nhau: client retry 3 lần, gọi API gateway retry 3 lần, gọi service retry 3 lần thành 27 lần
vào DB đang quá tải. Quy tắc thực tế: chỉ retry ở **một** tầng (thường là tầng gần người dùng nhất), các tầng dưới
fail nhanh; thêm **retry budget** hoặc circuit breaker (module 15) khi hệ thống lớn.

## Trong thực tế

- `curl --retry 5 --retry-delay 1 --retry-max-time 60 --retry-connrefused` có sẵn backoff cho riêng curl.
- `systemd`: `Restart=on-failure` với `RestartSec=` và `RestartSteps=`/`RestartMaxDelaySec=` (systemd 254+) cho backoff
  tăng dần ở mức service.
- Kubernetes: `CrashLoopBackOff` chính là exponential backoff (10 giây, gấp đôi, trần 5 phút) cho container khởi động
  lỗi.
- Python: thư viện `tenacity`; Go: `cenkalti/backoff`. Trong Bash, một hàm `retry` 20 dòng như bài này là đủ cho
  `bootstrap.sh` của capstone m01.
