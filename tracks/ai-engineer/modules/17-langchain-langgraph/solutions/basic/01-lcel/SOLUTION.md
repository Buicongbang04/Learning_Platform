# Lời giải: LCEL phân tích câu hỏi pháp luật

## Cách làm

**`build_analyzer`.** `PROMPT | llm.with_structured_output(QuestionAnalysis) | RunnableLambda(_require)`, rồi
`.with_retry(retry_if_exception_type=TRANSIENT, stop_after_attempt=attempts, wait_exponential_jitter=False)`.

- `with_structured_output` mặc định của `BaseChatModel` gọi `bind_tools([QuestionAnalysis], tool_choice=...)` rồi đọc
  tool call đầu tiên bằng `PydanticToolsParser`. Ba cách hỏng của nó **không giống nhau**: tham số sai schema ném
  `ValidationError`, tool lạ ném `OutputParserException`, còn model trả chữ thường (không gọi tool) thì parser trả
  **`None`** mà không báo gì. `_require` biến `None` thành `OutputParserException` để tầng trên (fallback) thấy được
  lỗi; thiếu bước này thì `None` đi tiếp vào pipeline và lỗi hiện ra ở một chỗ khác, khó đoán hơn.
- `with_retry` bọc **cả chuỗi** và chỉ bắt lỗi tạm thời. Thử lại một output sai schema với `temperature` 0 là gửi lại
  đúng prompt cũ cho cùng model: kết quả gần như chắc chắn giống hệt, chỉ tốn thêm một lượt. Lỗi kiểu đó cần
  **fallback** (cách khác), không cần retry.
- `wait_exponential_jitter=False` để test không phải chờ; trong production để mặc định (chờ tăng dần có nhiễu) để
  không dội lại server đang quá tải cùng lúc với mọi client khác.

**`naive_analysis`, `with_backup`.** `re.split(r"[?;]+")`, strip, bỏ phần rỗng. `analyzer.with_fallbacks([backup])` với
`backup = RunnableLambda(lambda inputs: naive_analysis(inputs["question"]))`: fallback nhận **cùng input** với runnable
chính (dict có `question`). `exceptions_to_handle` để mặc định (`Exception`) vì cả lỗi tạm thời đã hết lượt thử lẫn
lỗi output đều nên rơi về phân tích không LLM. Thứ tự lồng nhau quan trọng: retry ở **trong**, fallback ở **ngoài**;
đảo lại thì fallback chạy ngay lần lỗi đầu và retry không bao giờ có việc.

**`build_pipeline`.** `RunnablePassthrough.assign(analysis=analyzer) | RunnablePassthrough.assign(evidence=evidence)`:
mỗi `assign` chạy trên cả dict đầu vào và thêm một khoá, nên các khoá cũ (`user`) đi qua nguyên vẹn. Trong `evidence`,
`RunnableLambda(search).batch(parts)` chạy các phần trên thread pool của LangChain; dùng `dict(zip(parts, ...))` vì
`batch` giữ thứ tự đầu vào. Viết `{p: search(p) for p in parts}` cũng đúng kết quả nhưng tuần tự: với 4 phần và
retriever 0.3 s một lần là 1.2 s thay vì 0.3 s.

**`analyze_many`.** Bọc chain trong một hàm tự bắt lỗi của **chính nó** (`try: chain.invoke(...) except Exception as
exc: return exc`), rồi `RunnableLambda(safe).batch(inputs, config={"max_concurrency": n})`. Truyền `config` của
`RunnableLambda` vào `chain.invoke` để callback (ví dụ `CallCounter`) vẫn thấy các lời gọi con.

Cách hiển nhiên `chain.batch(inputs, return_exceptions=True)` **sai** khi chain có `with_retry`, do một lỗi của
`RunnableRetry._batch` trong `langchain-core` 1.6.12: sau lượt thử cuối, kết quả của các phần tử còn lỗi được lấy bằng
`result.pop(0)` trên danh sách kết quả **của lượt cuối**, danh sách này chứa cả phần tử vừa thành công ở lượt đó. Với
`stop_after_attempt=1`, lượt cuối là lượt đầu: `[0, 1, 2]` với phần tử 1 lỗi trả `[0, 0, 20]` cho hàm `x * 10` (phần tử
lỗi "mượn" kết quả của phần tử 0, không có exception nào). Với nhiều lượt, lỗi xuất hiện khi lượt cuối có cả phần tử
thành công lẫn phần tử lỗi. Log: `.superpowers/scratch/logs/retry_batch_bug.log`. Bài học: framework cũng có lỗi; test
với fake model là thứ bắt được nó.

**`CallCounter`.** `on_chat_model_start` tăng `calls`, `on_llm_error` tăng `errors` (chat model báo lỗi qua tên
`llm`). Mỗi lần thử lại là một lần gọi model, nên đếm được chi phí thật của retry.

## Chạy với model thật

Chuỗi của lời giải (`PROMPT | with_structured_output(QuestionAnalysis, method=...) | _require`) với
`ChatOllama(model="qwen2.5:3b", temperature=0, seed=0)` trên PC của track, ba nhóm 10 câu: 10 câu đầu của tập ghim Zalo
(một ý), 10 câu hai vế của bài Intermediate 03, 10 câu mức phạt giao thông không nói loại xe (log
`.superpowers/scratch/logs/theory_lcel.log`):

| method | Một ý: số vế trả về | Hai vế: tách đúng 2 | Thiếu loại xe: `missing` khác rỗng | Lỗi | Giây/câu |
| --- | --- | --- | --- | --- | --- |
| `function_calling` | 1 vế ở 3/10 câu, có câu 4 vế | 9/10 (1 câu ra `None`) | 0/10 | 1/30 | 1.9 đến 2.7 |
| `json_schema` (mặc định của `ChatOllama`) | 1 vế ở 5/10 câu, có câu 4 vế | 10/10 | 0/10 | 0/30 | 2.4 đến 3.8 |

Ba điều đọc được:

- `_require` có việc thật: một câu với `function_calling` ra `None` (model trả chữ thay vì gọi tool). Không có nó, `None`
  đi vào pipeline. `CallCounter` đếm 30 lượt gọi và 0 lỗi model cho mỗi method: lỗi output không phải lỗi của chat model,
  nên `on_llm_error` không thấy nó; muốn đếm thì đếm ở tầng parse.
- Model 3B tách **quá tay** câu một ý (một câu "Mức phạt khi quay đầu xe ô tô trên đường cao tốc" thành 2 đến 4 vế) và
  **không bao giờ** điền `missing` cho câu thiếu loại xe với một trường chữ tự do. Prompt và schema này chưa đủ cho model
  nhỏ; bài Intermediate 03 đo và sửa đúng chỗ này bằng schema hẹp (`bool`, `Literal`) và để code quyết định.
- `json_schema` ổn định hơn ở câu hai vế, chậm hơn một chút. Chọn method bằng số đo trên câu của bạn.
