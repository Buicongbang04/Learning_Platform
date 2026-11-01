---
title: LCEL - chuỗi phân tích câu hỏi pháp luật có structured output, retry, fallback và batch
level: basic
services: []
files:
  - path: starter/lcel.py
    note: 6 TODO
  - path: tests/test_lcel.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/17-langchain-langgraph/exercises/basic/01-lcel -q
---

## Mục tiêu

Viết bước đầu tiên của agent pháp luật trong capstone (milestone 6) bằng LCEL: phân tích câu hỏi thành các câu hỏi
con và thông tin còn thiếu, có structured output, retry đúng loại lỗi, fallback không cần LLM, tra các phần song song,
chạy cả lô mà một câu lỗi không kéo câu khác, và đếm lời gọi model bằng callback. Test dùng fake chat model của
LangChain, không cần Ollama.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Trong `starter/lcel.py` (`QuestionAnalysis`, `SYSTEM`, `PROMPT`, `TRANSIENT` đã có), viết theo docstring:

1. `build_analyzer(llm, *, attempts=3)`: `PROMPT` nối với `llm.with_structured_output(QuestionAnalysis)`. Khi model
   trả chữ thường thay vì gọi tool, structured output **không ném lỗi** mà trả `None`: biến trường hợp đó thành
   `OutputParserException`. Chỉ thử lại với lỗi trong `TRANSIENT` (mất kết nối, quá thời gian), tổng tối đa
   `attempts` lần, không chờ giữa các lần.
2. `naive_analysis(question)`: phân tích không cần LLM, tách theo `?` và `;`.
3. `with_backup(analyzer)`: analyzer lỗi bất kỳ (kể cả sau khi đã hết lượt thử lại) thì dùng `naive_analysis`.
4. `build_pipeline(analyzer, search)`: thêm khoá `analysis` và `evidence` vào dict đầu vào, giữ mọi khoá cũ; các phần
   được tra **song song**.
5. `analyze_many(chain, questions, *, max_concurrency=4)`: chạy cả lô, giới hạn số lời gọi cùng lúc, trả kết quả theo
   đúng thứ tự và lỗi theo vị trí.
6. `CallCounter`: callback đếm số lần gọi chat model và số lần lỗi.

Mục 1 lý thuyết có bảng các khối `Runnable` và ngữ nghĩa của `|`, `RunnableParallel`, `RunnablePassthrough.assign`,
`batch`, `with_retry`, `with_fallbacks`. Muốn chạy với model thật, thử trong một ô Python:
`build_analyzer(ChatOllama(model="qwen2.5:3b", temperature=0))` (cần `ollama pull qwen2.5:3b`).

## Tiêu chí đạt

- `build_analyzer` gửi đúng system và câu hỏi, trả `QuestionAnalysis`; thử lại lỗi tạm thời đúng số lần, **không** thử
  lại output sai schema; chữ thường thành `OutputParserException`.
- `with_backup` dùng phân tích không LLM cho cả ba kiểu output hỏng (chữ thường, sai schema, gọi tool lạ) và khi hết
  lượt thử lại; không gọi backup khi analyzer chạy được.
- `build_pipeline` giữ khoá đầu vào, `evidence` đúng thứ tự, mỗi phần tra một lần, các phần chạy đồng thời.
- `analyze_many` giữ thứ tự, lỗi đúng vị trí kể cả khi chain có `with_retry`, số lời gọi đồng thời không vượt giới hạn.
- `CallCounter` đếm cả lần thử lại.

## Gợi ý

### Gợi ý 1

Mọi bước là một `Runnable`: hàm thường thành `Runnable` bằng `RunnableLambda`. `RunnablePassthrough.assign(k=r)` chạy
`r` trên **cả dict đầu vào** và thêm kết quả vào khoá `k`. `with_retry` có tham số `retry_if_exception_type`,
`stop_after_attempt`, `wait_exponential_jitter`. Callback nhận `on_chat_model_start` và `on_llm_error` (chat model báo
lỗi qua tên `llm`).

### Gợi ý 2

Song song trong LCEL là `batch` (thread pool) hoặc `RunnableParallel`. Với `analyze_many`, đọc kỹ test có
`attempts=2`: `batch(..., return_exceptions=True)` của một chain bọc `with_retry` trong `langchain-core` 1.6.12 có lỗi
xếp nhầm kết quả khi lượt thử cuối có cả câu thành công lẫn câu lỗi (mục 1 lý thuyết). Cách an toàn là để mỗi phần tử
tự bắt lỗi của chính nó rồi mới `batch`.
