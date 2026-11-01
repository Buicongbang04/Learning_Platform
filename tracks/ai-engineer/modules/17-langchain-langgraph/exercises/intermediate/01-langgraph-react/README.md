---
title: Agent ReAct bằng LangGraph - dựng tay, prebuilt, và so với vòng lặp tự viết trên 24 task
level: intermediate
services: []
files:
  - path: starter/react_graph.ipynb
    note: dán bộ chấm module 16, 6 hàm TODO
  - path: starter/bookstore.py
    note: Môi trường hiệu sách của module 16 (không sửa)
  - path: tests/test_react_graph.py
    note: Không sửa
run:
  - ollama pull qwen2.5:3b
  - uv run jupyter lab tracks/ai-engineer/modules/17-langchain-langgraph/exercises/intermediate/01-langgraph-react/starter/react_graph.ipynb
  - uv run pytest tracks/ai-engineer/modules/17-langchain-langgraph/exercises/intermediate/01-langgraph-react -q
---

## Mục tiêu

Dựng lại agent của module 16 bằng LangGraph và đo nó trên **cùng** 24 task hiệu sách, cùng model, cùng cách chấm: tool
sinh từ hàm Python bằng `@tool`, vòng `agent -> tools -> agent` bằng `StateGraph` có ngân sách bước trong state,
`ToolNode` với xử lý lỗi, trace đổi về dạng của module 16, rồi so với agent prebuilt `create_react_agent`. Bạn sẽ biết
framework đổi được gì (số dòng code, streaming, chỗ cắm checkpoint) và không đổi được gì.

## Đề bài

**Phần cứng:** CPU · ~75 phút

Thời gian trên là thời gian làm bài. Các cell `explore` gọi model khoảng 140 lượt, chạy khoảng 4 đến 8 phút trên PC của track
(`qwen2.5:3b` trên GPU dùng chung); laptop GPU 4GB chậm hơn, CPU thuần chậm hơn nhiều.

Trong `starter/react_graph.ipynb`:

1. Dán `numbers_in`, `check_answer`, `wilson_interval`, `discordant` từ lời giải bài Intermediate 02 module 16 (không
   chấm, nhưng các cell `explore` cần chúng để chấm giống hệt module 16).
2. `make_tools(functions)`, `format_tool_error(exc)`.
3. `build_agent(llm, tools, *, system, max_steps)`, `run_task(app, question, *, recursion_limit)`.
4. `to_steps(messages)`: lịch sử message thành các bước kiểu module 16.

Rồi chạy các cell `explore`: agent dựng tay trên 24 task, agent prebuilt (mặc định và có xử lý lỗi tool), bảng có khoảng
tin cậy và so theo cặp, thời gian framework mỗi lượt gọi model, và streaming theo node và theo token. Sau đó làm phần
trắc nghiệm của bài trong app. Câu trả lời của model có thể lệch giữa các máy và phiên bản Ollama; các câu trắc nghiệm số
liệu hỏi theo khoảng.

## Tiêu chí đạt

- `make_tools`: đúng tên, thứ tự, mô tả hàm không còn mục `Args:`, mô tả tham số lấy từ docstring, `Literal` thành `enum`.
- `format_tool_error` đúng định dạng `ERROR: <TênLỗi>: <thông điệp>`.
- `build_agent` với fake chat model: system prompt gửi ở mọi lượt nhưng không nằm trong state; lỗi tool thành observation
  có `status` lỗi và agent đi tiếp; dừng đúng sau `max_steps` lượt gọi model (lượt cuối không chạy tool); trả lời ở lượt
  cuối được phép vẫn là `"answer"`; nhiều tool call trong một lượt đều được chạy.
- `run_task` truyền `recursion_limit` vào config.
- `to_steps`: đúng số bước và chỉ số, `ok` đọc từ `status` của `ToolMessage`, tool call chưa có trả lời thì `None`.
- Các cell `explore` chạy hết với `qwen2.5:3b`.

## Gợi ý

### Gợi ý 1

`tool(fn, parse_docstring=True)` đọc docstring kiểu Google. `ToolNode` nhận `handle_tool_errors` là `True`, một chuỗi, hay
một hàm `exception -> str`. `AgentState` kế thừa `MessagesState`, nên khoá `messages` đã có reducer `add_messages`; node
`agent` chỉ cần trả message **mới**.

### Gợi ý 2

Quyết định `stopped` ngay trong node `agent` (sau khi biết lượt này là lượt thứ mấy và model có gọi tool không), để hàm
định tuyến chỉ đọc một khoá. Với `to_steps`, dựng trước một dict `tool_call_id -> ToolMessage`; `ToolMessage.content` có
thể là list khối nội dung, nên đổi sang `str`.
