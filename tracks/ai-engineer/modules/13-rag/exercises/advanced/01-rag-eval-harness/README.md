---
title: Bộ đánh giá RAG với LLM-as-judge, chọn cấu hình bằng số liệu (portfolio)
level: advanced
services: []
files:
  - path: starter/eval.ipynb
    note: 5 hàm TODO, 2 cấu hình TODO
  - path: starter/REPORT.md
    note: Báo cáo khuyến nghị cấu hình
  - path: tests/test_eval.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py zalo-legal
  - ollama pull qwen2.5:3b
  - ollama pull bge-m3
  - ollama pull qwen2.5:7b
  - uv run jupyter lab tracks/ai-engineer/modules/13-rag/exercises/advanced/01-rag-eval-harness/starter/eval.ipynb
  - uv run pytest tracks/ai-engineer/modules/13-rag/exercises/advanced/01-rag-eval-harness -q
---

## Mục tiêu

Dựng một harness đánh giá RAG end-to-end chạy lại được sau mỗi thay đổi: thước đo retrieval từ qrels, faithfulness và
answer relevance do LLM chấm, tỉ lệ từ chối, độ trễ; so bốn cấu hình (đơn vị chunk, hybrid, rerank) trên cùng tập câu
hỏi ghim. Phần khó nhất không phải viết code mà là **biết tin điểm judge tới đâu**: bạn kiểm judge bằng nguồn sai và
bằng nhãn của chính mình trước khi dùng nó để chọn cấu hình.

## Đề bài

**Phần cứng:** GPU 4GB · ~360 phút

Thời gian trên là thời gian làm bài (code, chạy, đọc mẫu, tự chấm 20 câu, viết báo cáo). Model sinh là `qwen2.5:3b`.
Judge nên mạnh hơn model sinh. Cả bảng là khoảng 300 lượt gọi judge:

- `qwen2.5:7b` (khuyên dùng) chạy tốt trên PC GPU 12GB; trên laptop GPU 4GB nó vẫn chạy (một phần trên CPU) nhưng
  chậm (chưa đo trên bản tham chiếu, ước khoảng 1 giờ cho cả bảng).
- Chỉ có laptop: `qwen2.5:3b` làm judge (chưa đo, ước khoảng 25 phút), và ghi rõ giới hạn đó trong báo cáo: 3B là cùng model
  sinh câu trả lời, và nó dễ dãi với nguồn sai (mục 6 lý thuyết).
- Tuỳ chọn: judge mạnh hơn qua một gateway tương thích OpenAI (OmniRoute, Gemini...). Khai báo trong `setup/.env`
  `OMNIROUTE_BASE_URL` (kết thúc bằng `/v1`), `OMNIROUTE_API_KEY`, `OMNIROUTE_MODEL`, rồi bỏ comment đoạn tạo
  `OpenAICompatClient` trong cell chạy harness. Không bao giờ commit key. Bản tham chiếu dùng cách này: khoảng 6 giây
  một lượt, cả bảng khoảng 1 giờ.

Cần cache của ba bài Intermediate trong `data/raw/zalo-legal/cache/`: làm bài 01 và 03 trước.

1. Trong `starter/eval.ipynb`, cell chấm điểm:
   - `recall_at_k`, `mrr_at_k`: dán lời giải bài Basic 03 (notebook tự chứa, không import chéo bài).
   - `judge_faithfulness(answer: str, passages: list[str], llm) -> float`: judge tách câu trả lời thành khẳng định,
     đánh dấu từng khẳng định có được nguồn ủng hộ; trả tỉ lệ được ủng hộ trong [0, 1]. Gọi `llm.chat` một lần với
     `json_schema=FAITHFULNESS_SCHEMA`. JSON hỏng, sai kiểu, không có khẳng định nào, hoặc lời gọi judge lỗi
     (`llmkit.LLMError`: Ollama tắt, gateway 504) thì trả `nan`, không crash.
   - `judge_relevance(question: str, answer: str, llm) -> float`: điểm 1..5 có mô tả từng mức qua
     `json_schema=RELEVANCE_SCHEMA`, trả `(score - 1) / 4`; JSON hỏng hoặc điểm ngoài 1..5 thì `nan`.
   - `run_eval(configs: dict[str, Callable], questions) -> pd.DataFrame`: một dòng mỗi cấu hình, cột đúng `COLUMNS`
     (`config`, `n`, `recall@5`, `mrr@10`, `context_hit`, `refused`, `faithfulness`, `relevance`, `judge_nan`,
     `latency_s`). Câu bị từ chối không gửi judge; điểm judge lấy trung bình bỏ qua `nan`. Notebook mô tả từng cột.
   - Giữ nguyên hai schema, `COLUMNS`, các dataclass `Question` và `RagOutput`: test dùng chúng.
