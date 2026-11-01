# Lời giải: end-user ID, rate limit và theo dõi lạm dụng

## Cách làm

**`user_key`**: `"u_" + hmac.new(secret, canon.encode("utf-8"), hashlib.sha256).hexdigest()[:24]`. 24 ký tự hex là
96 bit, dư để không trùng giữa hàng tỉ người dùng, và ngắn hơn giới hạn độ dài của các API (OpenAI khuyên không quá 128
ký tự cho `user` của Images API; Anthropic cho `metadata.user_id` tới 512 ký tự, kiểm trên tài liệu ngày 2026-11-01).

**`TokenBucket`**: lưu `(tokens, last)` cho mỗi khoá. `_level(key)` nạp `min(capacity, tokens + (now - last) * rate)`
và cập nhật `last`; `allow` trừ khi đủ. `retry_after = max(0, (cost - tokens) / rate)`.

**`AbuseTracker`**: mỗi khoá một danh sách `(thời điểm, lý do)`; mỗi lần `record` lọc bỏ phần quá hạn
(`now - t < window_s` mới giữ), thêm lần mới, đủ `strikes` thì đặt `until = now + ban_s * 2**n`, tăng `n`, xoá danh sách.

**`handle`**: các cổng theo thứ tự đề bài, một hàm nhỏ `done(result)` vừa ghi log vừa trả kết quả để không quên ghi ở
nhánh nào.

## Vì sao như vậy

- **HMAC, không phải băm trần.** Tài liệu safety best practices của OpenAI khuyên băm username hay email trước khi gửi
  `safety_identifier`; tài liệu Messages API của Anthropic yêu cầu `metadata.user_id` là UUID, hash hay định danh mờ,
  không chứa tên, email, số điện thoại (cả hai kiểm ngày 2026-11-01). Băm trần SHA-256 của email đáp ứng chữ nhưng
  không đáp ứng ý: ai có danh sách email (rò rỉ, mua bán) thì dò ngược được. HMAC với secret của server thì không, và
  vẫn ổn định để nhà cung cấp gom các request của cùng một người. Xoay secret là "xoá" liên kết giữa log cũ và người
  dùng, hữu ích khi xử lý yêu cầu xoá dữ liệu.
- **Token bucket** cho phép burst ngắn (người dùng gõ nhanh vài câu) nhưng chặn tốc độ trung bình; đây là thuật toán mà
  nhiều API gateway dùng. Rate limit theo khoá người dùng, không chỉ theo IP: nhiều người dùng chung NAT, một kẻ lạm
  dụng đổi IP dễ dàng. Với LLM, chi phí tính bằng token nên `cost` có thể là số token ước lượng của request, không phải 1.
- **Leo thang** (`2**n`): một lần vi phạm do hiểu lầm không nên khoá người dùng lâu, nhưng kẻ cố tình thì mỗi lần quay
  lại bị cấm lâu hơn. Xoá đếm khi bắt đầu cấm để lần hết cấm đầu tiên không bị cấm lại ngay vì vi phạm cũ.
- **Vi phạm ở output cũng là vi phạm của người dùng**: người cố dẫn model tới nội dung xấu qua câu hỏi trông vô hại
  sẽ không bị cổng input bắt, nhưng output thì có.

## Giới hạn

- Trạng thái nằm trong bộ nhớ một tiến trình. Production có nhiều tiến trình nên cần kho dùng chung (Redis với
  `INCR`/`EXPIRE` hoặc script Lua cho token bucket) và đồng hồ chung.
- `moderate` ở đây là hàm giả; mục 5 lý thuyết và bài Advanced 02 dùng LLM làm moderator và đo nó sai ở đâu.
- Người dùng chưa đăng nhập không có `user_id` ổn định: dùng session ID (tài liệu OpenAI cũng gợi ý vậy), kèm rate limit
  theo IP làm lớp ngoài.

## Bẫy thường gặp

- Trừ token cả khi từ chối: người dùng bị chặn liên tục không bao giờ hồi lại.
- Kiểm rate limit trước khi kiểm cấm: người bị cấm vẫn tiêu token.
- Ghi `user_id` gốc vào log "để debug": log là nơi rò rỉ PII phổ biến nhất.
- Trả câu trả lời đã bị moderation output chặn cho người dùng "kèm cảnh báo".
