---
title: Dựng lại RAG bằng LangChain và so với SDK trực tiếp
level: advanced
services: []
files:
  - path: starter/frameworks.ipynb
    note: 3 hàm dán từ Intermediate 02, build_chain và retriever TODO
  - path: starter/COMPARE.md
    note: Báo cáo so sánh
  - path: tests/test_frameworks.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py zalo-legal
  - ollama pull qwen2.5:3b
  - ollama pull bge-m3
  - uv run jupyter lab tracks/ai-engineer/modules/13-rag/exercises/advanced/02-rag-frameworks/starter/frameworks.ipynb
  - uv run pytest tracks/ai-engineer/modules/13-rag/exercises/advanced/02-rag-frameworks -q
---

## Mục tiêu

Biết một framework RAG thật sự cho bạn gì và lấy đi gì, bằng số đo trên chính pipeline của bạn: dựng lại pipeline bài
Intermediate 02 bằng LangChain (LCEL, `langchain-ollama`), giữ **cùng prompt, cùng nguồn, cùng cổng từ chối**, rồi so
với bản SDK trực tiếp về số dòng code, độ trễ, chất lượng trên 50 câu và trải nghiệm debug.

## Đề bài

**Phần cứng:** GPU 4GB · ~180 phút

Thời gian trên là thời gian làm bài; phần chạy thật (khoảng 110 lượt gọi `qwen2.5:3b`) ước khoảng 10 phút trên laptop
GPU 4GB khi không chương trình nào khác dùng GPU (PC 12GB chạy nhanh hơn, có thể thử thêm `qwen2.5:7b`). Đừng chạy song
song việc khác dùng GPU: Ollama phải chia model giữa GPU và CPU, vừa chậm vừa làm câu trả lời đổi theo cách chia. Cần cache vector corpus của bài Intermediate 01
(`data/raw/zalo-legal/cache/bge-m3.npy`). Repo đã cài `langchain-core` và `langchain-ollama` (xem `pyproject.toml`).

1. Trong `starter/frameworks.ipynb`, cell chấm điểm:
   - Bản SDK: **dán** `build_messages`, `parse_citations`, `answer` của bạn ở bài Intermediate 02 (giữ chữ ký).
   - Bản LangChain: `build_chain(retriever, llm, min_score=0.5) -> Runnable`. `retriever` là `Runnable` nhận câu hỏi trả
     `list[Document]` (metadata `uid`, `title`, `score`), `llm` là chat model của LangChain. `chain.invoke(question)`
     trả `RagAnswer` giống hệt `answer(...)` của bản SDK khi model trả cùng văn bản: cổng điểm trước model (không gọi
     model), prompt bằng hệt `build_messages` (hai message `system`, `human`), trích dẫn map về `uid`, cờ từ chối.
     Dựng bằng LCEL; được dùng lại `build_messages`, `parse_citations`, **không** gọi `answer` bên trong chain.
2. Cell `explore`:
   - viết `DenseKhoanRetriever` (một `BaseRetriever` dùng `OllamaEmbeddings`) làm đúng việc của retrieve hai tầng, kiểm
     nó trả cùng nguồn với bản SDK;
   - chạy 50 câu đầu tập ghim qua cả hai bản với **cùng nguồn**, xen kẽ thứ tự gọi, bằng `ChatOllama(temperature=0)`
     và client của `llmkit`; so độ trễ phần sinh, số câu trả lời giống hệt, số câu có trích dẫn, trích đúng điều, từ chối;
   - gọi lại bản SDK trên 10 câu để biết chính nó tự lệch bao nhiêu trước khi đổ chênh lệch cho framework;
   - đo chi phí riêng của framework bằng LLM giả, đếm số dòng code, bật `set_debug(True)` xem LangChain gửi gì cho model.
3. Viết `starter/COMPARE.md` theo khung có sẵn, rồi làm phần trắc nghiệm của bài trong app.

**Một `COMPARE.md` tốt**:

- So **công bằng** và nói rõ đã làm gì để công bằng: cùng nguồn (retrieve một lần, đưa cho cả hai), cùng prompt (test
  đã ép), cùng model và `temperature`, xen kẽ thứ tự gọi. Thiếu một điều, chênh lệch đo được có thể đến từ chỗ khác.
- Tách **chi phí của framework** (mili giây, đo bằng LLM giả) khỏi **thời gian model** (giây). Trộn hai thứ thì kết luận
  "framework chậm" hay "framework nhanh" đều sai.
- Số dòng code đi kèm câu hỏi đúng: bản nào dễ đọc, dễ sửa, dễ lần lỗi hơn với **bạn** và đồng đội; LangChain thêm bao
  nhiêu gói phụ thuộc.
- Khuyến nghị có điều kiện: cho pipeline này, và khi nào đổi (nhiều tool, agent, streaming, cần LangSmith, module 17).

## Tiêu chí đạt

- Bản SDK dán lại qua kiểm tra nhanh (trích dẫn, cổng, map uid) với `FakeLLM`.
- `build_chain` chạy với `FakeListChatModel`: trả `RagAnswer`, trích dẫn `[7]` bị bỏ, hai khoản cùng điều chỉ cho một
  uid, retriever và model đều được gọi đúng một lần.
- Model nhận đúng hai message, nội dung bằng hệt `build_messages`.
- Mọi điểm dưới `min_score` hoặc không có nguồn: model không được gọi, kết quả `RagAnswer(REFUSAL, [], True)`; model
  trả câu từ chối thì `refused=True`.
- Với ba kiểu câu trả lời (có trích dẫn trùng, trích dẫn tự do không `[i]`, từ chối kèm trích dẫn), chain và `answer`
  của bản SDK cho cùng `RagAnswer`.
- `COMPARE.md` không còn TODO, ít nhất 400 từ, có bảng.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Một dict trong LCEL là chạy song song các nhánh: `{"question": RunnablePassthrough(), "docs": retriever}` biến câu hỏi
thành `{"question": ..., "docs": [...]}`. `RunnablePassthrough.assign(text=...)` thêm một khoá mà giữ các khoá cũ. Chat
model của LangChain nhận được list `(role, content)` như `("system", "...")`, `("human", "...")`; `StrOutputParser()`
lấy chuỗi từ message trả về.

### Gợi ý 2

Cổng từ chối là một nhánh: `RunnableBranch((điều_kiện, nhánh_sinh), nhánh_từ_chối)`, hoặc một `RunnableLambda` trả
về chính runnable cần chạy tiếp. Kiểm cổng **trước** khi dựng prompt để model không bị gọi. Bước cuối là một hàm nhận
`{"question", "docs", "text"}` trả `RagAnswer`: dùng lại `parse_citations` rồi map `[i]` về `docs[i - 1].metadata["uid"]`.
