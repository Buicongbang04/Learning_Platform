---
title: Fine-tune để "nhớ" luật hay RAG, đo trên Zalo Legal
level: advanced
services: []
files:
  - path: starter/finetune_vs_rag.ipynb
    note: 3 hàm TODO, phần chạy thí nghiệm tự viết
  - path: starter/REPORT.md
    note: Báo cáo
  - path: tests/test_finetune_vs_rag.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py zalo-legal
  - uv run jupyter lab tracks/ai-engineer/modules/14-fine-tuning-llm/exercises/advanced/02-finetune-vs-rag/starter/finetune_vs_rag.ipynb
  - uv run pytest tracks/ai-engineer/modules/14-fine-tuning-llm/exercises/advanced/02-finetune-vs-rag -q
---

## Mục tiêu

Đo bằng số điều mà module 13 mục 1 lập luận: fine-tune để nạp kiến thức (văn bản luật) không thay được retrieval. Bạn
fine-tune Qwen2.5-0.5B trả lời câu hỏi pháp luật bằng **một trích dẫn điều luật**, đo trích dẫn đúng bằng code trên câu đã
thấy và câu chưa thấy, rồi so với BM25 của module 13. Bài cũng là bước đệm cho milestone fine-tune của capstone: dựng dữ
liệu SFT từ qrels, chia theo câu hỏi, đo trước/sau.

## Đề bài

**Phần cứng:** GPU 4GB · ~180 phút

Chạy bằng kernel `ai-gpu`. Thời gian trên là thời gian làm bài; thời gian máy của bản tham chiếu trên PC của track (RTX 3060
12GB): <<A02_TIMES>>. Cần cài đặt BM25 của bạn ở module 13 bài Basic 02. Đọc mục 1, 5, 7 lý thuyết và mục 1 module 13.

1. Trong `starter/finetune_vs_rag.ipynb`, viết `citation`, `parse_citation`, `citation_scores` theo đặc tả. Cell `explore`
   đầu đã nạp corpus, câu hỏi, qrels và in một con số quan trọng: bao nhiêu câu ghim có điều đúng từng được hỏi trong train.
2. Tự viết phần còn lại, mỗi cấu hình đo `citation_scores` trên **300 câu ghim** (300 `query-id` đầu của `qrels/test.jsonl`,
   như module 13) và **300 câu train đầu tiên** (đo học thuộc):
   - BM25 top-1 trên toàn bộ 61 425 điều (văn bản là `title + " " + text`).
   - Qwen2.5-0.5B-Instruct gốc, chỉ prompt (system prompt yêu cầu đúng một trích dẫn).
   - SFT LoRA trên cặp (câu hỏi train, trích dẫn của điều đúng đầu tiên), vài epoch.
   - SFT LoRA trên các cặp đó **cộng** một mẫu cho mỗi điều của corpus: câu hỏi "Điều luật có tiêu đề ... nằm trong văn bản
     nào?", trả lời là trích dẫn của điều đó (một cách "đọc" cả corpus).
3. Đọc tận mắt các trích dẫn sai, viết `starter/REPORT.md` theo khung có sẵn, rồi làm phần trắc nghiệm của bài trong app.

**Một `REPORT.md` tốt**:

- Tách **học thuộc** (câu train) khỏi **tổng quát hoá** (câu ghim), và giải thích con số "câu ghim có điều đúng từng xuất
  hiện trong train".
- So với BM25 trên đúng 300 câu đó; nhắc lại BM25 của module 13 là baseline rẻ nhất, chưa phải RAG tốt nhất.
- Phân loại lỗi của model fine-tune: số hiệu không tồn tại, văn bản đúng sai điều, văn bản phổ biến trong train.
- Khuyến nghị có điều kiện: fine-tune ở đâu trong hệ trợ lý pháp luật thì có ích (embedding, định dạng câu trả lời), ở đâu
  thì không; điều gì bảng chưa đo (RAG + model fine-tune đọc nguồn).

## Tiêu chí đạt

- `citation` và `parse_citation` khớp các ví dụ trong test (hoa thường, khoảng trắng quanh dấu phẩy, số 0 đầu, trích dẫn
  đầu tiên, không nhận trích dẫn thiếu dấu phẩy); `parse_citation(citation(uid)) == uid`.
- `citation_scores` tính đúng `exact`, `law`, `format`; so văn bản bằng nguyên chuỗi số hiệu.
- `REPORT.md` không còn TODO, ít nhất 400 từ, có bảng.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Định dạng dữ liệu prompt-completion của TRL (`{"prompt": [...messages], "completion": [assistant]}`) cho bạn
`completion_only_loss` sẵn, giống label của bài Basic 02. Câu hỏi train có thể có nhiều điều đúng: chọn một quy tắc (điều
đầu tiên) và ghi vào báo cáo. Khi sinh, `max_new_tokens` 32 là đủ cho một trích dẫn.

### Gợi ý 2

Trước khi train, đếm: các điều được hỏi ở train và ở tập ghim chung nhau bao nhiêu? Con số đó cho biết trần của mọi cách
"nhớ câu trả lời". Mẫu "tiêu đề → trích dẫn" có khoảng 61 nghìn dòng: một epoch là đủ để thấy xu hướng, và batch 32 với
chuỗi ngắn vừa GPU 4GB.
