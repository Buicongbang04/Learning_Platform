---
title: RAG có trích dẫn kiểm bằng code và cổng từ chối
level: intermediate
services: []
files:
  - path: starter/rag.ipynb
    note: 3 hàm TODO
  - path: tests/test_rag.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py zalo-legal
  - ollama pull qwen2.5:3b
  - ollama pull bge-m3
  - uv run jupyter lab tracks/ai-engineer/modules/13-rag/exercises/intermediate/02-rag-with-citations/starter/rag.ipynb
  - uv run pytest tracks/ai-engineer/modules/13-rag/exercises/intermediate/02-rag-with-citations -q
---

## Mục tiêu

Viết nửa generation của hệ RAG: prompt có nguồn đánh số, đọc và kiểm trích dẫn bằng code, cổng từ chối trước LLM.
Rồi chạy thật với `qwen2.5:3b` trên câu hỏi pháp luật thật, đếm theo cây debug ở mục 6 lý thuyết để biết câu trả lời
hỏng vì retrieval hay vì generation, và thấy đổi đơn vị nguồn từ cả điều sang khoản thay đổi kết quả thế nào.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Cần Ollama với `qwen2.5:3b` và `bge-m3`, và cache vector corpus của **bài 01** (`data/raw/zalo-legal/cache/bge-m3.npy`):
làm bài 01 trước. Các cell `explore` gọi LLM khoảng 30 lần, chạy chừng 3 phút trên laptop GPU 4GB.

Mở `starter/rag.ipynb`. Trong cell chấm điểm:

1. `build_messages(question, passages) -> list[Message]`: hai message `system` và `user` theo khung ở mục 5 lý thuyết.
   Notebook nêu đúng định dạng dòng đầu của mỗi nguồn (`[i] <số hiệu văn bản>, <tiêu đề>`) và câu từ chối `REFUSAL`.
2. `parse_citations(answer, n_passages) -> list[int]`: các `[i]` theo thứ tự, bỏ số ngoài `1..n_passages`, bỏ trùng.
3. `answer(question, retrieve, llm, min_score) -> RagAnswer`: điểm cao nhất dưới `min_score` (hoặc không có hit) thì
   từ chối **không gọi LLM**; ngược lại gọi LLM một lần với mọi hit, map trích dẫn về `uid` (bỏ uid trùng), đánh dấu
   `refused` khi câu trả lời chứa "Không tìm thấy căn cứ".

Rồi chạy các cell `explore`:

- Tái hiện thí nghiệm ở mục 5 lý thuyết (cả điều cắt ở 1 500 ký tự) bằng `build_messages` của bạn.
- Retrieve hai tầng: dense `bge-m3` tìm 5 điều trên toàn corpus (cache bài 01), tách các điều đó theo khoản, giữ 5
  khoản có cosine cao nhất với câu hỏi làm nguồn.
- 20 câu đầu của tập ghim: in câu trả lời, nguồn, và bảng đếm (điều đúng có trong nguồn, có trích dẫn, trích đúng điều,
  từ chối dù có căn cứ). 5 câu ngoài phạm vi: cổng điểm chặn bao nhiêu câu trước LLM.

Sau đó làm phần trắc nghiệm của bài trong app. Câu trả lời của LLM có thể lệch đôi chút giữa các máy và phiên bản
Ollama; các câu trắc nghiệm số liệu lấy từ lần chạy của lời giải mẫu.

## Tiêu chí đạt

- `build_messages`: đúng hai vai, system chứa đúng câu `REFUSAL` và nói định dạng `[số]`; mỗi nguồn có dòng đầu
  `[i] <số hiệu>, <tiêu đề>` rồi nội dung, theo đúng thứ tự; không có `[n+1]`; câu hỏi đứng cuối.
- `parse_citations("Theo [2], phạt tiền [1]. Xem [7] và [2], [0].", 5) == [2, 1]`.
- `answer` với `FakeLLM`: prompt đúng bằng `build_messages` của mọi hit, `[7]` bị bỏ, hai khoản cùng điều chỉ cho một
  uid; mọi điểm dưới ngưỡng thì `FakeLLM.calls` rỗng và `refused=True`; LLM trả câu từ chối thì `refused=True`.
- Cell `explore` chạy hết với `qwen2.5:3b` và in bảng đếm của 20 câu.

## Gợi ý

### Gợi ý 1

Dựng phần nguồn bằng một list các khối chuỗi rồi `"\n\n".join(...)`; `enumerate(passages, start=1)` cho số bắt đầu
từ 1. Số hiệu văn bản là phần `uid` trước dấu `+` cuối cùng. Kiểm `build_messages` bằng cách in message `user` ra xem
trước khi chạy test.

### Gợi ý 2

`re.finditer(r"\[(\d+)\]", answer)` duyệt các trích dẫn theo thứ tự xuất hiện. Trong `answer`, kiểm cổng điểm **trước**
mọi việc khác; trích dẫn `[i]` ứng với `passages[i - 1]`.
