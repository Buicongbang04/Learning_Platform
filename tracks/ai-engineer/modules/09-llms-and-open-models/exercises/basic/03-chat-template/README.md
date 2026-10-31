---
title: Chat template viết tay và cắt lịch sử theo context
level: basic
services: []
files:
  - path: starter/chat_template.py
    note: 4 hàm TODO
  - path: tests/test_chat_template.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/09-llms-and-open-models/exercises/basic/03-chat-template -q
---

## Mục tiêu

Thấy tận mắt rằng "chat" chỉ là một chuỗi văn bản có thẻ đặc biệt mà model instruct đã học lúc fine-tune, và
mỗi họ model có một định dạng riêng. Bạn viết lại đúng từng ký tự template của Qwen2.5 (ChatML) và Llama 3, phân
tích ngược ChatML, và cắt lịch sử hội thoại cho vừa context.

## Đề bài

**Phần cứng:** CPU · ~40 phút

Trong `starter/chat_template.py`, chỉ dùng thư viện chuẩn, viết theo docstring:

1. `render_qwen(messages, add_generation_prompt=True)`: template Qwen2.5 khi không có `tools`, gồm system mặc định
   "You are Qwen, created by Alibaba Cloud..." khi hội thoại không có system, và cách gom các message `tool` liên
   tiếp vào **một** khối user với thẻ `<tool_response>`.
2. `render_llama3(messages, add_generation_prompt=True)`: template Llama 3 Instruct (`<|begin_of_text|>`,
   `<|start_header_id|>`, `<|eot_id|>`, nội dung bị strip, không có system mặc định).
3. `parse_chatml(text)`: đổi chuỗi ChatML về danh sách message, bỏ khối generation prompt chưa đóng.
4. `fit_history(messages, max_tokens, count_tokens, per_message=4)`: giữ system, lấy đoạn liên tục mới nhất vừa
   ngân sách, đoạn phải bắt đầu bằng message user, không vừa nổi message cuối thì `ValueError`.

Chuỗi mong đợi trong test được sinh bằng `tokenizer.apply_chat_template(..., tokenize=False)` của
`Qwen/Qwen2.5-0.5B-Instruct` và template Jinja trong `tokenizer_config.json` của Llama 3 8B Instruct: khớp test
nghĩa là khớp **từng ký tự** với cái model thật nhìn thấy.

## Tiêu chí đạt

- `render_qwen` khớp chuỗi thật trong 4 tình huống: chỉ user, có system riêng, system giữa hội thoại, nhiều kết
  quả tool liên tiếp; giữ nguyên khoảng trắng của nội dung.
- `render_llama3` khớp chuỗi thật, strip nội dung, không thêm system mặc định.
- `parse_chatml(render_qwen(msgs))` trả lại đúng `msgs`, kể cả nội dung nhiều dòng.
- `fit_history` đúng ở 5 ngân sách test: giữ hết, bỏ message cũ, bỏ assistant đứng đầu đoạn, không nhảy cóc,
  `ValueError` khi quá nhỏ.

## Gợi ý

### Gợi ý 1

Với tool, cần biết message trước và sau có phải `tool` không: mở `<|im_start|>user` khi message trước **không**
phải tool, đóng `<|im_end|>\n` khi message sau không phải tool (hoặc hết danh sách). Đó chính là logic trong
template Jinja gốc (`loop.index0`, `messages[loop.index0 - 1].role`).

### Gợi ý 2

`re.findall(r"<\|im_start\|>(\w+)\n(.*?)<\|im_end\|>", text, flags=re.S)` bắt từng khối: `re.S` cho `.` khớp cả
xuống dòng, `*?` không tham để mỗi khối dừng ở `<|im_end|>` gần nhất. Với `fit_history`, đi ngược từ cuối, cộng
dồn chi phí, `break` ở message đầu tiên không vừa (không `continue`: bỏ một message ở giữa làm hội thoại mất mạch).
