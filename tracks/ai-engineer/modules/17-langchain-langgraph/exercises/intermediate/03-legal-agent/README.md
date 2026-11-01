---
title: Agent pháp luật bằng LangGraph - lập kế hoạch, hỏi lại khi thiếu thông tin, tra song song, đo với RAG một lượt
level: intermediate
services: []
files:
  - path: starter/legal_agent.ipynb
    note: dán reducer bài Basic 02, 12 hàm TODO
  - path: starter/legal_index.py
    note: Chỉ mục Zalo Legal dùng cache bge-m3 của module 13 (không sửa)
  - path: tests/test_legal_agent.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py zalo-legal
  - ollama pull qwen2.5:3b
  - ollama pull bge-m3
  - uv run jupyter lab tracks/ai-engineer/modules/17-langchain-langgraph/exercises/intermediate/03-legal-agent/starter/legal_agent.ipynb
  - uv run pytest tracks/ai-engineer/modules/17-langchain-langgraph/exercises/intermediate/03-legal-agent -q
---

## Mục tiêu

Dựng bản thu nhỏ của agent capstone milestone 6 trên Zalo Legal: lập kế hoạch bằng structured output (tách câu hỏi nhiều
vế, nhận ra câu hỏi mức phạt giao thông không nói loại xe), **hỏi lại** bằng `interrupt`, tra từng vế **song song** bằng
`Send` với reducer gộp evidence, trả lời có trích dẫn, state trong SQLite. Rồi đo nó với RAG một lượt kiểu module 13 bằng
bộ chấm không dùng LLM trên ba bộ câu hỏi, để biết agent đáng tiền ở đâu và không ở đâu.

## Đề bài

**Phần cứng:** CPU · ~120 phút

Thời gian trên là thời gian làm bài. Cần Zalo Legal và cache vector `bge-m3` của bài Intermediate 01 module 13
(`data/raw/zalo-legal/cache/bge-m3.npy`; chưa có thì chạy notebook bài đó trước, khoảng 45 phút trên laptop GPU 4GB). Các
cell `explore` gọi model khoảng 510 lượt, chạy khoảng 25 đến 40 phút trên PC của track (GPU dùng chung); laptop GPU
4GB chậm hơn, nên chạy thử S3 và 20 câu S1 trước.

Trong `starter/legal_agent.ipynb` (`Plan`, các prompt, `LegalState` đã có; mỗi hàm có đặc tả ở mục tương ứng):

1. Dán `merge_evidence` của bài Basic 02.
2. Các hàm nhỏ: `ask_text`, `search_query`, `select_sources`, `build_answer_messages`, `parse_citations`.
3. Các node: `make_planner`, `route_after_plan`, `clarify`, `make_retriever`, `make_answerer`.
4. `build_legal_agent`, `run_question`.

Rồi chạy các cell `explore` theo thứ tự: S3 (câu thiếu loại xe), S1 (100 câu thường), S2 (50 câu hai vế), và một cell
dừng ở câu hỏi lại, mở kết nối SQLite mới như sau khi khởi động lại, rồi đi tiếp. Sau đó làm phần trắc nghiệm của bài
trong app. Câu trả lời của model có thể lệch giữa các máy và phiên bản Ollama; câu trắc nghiệm số liệu hỏi theo khoảng
hoặc theo so sánh.

## Tiêu chí đạt

- Hàm nhỏ: câu hỏi lại đúng dạng; truy vấn ghép thông tin bổ sung đúng quy tắc; mỗi vế có chỗ riêng trong nguồn, uid đã
  chọn không chiếm chỗ vế sau; prompt trả lời đúng định dạng, cắt nguồn ở `SOURCE_CHARS`; trích dẫn ngoài khoảng bị bỏ.
- `make_planner`: gửi đúng prompt, dùng `json_schema`; "thiếu loại xe" do **code** suy ra từ `traffic_fine` và `vehicle`;
  model lỗi, trả chữ thường hay output sai schema không làm sập đồ thị.
- Đồ thị: câu hai vế tra mỗi vế đúng một lần và trích đúng điều cho từng vế; câu thiếu loại xe dừng hỏi **trước khi tra**,
  hỏi đúng một lần, không lập kế hoạch lại, tra bằng truy vấn đã ghép câu trả lời; không có nguồn thì từ chối không gọi
  LLM; thread độc lập.
- Các cell `explore` chạy hết.

## Gợi ý

### Gợi ý 1

Hai node định tuyến dùng chung một hàm: `add_conditional_edges("plan", route_after_plan, ["clarify", "retrieve"])` và
tương tự cho `"clarify"`; khi `asked` đã là 1, hàm đó trả list `Send`. `make_retriever` nhận `PartState` (input riêng của
`Send`), nhưng gắn `part` **gốc** vào evidence để `select_sources` tìm lại được. `run_question` đọc
`app.get_state(config).interrupts` sau mỗi `invoke`.

### Gợi ý 2

Fake model trong test trả `AIMessage` có tool call tên `Plan` và ghi lại `method` bạn truyền cho
`with_structured_output`. Với `select_sources`, sắp theo `(-score, uid)` trong từng vế rồi mới bỏ uid đã chọn và cắt
`per_part`. Khi đọc bảng S1, chú ý cột `agent_so_ve` và `agent_hoi`: câu bị tách hay bị hỏi thừa là chỗ agent khác RAG.
