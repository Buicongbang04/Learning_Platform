---
title: Multi-agent - một agent, supervisor, swarm trên trợ lý nhà sách luật (portfolio)
level: advanced
services: []
files:
  - path: starter/handoff.py
    note: make_handoff_tool (có test)
  - path: starter/multi_agent.ipynb
    note: Notebook làm việc
  - path: starter/REPORT.md
    note: Báo cáo của bạn
  - path: tests/test_handoff.py
    note: Không sửa
run:
  - ollama pull qwen2.5:3b
  - ollama pull bge-m3
  - uv run pytest tracks/ai-engineer/modules/17-langchain-langgraph/exercises/advanced/01-multi-agent -q
  - uv run jupyter lab tracks/ai-engineer/modules/17-langchain-langgraph/exercises/advanced/01-multi-agent/starter/multi_agent.ipynb
---

## Mục tiêu

Đo, thay vì tin, câu hỏi "chia cho nhiều agent có tốt hơn một agent không". Bạn dựng một trợ lý nhà sách luật theo ba
kiến trúc trên cùng model và cùng tool: **một agent** cầm mọi tool, **supervisor** giao việc cho hai agent chuyên trách
(nhà sách, pháp luật), và **swarm** trong đó các agent tự chuyển quyền cho nhau bằng handoff. Rồi chấm cả ba trên cùng bộ
task bằng bộ chấm không dùng LLM, đếm cái giá (lượt LLM, token, giây), và đọc trace để biết mỗi kiến trúc hỏng ở đâu. Đây
là bài portfolio: một bảng trung thực kèm phân tích lỗi đáng giá hơn một sơ đồ kiến trúc đẹp.

## Đề bài

**Phần cứng:** CPU · ~300 phút

Thời gian trên là thời gian làm bài. Chạy cả ba kiến trúc trên 52 task với `qwen2.5:3b` mất khoảng 25 phút trên PC của
track (GPU dùng chung); laptop GPU 4GB chậm hơn, nên chạy thử trên 10 task trước. `qwen2.5:7b` chỉ chạy trên PC 12GB,
không bắt buộc.

1. **`starter/handoff.py`**: viết `make_handoff_tool(agent_name, description)` theo docstring (có test). Đây là cách
   một agent trong swarm chuyển quyền cho agent khác: tool trả `Command(goto=..., graph=Command.PARENT, update=...)`.
2. **Tool và bộ task** (trong `starter/multi_agent.ipynb`):
   - Tool nhà sách: 5 tool của `bookstore.py` (bài Intermediate 01). Tool pháp luật: `search_law(query)` trả 3 điều
     luật (mã, tiêu đề, 600 ký tự đầu) từ `LegalIndex` (bài Intermediate 03), và ghi lại các uid đã trả.
   - 52 task: 24 task của `bookstore.TASKS`; 20 câu đầu của tập ghim Zalo (`load_questions(root, 300)[:20]`); 8 câu
     ghép `f"{câu hỏi task j của bookstore} Ngoài ra cho tôi hỏi: {câu pháp luật 20 + j}"` với `j = 0..7`.
   - Chấm: task nhà sách đúng khi `check_answer` của module 16 đúng; task pháp luật đúng khi có câu trả lời và điều
     đúng (qrels) nằm trong các uid `search_law` đã trả trong lần chạy đó; câu ghép đúng khi cả hai phần đúng.
3. **Ba kiến trúc**, cùng `qwen2.5:3b`, `temperature` 0, có ngân sách bước cho **mỗi** agent:
   - một agent cầm cả 6 tool;
   - supervisor: một agent điều phối có hai tool `ask_bookstore(request)`, `ask_legal(request)`, mỗi tool chạy một
     agent con (agent làm tool), rồi tổng hợp; hoặc một biến thể supervisor bạn chọn và giải thích;
   - swarm: agent nhà sách và agent pháp luật là hai subgraph, mỗi agent có tool của mình cộng một tool handoff sang
     agent kia; lượt đầu bắt đầu ở agent nhà sách.
4. **Đo**: tỉ lệ đúng (tổng và theo nhóm) kèm khoảng tin cậy Wilson, so theo cặp, lượt LLM và token prompt mỗi task
   (callback đếm cả lời gọi của agent con: truyền `callbacks` của tool xuống agent con), giây mỗi task.
5. **`REPORT.md`**: bảng, ít nhất 5 trace lỗi có phân loại, kết luận.

## Tiêu chí đạt

- Test của `make_handoff_tool` xanh (`uv run pytest ... -q`; `SOLUTION=1` thì bỏ qua vì bài này không có lời giải code).
- Ba kiến trúc chạy trên đúng 52 task đã ghim với cùng model và cùng bộ chấm; kết quả lưu ra tệp, bảng tái tạo được.
- Đếm chi phí đầy đủ: lượt LLM của agent con được tính vào task cha.
- Phân tích lỗi dựa trên trace (giao sai người, mất thông tin khi chuyển giao, agent con trả lời chung chung, supervisor
  tự bịa thay vì giao việc...), có đếm.
- Kết luận trung thực, gắn với số: "multi-agent không đáng trên bộ này" là kết luận tốt nếu số nói vậy.

## Gợi ý

### Gợi ý 1

Một tool LangChain nhận được `RunnableConfig` nếu có tham số kiểu `RunnableConfig`; dùng nó để truyền `callbacks`
xuống agent con, nếu không callback đếm token của bạn sẽ không thấy các lời gọi bên trong. Với swarm, đồ thị cha cần
`destinations` khi `add_node` vì node chuyển hướng bằng `Command`, và một khoá `active_agent` để lượt sau bắt đầu ở agent
đang giữ quyền.

### Gợi ý 2

Đọc trace câu ghép trước tiên: đó là nơi ba kiến trúc khác nhau rõ nhất. Đếm số lần agent nhà sách trả lời câu pháp luật
mà không chuyển giao, và số lần supervisor tự trả lời thay vì gọi agent con. Mục 6 lý thuyết có bảng đánh đổi để bạn
đối chiếu.
