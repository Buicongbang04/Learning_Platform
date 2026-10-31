---
title: Một hội thoại, ba phương ngữ Chat API (OpenAI, Anthropic, Ollama)
level: basic
services: []
files:
  - path: starter/payloads.py
    note: 4 hàm TODO
  - path: tests/test_payloads.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/11-llm-apis-prompting/exercises/basic/01-chat-payloads -q
---

## Mục tiêu

Hiểu đến từng khoá JSON một hội thoại có gọi tool đi qua ba API phổ biến như thế nào, bằng cách tự viết lớp chuyển
đổi mà mọi gateway (LiteLLM, OmniRoute, `llmkit` của track) đều phải có. Sau bài này bạn đọc được response thô của
bất kỳ nhà cung cấp nào và biết chỗ nào hay vỡ khi đổi nhà cung cấp.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Dạng chuẩn của bài là message kiểu **OpenAI Chat Completions** (mục 1 lý thuyết): `system`, `user`, `assistant`
(có thể có `tool_calls`, mỗi call có `id`, `function.name`, `function.arguments` là **chuỗi** JSON) và `tool`
(`tool_call_id`, `content`). Trong `starter/payloads.py`, chỉ dùng thư viện chuẩn:

1. `to_anthropic(messages, tools=None, *, model, max_tokens=1024) -> dict`: body cho `POST /v1/messages` của Anthropic.
   Docstring liệt kê đủ quy tắc; ba điểm khác biệt chính so với OpenAI:
   - system là **khoá cấp ngoài**, không phải một message;
   - tool call là khối `tool_use` có `input` là **dict**, nằm trong `content` của assistant;
   - kết quả tool là khối `tool_result` nằm trong message **user**, và mọi kết quả của một lượt gọi song song phải
     nằm trong **một** message user.
2. `parse_openai(resp) -> Reply`, `parse_anthropic(resp) -> Reply`, `parse_ollama(resp) -> Reply`: đưa response
   thô về dataclass `Reply` chung (`text`, `tool_calls`, `finish_reason` theo từ vựng OpenAI `stop` / `length` /
   `tool_calls`, `prompt_tokens`, `completion_tokens`).

Bảng đối chiếu tối thiểu (đủ để làm bài; đọc thêm ở mục 1 và 6 lý thuyết):

| | OpenAI Chat Completions | Anthropic Messages | Ollama `/api/chat` |
| --- | --- | --- | --- |
| Text trả về | `choices[0].message.content` (có thể `null`) | các khối `{"type": "text"}` trong `content` | `message.content` |
| Tool call | `message.tool_calls[i]`: `id`, `function.name`, `function.arguments` (chuỗi JSON) | khối `{"type": "tool_use", "id", "name", "input"}` (`input` là object) | `message.tool_calls[i].function`: `name`, `arguments` (object), thường không có `id` |
| Lý do dừng | `finish_reason`: `stop`, `length`, `tool_calls` | `stop_reason`: `end_turn`, `stop_sequence`, `max_tokens`, `tool_use` | `done_reason`: `stop`, `length` |
| Token | `usage.prompt_tokens`, `usage.completion_tokens` | `usage.input_tokens`, `usage.output_tokens` | `prompt_eval_count`, `eval_count` |

Arguments không parse được thành JSON object (chuỗi hỏng, hoặc JSON hợp lệ nhưng là list) thì ném `ValueError`: model
nhỏ thỉnh thoảng sinh JSON hỏng, và lỗi phải lộ ra ở lớp này chứ không phải sâu trong code gọi tool.

## Tiêu chí đạt

- `to_anthropic`: system thành khoá ngoài (nhiều system nối bằng `"\n\n"`); chỉ còn role `user`/`assistant`; tool
  call thành `tool_use` với `input` dict (nhận cả chuỗi JSON lẫn dict); hai `tool` liên tiếp gom vào một message user;
  tools đổi sang `input_schema`; không thêm khoá `system`/`tools` khi không có; không sửa input.
- `ValueError` khi arguments hỏng hoặc không phải object, hoặc `tool_call_id` không có tool call tương ứng.
- Ba hàm `parse_*` cho cùng một `Reply` cho cùng một ý: text nối đủ khối, tool call đúng thứ tự, `finish_reason` đã
  quy đổi (Ollama gọi tool thì là `tool_calls` dù `done_reason` là `stop`), số token đúng trường.
- Reply parse từ OpenAI đưa ngược lại được vào lịch sử rồi chuyển sang Anthropic (test round-trip).

## Gợi ý

### Gợi ý 1

Viết một hàm phụ nhận `arguments` (chuỗi hoặc dict) và trả dict hoặc ném `ValueError`; cả `to_anthropic` lẫn ba hàm
parse đều dùng nó. Khi duyệt `messages`, giữ một tập các `id` tool call đã gặp để kiểm `tool_call_id`.

### Gợi ý 2

Để gom kết quả tool, nhìn message cuối cùng đã đưa vào danh sách output: nếu nó là message user mà content là danh
sách khối (tức là đang chứa `tool_result`), thêm khối mới vào đó thay vì tạo message mới. Với Anthropic, ánh xạ
`stop_reason` bằng một dict nhỏ; với Ollama, có tool call hay không quan trọng hơn `done_reason`.
