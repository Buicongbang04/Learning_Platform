---
title: Corrective RAG - chấm nguồn, viết lại truy vấn, tra lại, và đo bộ chấm với qrels (portfolio)
level: advanced
services: []
files:
  - path: starter/crag.py
    note: decide_next, grader_agreement (có test)
  - path: starter/crag.ipynb
    note: Notebook làm việc
  - path: starter/REPORT.md
    note: Báo cáo của bạn
  - path: tests/test_crag.py
    note: Không sửa
run:
  - ollama pull qwen2.5:3b
  - ollama pull bge-m3
  - uv run pytest tracks/ai-engineer/modules/17-langchain-langgraph/exercises/advanced/02-corrective-rag -q
  - uv run jupyter lab tracks/ai-engineer/modules/17-langchain-langgraph/exercises/advanced/02-corrective-rag/starter/crag.ipynb
---

## Mục tiêu

Module 13 kết thúc bằng danh sách "RAG nâng cao" và hẹn "agentic RAG với LangGraph ở module 17". Bài này dựng một biến
thể cụ thể, **Corrective RAG** (Yan et al., 2024, rút gọn): sau khi tìm, một LLM chấm từng nguồn có liên quan không;
không còn nguồn nào thì viết lại truy vấn và tìm lại, tối đa vài lần; cuối cùng trả lời từ các nguồn được giữ, hoặc từ
chối. Rồi đo nó với RAG một lượt trên cùng 100 câu bằng bộ chấm không dùng LLM, và đo luôn **bộ chấm LLM** so với qrels:
một bước "tự sửa" chỉ tốt bằng bộ chấm của nó.

## Đề bài

**Phần cứng:** CPU · ~240 phút

Thời gian trên là thời gian làm bài. Một lần chạy 100 câu với `qwen2.5:3b` mất khoảng 10 đến 15 phút trên PC của track
(GPU dùng chung) cho mỗi biến thể; laptop GPU 4GB chậm hơn, nên chạy thử 20 câu trước.

1. **`starter/crag.py`**: `decide_next(relevant, rewrites, max_rewrites)` và `grader_agreement(rounds)` theo docstring
   (có test).
2. **Đồ thị CRAG** (trong `starter/crag.ipynb`), dùng lại `LegalIndex`, `build_answer_messages`, `parse_citations` của
   bài Intermediate 03: `retrieve` (dense top-5) -> `grade` (một lượt LLM, structured output: số thứ tự các nguồn liên
   quan) -> `decide_next` -> `rewrite` (LLM viết lại truy vấn bằng thuật ngữ văn bản luật) quay lại `retrieve`, hoặc
   `answer` (chỉ với các nguồn được giữ), hoặc `refuse` (câu từ chối, không gọi LLM). Ghi mọi lượt chấm vào state bằng
   reducer để đo bộ chấm.
3. **So sánh** trên câu 0-99 của tập ghim: RAG một lượt (top-5, như bài Intermediate 03) và ít nhất hai biến thể CRAG
   (ví dụ `max_rewrites` 0 và 1; hoặc chấm trên 700 ký tự đầu của điều so với cả điều). Thước đo: nguồn trúng, trích
   trúng, từ chối, lượt LLM, giây trung vị; `grader_agreement` cho mỗi biến thể.
4. **`REPORT.md`**: bảng, ví dụ cụ thể bộ chấm bỏ điều đúng, kết luận cho capstone.

## Tiêu chí đạt

- Test của `crag.py` xanh (`SOLUTION=1` thì bỏ qua vì bài này không có lời giải code).
- RAG một lượt và hai biến thể CRAG chạy trên đúng 100 câu đã ghim, cùng model, cùng chỉ mục; kết quả lưu ra tệp.
- Có đo bộ chấm với qrels (precision, recall, tỉ lệ giữ được điều đúng khi nó có mặt), không chỉ đo đầu ra cuối.
- Đọc và giải thích ít nhất 5 câu mà CRAG tệ hơn RAG một lượt.
- Kết luận trung thực, gắn với số và với chi phí.

## Gợi ý

### Gợi ý 1

Điều đúng chỉ được trích nếu nó qua được bộ chấm. Trước khi chạy cả bộ, tính trên 20 câu: trong các câu mà điều đúng
có trong top-5, bộ chấm giữ lại nó bao nhiêu lần? Con số đó là trần của "trích trúng" cho CRAG.

### Gợi ý 2

Structured output cho bộ chấm có thể chỉ là một list số nguyên; nhớ lọc số ngoài `1..k`, và quyết định trước làm gì khi
bộ chấm lỗi (giữ hết hay bỏ hết các nguồn) vì lựa chọn đó đổi kết quả. Câu từ chối không gọi LLM nên rẻ; đếm riêng số câu
bị từ chối mà điều đúng có trong top-5 ban đầu.