2. Cell `explore`: viết nốt hai cấu hình `hybrid · khoản` và `hybrid + rerank · khoản` (hai cấu hình dense đã có
   mẫu), sinh câu trả lời cho 50 câu đầu tập ghim (cache ra đĩa, hai pha để GPU 4GB không phải nạp lại model liên tục),
   chạy `run_eval` với judge, rồi **kiểm judge**:
   - chấm lại cùng câu trả lời với nguồn của câu hỏi khác: judge tốt phải cho điểm gần 0;
   - tự chấm 20 câu trả lời (cell ghi `calibration.csv`, bạn điền cột `human`), đo tỉ lệ đồng ý với judge.
3. Viết `starter/REPORT.md` theo khung có sẵn, rồi làm phần trắc nghiệm của bài trong app.

**Một `REPORT.md` tốt** để trưởng nhóm quyết định được trong 5 phút:

- Mở bằng **khuyến nghị có số**, ví dụ minh hoạ với số bịa: "dùng cấu hình X: context_hit 0.9 so với 0.7, từ chối
  giảm từ 40% xuống 10%, độ trễ N giây; cấu hình Y thêm M giây mỗi câu mà MRR chỉ tăng trong mức nhiễu". Không mở bằng
  định nghĩa RAG.
- Bảng `run_eval` đủ cột, và câu đọc bảng tách **chênh lệch thật** khỏi **nhiễu của 50 câu**: một câu là 0.02 điểm
  recall, nên chênh lệch 0.02 tới 0.04 chưa nói được gì.
- Mục **judge có đáng tin không** là phần người đọc kỹ nhất: kết quả thí nghiệm nguồn sai, tỉ lệ đồng ý với nhãn của
  bạn, judge sai theo hướng nào (dễ dãi hay khắt khe). Điểm faithfulness không kèm mục này thì không ai nên tin.
- **Phân tích lỗi** có ví dụ thật: đọc ít nhất 5 câu điểm thấp hoặc từ chối, xếp theo cây debug ở mục 6 lý thuyết.
- **Giới hạn**: 50 câu, một model sinh, judge nhỏ, nhãn qrels chỉ ghi một điều đúng mỗi câu.

## Tiêu chí đạt

- `recall_at_k`, `mrr_at_k` khớp ví dụ tính tay ở mục 6 lý thuyết.
- `judge_faithfulness` với `FakeLLM`: 3 khẳng định, 2 được ủng hộ cho 2/3; prompt chứa câu trả lời và mọi đoạn nguồn;
  truyền `json_schema=FAITHFULNESS_SCHEMA`; 8 kiểu câu trả lời hỏng (không phải JSON, JSON cắt cụt, thiếu khoá, sai
  kiểu, danh sách rỗng...) đều cho `nan`; `llm.chat` ném `llmkit.LLMError` thì cả hai judge cho `nan`.
- `judge_relevance`: điểm 5, 4, 1 cho 1.0, 0.75, 0.0; điểm 9, 0, 3.5, `"năm"`, `true` hay JSON hỏng cho `nan`.
- `run_eval` trên hai cấu hình giả: cột đúng `COLUMNS` theo thứ tự, mỗi cấu hình gọi đúng một lần mỗi câu, số liệu
  từng cột đúng (kể cả trung vị độ trễ, `judge_nan`), câu từ chối không tới judge; judge luôn trả chuỗi hỏng thì bảng
  vẫn ra với `nan`; `judge=None` dùng `llmkit.get_client()`.
- `REPORT.md` không còn TODO, ít nhất 500 từ, có bảng.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Bọc **cả** `json.loads` lẫn phần đọc khoá trong một `try` bắt `ValueError`, `KeyError`, `TypeError`
(`json.JSONDecodeError` là con của `ValueError`), rồi kiểm kiểu sau đó: `isinstance(True, int)` là `True` trong Python,
nên điểm `true` phải bị loại riêng. Trong `run_eval`, gom điểm judge vào list rồi tự lấy trung bình phần không phải
`nan`; `statistics.median` cho trung vị độ trễ. Lời gọi judge cũng có thể ném `llmkit.LLMError` (Ollama tắt, quá thời
gian chờ, gateway trả 504): bắt nó trong cùng `try` để một lượt gọi lỗi chỉ thành một `nan` được đếm ở `judge_nan`.

### Gợi ý 2

Prompt judge faithfulness cần nói rõ **định nghĩa** "được ủng hộ": đúng theo hiểu biết chung nhưng không có trong nguồn
vẫn là `false`. Thiếu câu đó, judge nhỏ chấm theo kiến thức của nó và cho điểm cao cả khi nguồn không liên quan. Đánh
số các đoạn nguồn và đặt câu trả lời **sau** nguồn. Khi kiểm judge bằng nguồn sai mà điểm trung bình vẫn trên 0.3, sửa
prompt judge trước khi tin bất kỳ cột faithfulness nào.
