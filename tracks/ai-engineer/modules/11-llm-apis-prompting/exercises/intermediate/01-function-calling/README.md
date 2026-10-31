---
title: Function calling viết tay - registry, kiểm tham số, vòng lặp, native và prompted
level: intermediate
services: []
files:
  - path: starter/tools.ipynb
    note: 4 hàm TODO
  - path: tests/test_tools.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py uit-vsfc
  - ollama pull qwen2.5:3b
  - uv run jupyter lab tracks/ai-engineer/modules/11-llm-apis-prompting/exercises/intermediate/01-function-calling/starter/tools.ipynb
  - uv run pytest tracks/ai-engineer/modules/11-llm-apis-prompting/exercises/intermediate/01-function-calling -q
---

## Mục tiêu

Tự viết toàn bộ phần "function calling" nằm ngoài model: thực thi tool call có kiểm tham số, vòng lặp gửi kết quả lại
cho tới khi model trả lời, xử lý mọi kiểu lỗi mà không crash, và một lớp tool calling bằng prompt cho LLM không có
trường `tools`. Rồi đo hai cách gọi tool với `qwen2.5:3b` trên câu hỏi thật về dữ liệu UIT-VSFC. Đây là lõi của mọi
agent (module 16) và mọi framework (module 17), viết một lần bằng tay để thấy nó.

## Đề bài

**Phần cứng:** CPU · ~90 phút

Mở `starter/tools.ipynb`. `TOOLS` (ba tool: đếm phản hồi theo chủ đề/cảm xúc, tính phần trăm, lấy câu mẫu) đã có.
Trong các cell chấm điểm:

1. `make_registry(df)`: ba hàm Python chạy trên `DataFrame` kiểu UIT-VSFC, trả dict (notebook có bảng định nghĩa).
2. `execute_tool_call(call, tools, registry) -> str`: thực thi một tool call dạng OpenAI (`arguments` là chuỗi JSON
   hoặc dict), kiểm tham số bằng `jsonschema` theo `parameters` của tool; mọi lỗi (tool lạ, JSON hỏng, sai schema,
   hàm ném lỗi) thành chuỗi `"ERROR: ..."` đủ thông tin để model tự sửa, không bao giờ ném exception.
3. `run_tool_loop(chat, messages, tools, registry, max_steps=5) -> LoopResult`: vòng lặp gọi `chat`, thực thi tool,
   thêm message `tool`, dừng khi model trả lời văn bản hoặc hết `max_steps`; tự đặt `id` cho tool call thiếu id.
4. `prompted_chat(llm)`: bọc một LLM chỉ nhận và trả chuỗi (như `llmkit.chat`) thành hàm `chat(messages, tools)` cùng
   giao diện: mô tả tool và giao thức JSON trong system prompt, ép output bằng `json_schema=PROMPTED_SCHEMA`, đổi lịch
   sử có tool call thành chuỗi.

Notebook mô tả chính xác định dạng từng message. Rồi chạy các cell `explore`: 12 câu hỏi (10 câu có đáp án số tính
từ tập test, một câu cần `list_examples`, một câu ngoài phạm vi), mỗi câu chạy hai cách **native** (trường `tools`
của Ollama) và **prompted**, in bảng đúng/sai, số bước, số lỗi tool, thời gian; và một thí nghiệm đưa cho model một
kết quả `ERROR:` xem nó có tự sửa tham số không. Khoảng 50 lượt gọi model, dưới 2 phút trên PC của track.

Sau đó làm phần trắc nghiệm của bài trong app. Câu trả lời của model có thể lệch giữa các máy và phiên bản Ollama; các
câu trắc nghiệm số liệu lấy từ lần chạy của lời giải mẫu và hỏi theo khoảng.

## Tiêu chí đạt

- `make_registry`: đếm đúng với lọc một, hai hoặc không tham số, `count` là `int` Python, phần trăm làm tròn 1 chữ
  số, `whole` bằng 0 thì `ValueError`, `limit` mặc định 3.
- `execute_tool_call`: kết quả JSON giữ tiếng Việt; 8 kiểu lỗi đều trả chuỗi `ERROR: ` có nêu tên tool hợp lệ, giá
  trị sai hoặc tham số thiếu.
- `run_tool_loop` với `FakeLLM`: hai tool song song rồi một tool rồi câu trả lời cho đúng lịch sử, đúng `tool_call_id`;
  id thiếu thành `call_<bước>_<thứ tự>`; lỗi tool quay lại model và được đếm; arguments hỏng giữ nguyên văn; dừng
  đúng `max_steps` lần gọi; không sửa `messages` đầu vào.
- `prompted_chat`: system giao thức đứng đầu, chứa tên, mô tả và schema của mọi tool; lịch sử chỉ còn chuỗi; truyền
  `PROMPTED_SCHEMA`; câu trả lời không phải JSON object thành câu trả lời cuối; chạy được với `run_tool_loop`.
- Cell `explore` chạy hết với `qwen2.5:3b` và in bảng so hai cách.

## Gợi ý

### Gợi ý 1

`jsonschema.Draft202012Validator(schema).iter_errors(args)` cho từng lỗi kèm `.message` đọc được ("'phòng học' is not
one of [...]"): ghép chúng vào thông báo lỗi là đủ cho model sửa. Bọc lời gọi hàm trong `try/except Exception`: một
tool lỗi không được làm chết cả hội thoại.

### Gợi ý 2

Trong vòng lặp, thêm message assistant **đã có id** vào lịch sử trước, rồi mới thêm các message `tool`: model cần thấy
đúng cặp tool call và kết quả. Với `prompted_chat`, in ra `history` mà bạn gửi cho LLM ở lượt thứ hai của một câu hỏi
cần hai bước: nó phải đọc được như một cuộc hội thoại bình thường.
