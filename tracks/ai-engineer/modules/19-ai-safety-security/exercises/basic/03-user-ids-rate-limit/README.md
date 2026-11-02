---
title: End-user ID, rate limit và theo dõi lạm dụng quanh lời gọi LLM
level: basic
services: []
files:
  - path: starter/abuse.py
    note: 1 hàm, 2 lớp, pipeline TODO
  - path: tests/test_abuse.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/19-ai-safety-security/exercises/basic/03-user-ids-rate-limit -q
---

## Mục tiêu

Dựng lớp vận hành mà nhà cung cấp API yêu cầu ở phía bạn: định danh người dùng cuối không lộ danh tính (để nhà cung
cấp và chính bạn lần ra ai lạm dụng mà không gửi email hay số điện thoại đi), giới hạn tốc độ theo từng người dùng, đếm
vi phạm và cấm có leo thang, và một pipeline moderation hai đầu quanh lời gọi LLM. Mục 5 lý thuyết giải thích vì sao
những thứ này là của **ứng dụng**, không phải của model.

## Đề bài

**Phần cứng:** CPU · ~75 phút

Trong `starter/abuse.py`, chỉ dùng thư viện chuẩn:

1. `user_key(user_id, secret)`: `"u_"` + 24 ký tự hex đầu của `HMAC-SHA256(secret, canon)`, `canon` là `user_id` đã
   `strip()` và `casefold()`, mã hoá UTF-8. `secret` rỗng hoặc `canon` rỗng thì `ValueError`. Đây là giá trị bạn gửi
   vào `safety_identifier` (OpenAI) hay `metadata.user_id` (Anthropic) và ghi vào log.
2. `TokenBucket(rate_per_s, capacity, clock)`: `rate_per_s <= 0` hoặc `capacity <= 0` thì `ValueError`. Mỗi `key` có
   một bucket riêng, lần đầu gặp thì đầy. Trước mỗi thao tác, nạp thêm `(bây giờ - lần trước) * rate` token, không quá
   `capacity`. `allow(key, cost=1)`: đủ token thì trừ và trả `True`, thiếu thì `False` và **không trừ**.
   `retry_after(key, cost=1)`: số giây phải chờ để đủ `cost` token (0 nếu đủ ngay, `inf` nếu `cost > capacity`).
3. `AbuseTracker(strikes, window_s, ban_s, clock)`: `record(key, reason)` ghi một vi phạm; chỉ đếm vi phạm trong
   `window_s` giây gần nhất (vi phạm cách đúng `window_s` giây là đã hết hạn). Khi số vi phạm còn hạn (kể cả lần vừa
   ghi) đạt `strikes`: cấm tới `bây giờ + ban_s * 2**n` (`n` là số lần đã bị cấm trước đó) và xoá danh sách vi phạm.
   `banned(key)`: còn trong thời gian cấm (thời điểm hết cấm thì không còn bị cấm). `history(key)`: lý do của các vi
   phạm còn hạn, theo thứ tự ghi.
4. `handle(user_id, text, *, secret, llm, moderate, limiter, tracker, log) -> Result`, theo đúng thứ tự:
   - `key = user_key(user_id, secret)`; đang bị cấm thì `Result("banned", REFUSAL)` (không tốn token rate limit);
   - `limiter.allow(key)` sai thì `Result("rate_limited", REFUSAL)`;
   - `moderate(text)` trả danh sách nhãn vi phạm; khác rỗng thì ghi vi phạm `"input:" + ",".join(nhãn)` và trả
     `Result("blocked_input", REFUSAL, nhãn)`, **không** gọi LLM;
   - `reply = llm([{"role": "user", "content": text}], key)`; `moderate(reply)` khác rỗng thì ghi vi phạm
     `"output:..."` và trả `Result("blocked_output", REFUSAL, nhãn)` (người dùng không thấy câu trả lời bị chặn);
   - còn lại `Result("ok", reply)`.
   - Mỗi lần gọi thêm đúng một dòng `{"user": key, "status": ..., "flags": [...]}` vào `log`. `user_id` gốc không bao giờ
     tới `llm` hay `log`.

## Tiêu chí đạt

- `user_key` khớp HMAC tính tay, ổn định qua hoa thường và khoảng trắng, khác khi đổi secret, không phải SHA-256 trần.
- Token bucket: cho đúng `capacity` request liền, nạp lại theo thời gian, không vượt `capacity` sau thời gian dài, mỗi
  người dùng độc lập, lần bị từ chối không trừ token, `retry_after` đúng.
- Tracker: cấm khi đủ vi phạm trong cửa sổ, vi phạm cũ hết hạn, lần cấm thứ hai dài gấp đôi, xoá đếm khi bắt đầu cấm.
- Pipeline: đúng thứ tự các cổng, không gọi LLM khi input bị chặn hay người dùng bị cấm, câu trả lời bị chặn không tới
  người dùng, log chỉ có khoá băm.

## Gợi ý

### Gợi ý 1

Token bucket không cần luồng chạy nền: lưu cho mỗi `key` một cặp (số token, thời điểm cập nhật), và chỉ tính lượng nạp
thêm khi có request. `hmac.new(secret, data, hashlib.sha256).hexdigest()` cho HMAC.

### Gợi ý 2

Thứ tự cổng trong `handle` là thiết kế: cổng rẻ và không cần đọc nội dung đứng trước (cấm, rate limit), cổng tốn tiền
(LLM) đứng sau cùng. Người dùng bị cấm mà vẫn bị trừ token thì hết cấm xong lại bị rate limit oan.
