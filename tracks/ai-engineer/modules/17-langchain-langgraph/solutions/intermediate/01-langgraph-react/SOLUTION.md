# Lời giải: agent ReAct bằng LangGraph

## Cách làm

**`make_tools`.** `[tool(fn, parse_docstring=True) for fn in functions]`. Không có `parse_docstring`, mô tả tool là cả
docstring (kể cả mục `Args:`) và tham số không có mô tả; với nó, mô tả tool là đoạn đầu, mô tả `currency` là "mã ngoại tệ",
`Literal["USD", "EUR", "JPY"]` thành `enum`. Đây đúng là việc bài Basic 01 module 16 tự làm trong khoảng 114 dòng.

**`format_tool_error`.** `f"ERROR: {type(exc).__name__}: {exc}"`, truyền cho `ToolNode(..., handle_tool_errors=...)`.
`ToolNode` gắn `status="error"` cho `ToolMessage` đó, và `to_steps` đọc `ok` từ `status` chứ không đoán từ chữ.

**`build_agent`.** Node `agent` gửi `[SystemMessage(system), *state["messages"]]` cho `llm.bind_tools(tools)` và chỉ trả
message mới: system prompt là cấu hình, không ghi vào state (đổi prompt không phải sửa mọi thread đã lưu, và checkpoint
không phình thêm một bản prompt mỗi lượt). `stopped` được quyết định ngay trong node: không có tool call là `"answer"`;
có tool call ở lượt thứ `max_steps` là `"max_steps"` (không chạy tool nữa); còn lại `""`. Hàm định tuyến chỉ đọc
`stopped`. Ngân sách nằm trong state, nên dừng là một kết quả bình thường có trace đầy đủ, không phải
`GraphRecursionError`.

**`run_task`.** `invoke` với `{"messages": [HumanMessage(q)], "llm_calls": 0, "stopped": ""}` và
`{"recursion_limit": recursion_limit}`. `recursion_limit` 50 rộng hơn ngân sách (8 lượt model là tối đa 16 superstep), nên
nó chỉ là lưới an toàn.

**`to_steps`.** Một dict `tool_call_id -> ToolMessage`, rồi duyệt các `AIMessage`: mỗi AIMessage một chỉ số, mỗi tool call
một bước. Đổi `content` sang `str` vì `ToolMessage.content` có thể là list khối nội dung.

## Kết quả thật

PC của track, 2026-11-01, Ollama 0.13.5, `qwen2.5:3b`, `temperature` 0, `seed` 0, GPU dùng chung với phiên khác, cùng
system prompt `NATIVE_SYSTEM`, tối đa 8 lượt gọi model. Hai dòng module 16 là **chạy lại cùng ngày** bằng đúng code lời giải
module 16 để so cùng điều kiện (log `.superpowers/scratch/logs/i01_eval.log`, `i01_eval2.log`, tổng hợp
`i01_summary.log`, `i01_details.log`):

| Cách | Đúng / 24 | Wilson 95% | Lượt model TB | Giây trung vị | Framework ms mỗi lượt (trung vị) | Kết thúc |
| --- | --- | --- | --- | --- | --- | --- |
| LangGraph dựng tay (native) | 11 | [0.28, 0.65] | 1.96 | 4.3 | 3.6 | 24 trả lời |
| `create_react_agent` + `handle_tool_errors` | 9 | [0.21, 0.57] | 2.00 | 3.4 | 5.1 | 24 trả lời |
| `create_react_agent` mặc định | 8 | [0.18, 0.53] | 1.71 | 3.3 | 5.6 | 17 trả lời, 7 exception |
| Module 16, ReAct văn bản tự viết | 18 | [0.55, 0.88] | 3.08 | 7.1 | 6.4 | 24 trả lời |
| Module 16, native tự viết | 10 | [0.24, 0.61] | 2.04 | 3.4 | 8.5 | 24 trả lời |

**Lần chạy thứ hai** (chính notebook lời giải qua `nbconvert`, cùng ngày, log
`.superpowers/scratch/logs/nb_i01_executed.ipynb`): dựng tay 10/24, prebuilt mặc định 9/24 (4 task kết thúc bằng
`ValueError`), prebuilt có xử lý lỗi 10/24, hai cách sau cùng giống hệt nhau theo từng task; thời gian framework 3.7 và 5.3
ms mỗi lượt. `temperature` 0 với `seed` cố định vẫn không cho kết quả y hệt giữa hai lần chạy trên GPU dùng chung (số
task đổi 1 tới 3, số task sập đổi từ 7 xuống 4): đọc các chênh lệch nhỏ như nhiễu.

