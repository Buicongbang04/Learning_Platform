---
title: Context engineering - cắt observation, rút gọn lịch sử, ép vào ngân sách token
level: basic
services: []
files:
  - path: starter/context.py
    note: truncate_middle, compact_history, fit_messages TODO
  - path: tests/test_context.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/16-ai-agents/exercises/basic/03-context-budget -q
---

## Mục tiêu

Viết ba công cụ quản lý context cho agent chạy nhiều bước: cắt phần giữa của một observation quá dài, rút gọn
observation cũ ("tool result clearing"), và ép cả lịch sử vào một ngân sách token mà **không bao giờ** mất system
prompt và yêu cầu của người dùng. Đó là thứ Ollama không làm cho bạn: khi prompt vượt `num_ctx`, nó lặng lẽ bỏ các
message cũ nhất, kể cả task (mục 3 lý thuyết đo hiện tượng này).

## Đề bài

**Phần cứng:** CPU · ~50 phút

Trong `starter/context.py` (`approx_tokens`, `messages_tokens`, `_marker`, `dropped_note` đã có). Mọi hàm nhận
`count` (hàm đếm token của một chuỗi) để test dùng bộ đếm chính xác; mặc định là `approx_tokens`.

1. `truncate_middle(text, max_tokens, count)`: vừa thì trả nguyên văn; không thì giữ `k` ký tự đầu và `k` ký tự cuối
   quanh `_marker(len(text) - 2k)`, với `k` **lớn nhất** để kết quả vừa `max_tokens`; không chứa nổi cả dấu cắt thì
   `ContextOverflowError`.
2. `compact_history(messages, keep_last=2, stub_chars=60)`: giữ nguyên `keep_last` observation cuối (message `user`
   bắt đầu bằng `"Observation: "`), observation cũ hơn mà phần thân dài hơn `stub_chars` thì thay bằng
   `"Observation: [đã rút gọn, <độ dài thân> ký tự] <stub_chars ký tự đầu của thân>..."`. Không sửa đầu vào.
3. `fit_messages(messages, budget, count, keep_last=4)`: vừa ngân sách thì trả bản sao; không thì giữ
   `messages[0]` (system) và `messages[1]` (task), thêm `dropped_note(n)`, rồi đoạn đuôi liên tục **dài nhất** của phần
   còn lại sao cho tổng (tính cả ghi chú, mỗi message cộng `MSG_OVERHEAD`) vừa `budget`. Giữ được ít hơn
   `min(keep_last, số message sau task)` thì `ContextOverflowError`.

## Tiêu chí đạt

- `truncate_middle` giữ đúng đầu và đuôi cùng độ dài, kết quả vừa ngân sách và là **cực đại** (giữ thêm một ký tự mỗi
  đầu là vượt), chạy đúng với cả bộ đếm theo ký tự lẫn theo từ, báo lỗi khi ngân sách quá nhỏ.
- `compact_history` đúng định dạng rút gọn, không đụng observation ngắn và message không phải observation,
  `keep_last=0` rút gọn hết, không sửa list hay dict đầu vào.
- `fit_messages` luôn giữ system và task, phần giữ lại là đoạn đuôi liên tục dài nhất, ghi chú nêu đúng số message bị
  bỏ, báo `ContextOverflowError` khi không giữ nổi `keep_last` message cuối, không sửa đầu vào.

## Gợi ý

### Gợi ý 1

Độ dài kết quả của `truncate_middle` tăng theo `k`, nên có thể tìm `k` lớn nhất bằng tìm kiếm nhị phân trên
`0..len(text)//2` (với bộ đếm theo từ, không suy ra `k` bằng phép chia được). Chú ý số ký tự bị cắt nằm trong dấu cắt:
đổi `k` thì độ dài dấu cắt cũng đổi.

### Gợi ý 2

Với `fit_messages`, thử giữ đoạn đuôi dài nhất trước rồi ngắn dần, dừng ở lựa chọn đầu tiên vừa ngân sách. Nhớ rằng
ghi chú "đã lược bỏ" cũng tốn token và phải được tính. Dùng `[dict(m) for m in ...]` khi trả kết quả để người gọi sửa
kết quả không làm hỏng lịch sử gốc.
