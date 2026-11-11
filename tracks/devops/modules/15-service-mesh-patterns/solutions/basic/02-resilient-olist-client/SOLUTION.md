# Lời giải: client Olist Shop có retry, backoff, jitter và circuit breaker

## Cách làm

- `backoff_delay` một dòng: `rng.uniform(0, min(cap, base * 2 ** (attempt - 1)))`. Tính trần trước khi nhân với số ngẫu nhiên, nên
  delay không bao giờ vượt `cap`.
- `CircuitBreaker` giữ `failures`, `opened_at`, `trial_in_flight`. `state` suy ra từ `opened_at` và `clock()`: chưa mở là `closed`, đã
  mở và chưa đủ `reset_timeout` là `open`, đủ rồi là `half_open`. `allow()` ở `half_open` bật `trial_in_flight` cho request đầu tiên,
  các lần sau trả `False`. `record_failure()` khi đã mở (tức request thử thất bại) đặt lại `opened_at = clock()`.
- `_call` làm theo đúng thứ tự: hỏi breaker, gửi, phân loại, ghi vào breaker, quyết định thử lại, kiểm breaker lần nữa, tính chờ (ưu tiên
  `Retry-After`), kiểm deadline, ngủ.
- `create_payment` sinh key một lần ngoài vòng thử và truyền vào `_call`, nên mọi lần thử gửi cùng key.

## Vì sao các quyết định này

- **Full jitter** (AWS Architecture Blog, "Exponential Backoff and Jitter"): khi nhiều client cùng lỗi một lúc, backoff cố định làm
  chúng cùng thử lại một lúc, tạo các đợt tải đồng bộ. Lấy ngẫu nhiên trong cả khoảng `[0, cap]` dàn đều tải, tổng thời gian chờ trung
  bình còn thấp hơn "equal jitter".
- **Chỉ thử lại lỗi tạm thời**: 429, 502, 503, 504, timeout, mất kết nối thường tự hết. 4xx là lỗi của request, thử lại vẫn thế. 500 hay
  là bug, thử lại nhân tải lên một service đang lỗi.
- **4xx không làm mở breaker**: breaker đo sức khoẻ của upstream. 404 nghĩa là upstream khoẻ và trả lời đúng; đếm nó là lỗi thì một đợt
  người dùng gõ sai mã đơn có thể chặn cả trang đơn hàng.
- **Tôn trọng `Retry-After`**: server đang nói rõ nó cần bao lâu; thử sớm hơn chỉ thêm tải vào lúc nó yếu nhất.
- **Deadline cho cả lời gọi**: người dùng không chờ quá vài giây; retry vượt deadline là tốn tài nguyên cho một câu trả lời không ai đọc.
  Truyền phần deadline còn lại làm timeout của lần thử (deadline propagation).
- **Breaker cắt vòng retry**: khi breaker đã mở, các lần thử còn lại chắc chắn bị chặn; ngủ rồi mới phát hiện là phí thời gian của
  người gọi.
- **Idempotency-Key**: timeout không nói server đã làm hay chưa. Gửi lại với cùng key, server tra key, thấy đã xử lý thì trả kết quả cũ
  thay vì trừ tiền lần nữa. Server phải lưu key cùng kết quả (bảng có ràng buộc unique, có TTL), và trả 409 khi cùng key mà body khác.

## Liên hệ với mesh

Linkerd làm được retry, timeout ở tầng proxy (bài Intermediate 01) cho mọi ngôn ngữ, có metric retry và giới hạn số lần thử. Nhưng mesh
không biết request nào idempotent ngoài method HTTP, không đọc được nghiệp vụ để chọn fallback, và breaker của Linkerd (failure accrual)
loại endpoint lỗi khỏi cân bằng tải chứ không trả lỗi nhanh cho ứng dụng. Thực tế dùng cả hai, và chỉ retry ở **một** tầng.

## Lỗi hay gặp

- Dùng `random.uniform` toàn cục: test cùng seed ra khác dãy.
- Retry cả 500 và 4xx.
- Sinh Idempotency-Key trong vòng thử: mỗi lần thử một key, server coi là payment mới.
- Ngủ rồi mới kiểm deadline: vượt deadline một khoảng bằng lần chờ cuối.
- Breaker đếm tổng số lỗi thay vì lỗi liên tiếp: một service lỗi 1% rồi cũng có ngày mở breaker.
