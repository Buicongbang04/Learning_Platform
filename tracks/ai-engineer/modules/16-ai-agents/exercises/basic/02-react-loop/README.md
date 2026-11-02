---
title: Vòng ReAct tự viết - parser, ngân sách bước, điều kiện dừng, trace
level: basic
services: []
files:
  - path: starter/react.py
    note: clean_reply, parse_react, run_react TODO
  - path: tests/test_react.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/16-ai-agents/exercises/basic/02-react-loop -q
---

## Mục tiêu

Tự viết vòng lặp agent kiểu ReAct không framework: đọc output dạng `Thought / Action / Action Input / Final Answer`
của model (kể cả khi model viết sai), gọi tool, đưa kết quả hoặc lỗi trở lại, và dừng đúng lúc: có câu trả lời, hết
ngân sách bước, lỗi định dạng lặp lại, gọi đi gọi lại cùng một action, hoặc LLM lỗi. Mỗi bước được ghi lại (trace)
để sau này đo và debug. Bài Intermediate 02 chạy chính vòng này với `qwen2.5:3b` trên 24 task.

## Đề bài

**Phần cứng:** CPU · ~75 phút

Trong `starter/react.py` (dataclass `Action`, `Final`, `Step`, `RunResult`, `SYSTEM_TEMPLATE`, `render_tools` đã có):

1. `clean_reply(text)` và `parse_react(text) -> Action | Final` theo docstring: bỏ phần `Observation:` model tự bịa,
   từ khoá không phân biệt hoa thường, cái nào đứng trước thắng (Action hay Final Answer), tham số là JSON object
   đầu tiên sau `Action Input:` (có thể trong khối ```` ```json ````, có thể có chữ thừa phía sau). Lỗi thì
   `ReActParseError` với thông điệp đủ để model sửa (nhắc tới phần bị thiếu hoặc sai).
2. `run_react(llm, task, registry, *, max_steps=8, max_format_retries=2, max_repeats=2, system=None, history=None)`:
   - `messages` bắt đầu bằng system (`(system or SYSTEM_TEMPLATE).format(tools=render_tools(registry.specs()))`), rồi
     bản sao của `history`, rồi `{"role": "user", "content": task}`. Mỗi lần gọi `llm.chat(messages)` là một bước;
     tối đa `max_steps` bước, hết thì `stopped="max_steps"`, `answer=None`.
   - `llmkit.LLMError` khi gọi LLM: dừng ngay, `stopped="llm_error"`, `error` là thông điệp.
   - Lỗi định dạng: thêm message assistant (nguyên văn) và message user bắt đầu bằng `"Lỗi định dạng: "` kèm thông
     điệp của `ReActParseError`; `Step(kind="format_error")`, `format_errors += 1`. Lỗi định dạng **liên tiếp** vượt
     `max_format_retries` thì `stopped="format_error"`.
   - `Final`: thêm message assistant là `clean_reply(reply)`, `stopped="answer"`, `answer` là câu trả lời.
   - `Action`: nếu cùng tool, cùng tham số (so dict, không so chữ) với action **vừa thực thi** và chuỗi giống hệt đó đã
     được thực thi `max_repeats` lần liên tiếp thì không thực thi nữa, `Step(kind="repeat")`,
     `stopped="repeated_action"` (lượt lỗi định dạng ở giữa không làm đứt chuỗi). Ngược lại gọi
     `registry.call(tool, args)`, thêm message assistant `clean_reply(reply)` và message user
     `"Observation: <content>"`, `Step(kind="action", ...)` có observation và `ok`; observation lỗi thì
     `tool_errors += 1` (lỗi tool không làm dừng vòng lặp).
   - Mỗi `Step` có `index` (số bước, từ 0) và `seconds` (thời gian của bước đó).

`registry` chỉ cần có `specs()` và `call(name, args)` trả object có `.ok`, `.content`: `ToolRegistry` của bài 01,
`MCPToolbox` của bài Intermediate 01, hay registry giả trong test đều dùng được. Mục 2 lý thuyết có sơ đồ trạng thái
của vòng lặp.

## Tiêu chí đạt

- `parse_react`: 4 biến thể `Action Input` (khối code, chữ thừa phía sau, JSON nhiều dòng lồng nhau, từ khoá viết
  hoa thường lẫn lộn) đều đọc đúng; 7 kiểu output hỏng đều ném `ReActParseError` với thông điệp đúng chỗ.
- `run_react` với `FakeLLM`: lịch sử message đúng từng vai và nội dung (Observation bịa không lọt vào lịch sử); lỗi
  tool là observation cho lượt sau; lỗi định dạng được gửi lại và đếm **liên tiếp**; đúng `max_steps` lần gọi khi
  model không dừng; action lặp bị chặn trước khi thực thi lần thứ `max_repeats + 1` (so theo tham số, không theo chữ);
  `LLMError` dừng vòng lặp; `history` của người gọi không bị sửa.

## Gợi ý

### Gợi ý 1

Regex theo dòng với cờ `re.M | re.I` (`^\s*Action\s*:`) phân biệt được `Action:` với `Action Input:`. Để lấy JSON đầu
tiên mà bỏ qua chữ thừa phía sau, xem `json.JSONDecoder().raw_decode`. So hai action bằng
`json.dumps(args, sort_keys=True)` để thứ tự khoá không ảnh hưởng.

### Gợi ý 2

Viết vòng lặp như một máy trạng thái nhỏ: mỗi nhánh (lỗi LLM, lỗi định dạng, Final, lặp, Action) làm đúng ba việc:
cập nhật `messages`, thêm `Step`, quyết định dừng hay đi tiếp. Test kiểm `FakeLLM.calls[i]` (bản sao `messages` lúc
gọi lần `i`), nên thứ tự thêm message quan trọng. Khi debug, in `res.steps` ra xem trước khi đọc assert.