Lần chạy tham chiếu, so theo cặp: dựng tay và prebuilt có xử lý lỗi lệch nhau ở 2 task (t01, t11, đều chỉ dựng tay đúng); dựng tay và native
tự viết lệch nhau ở 1 task (t11). Native tự viết và ReAct văn bản lệch nhau ở 8 task, cả 8 đều chỉ ReAct đúng.

Theo nhóm (dựng tay / ReAct văn bản): tra một lần 3/6 so với 6/6, tính toán 1/6 so với 3/6, đơn hàng 1/4 so với 2/4.

## Đọc kết quả

- **Framework không đổi giao thức.** Ba cách native (dựng tay, prebuilt, tự viết) nằm trong 8 tới 11 task, khoảng tin cậy
  chồng nhau gần hết và chỉ 1 tới 2 task lệch nhau theo cặp: cùng giao thức native cho cùng hành vi, dù vòng lặp viết bằng
  gì. Khoảng cách tới ReAct văn bản (18) là khoảng cách của **giao thức** trên model 3B này, đúng như module 16 đo; nó
  không biến mất khi đổi sang LangGraph. Nếu muốn ReAct văn bản trong LangGraph, đặt parser của module 16 vào node
  `agent` (model không `bind_tools`, node tự parse `Action`, gọi tool, ghi observation): đồ thị không quan tâm giao thức.
- **Kiểu hỏng giống module 16.** Với `classify_failure` của module 16, 13 task sai của agent dựng tay gồm 5 "số bịa",
  5 "sai khác", 2 "không gọi tool", 1 "lỗi tool"; 5 câu trả lời sai quay ra hỏi lại người dùng ("Bạn có thể cung cấp mã
  sách không?") thay vì gọi tool tiếp, như native của module 16.
- **Prebuilt mặc định sập 7/24 task** ở lần chạy tham chiếu (4/24 ở lần chạy notebook): 6 `ValueError` từ `get_book` khi model đoán mã sách ("DTNT", "S01") và 1
  `SyntaxError` từ `calculator`. `ToolNode` mặc định (`langgraph-prebuilt` 1.1.1) ném lại exception lúc tool chạy thay vì
  trả observation; module 16 coi "lỗi là observation" là nguyên tắc đầu tiên của tool registry. Truyền một `ToolNode` có
  `handle_tool_errors` cho `create_react_agent` là sửa được; đọc mặc định của prebuilt trước khi dùng.
- **Overhead.** Thời gian ngoài lượt gọi model là vài mili giây mỗi lượt cho mọi cách, so với khoảng 1.5 tới 2 giây một
  lượt `qwen2.5:3b`. Không có lý do hiệu năng để tránh LangGraph ở đây. ReAct văn bản chậm hơn theo giây vì nó gọi model
  nhiều lượt hơn (3.08 so với 1.96), không phải vì code.
- **Số dòng code** (đếm dòng không trống, không chú thích, bỏ docstring; log `loc_compare.log`): `make_tools`,
  `format_tool_error`, `AgentState`, `build_agent`, `run_task` là 34 dòng. Module 16 cần `tools.py` (registry sinh schema
  từ chữ ký hàm, kiểm tham số, 114 dòng) cộng vòng native (24 dòng). Cái LangGraph cho thêm mà không tốn dòng nào:
  streaming theo node và theo token, chỗ cắm checkpointer và `interrupt`, callback cho trace. Cái nó lấy đi: bạn phải
  biết mặc định của từng lớp (lỗi của `ToolNode`, `recursion_limit`, deprecation của prebuilt).
- **Streaming.** Cell cuối in từng bước của đồ thị (`updates`) và từng token (`messages`). Ở lần chạy notebook, với câu
  t02 token đầu tiên đến sau 1.43 s, cả câu 1.92 s: câu trả lời ngắn, nên phần lớn thời gian là lượt gọi tool và prefill,
  không phải sinh token; với câu trả lời dài, streaming mới đổi trải nghiệm rõ rệt.
- 24 task là ít: chênh 2 task giữa dựng tay và prebuilt (cùng giao thức, prompt hệ thống được chèn theo hai cách khác
  nhau) nằm trong nhiễu. Chạy lại với seed khác trước khi kết luận cách nào hơn.
