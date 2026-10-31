---
title: Context length thật của qwen2.5:3b qua Ollama, đo bằng needle in a haystack
level: advanced
services: []
files:
  - path: starter/needle.ipynb
    note: 2 hàm TODO, thí nghiệm TODO
  - path: starter/REPORT.md
    note: Báo cáo "dùng được tới đâu"
  - path: tests/test_needle.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py wikipedia-vi
  - ollama pull qwen2.5:3b
  - uv run jupyter lab tracks/ai-engineer/modules/09-llms-and-open-models/exercises/advanced/02-needle-in-haystack/starter/needle.ipynb
  - uv run pytest tracks/ai-engineer/modules/09-llms-and-open-models/exercises/advanced/02-needle-in-haystack -q
---

## Mục tiêu

Biến con số "context 32 768 token" trên model card thành một bản đồ đo được: với cấu hình Ollama của bạn,
`qwen2.5:3b` tìm lại một dữ kiện giấu trong văn bản dài tới độ dài nào, ở vị trí nào, và vì sao. Bạn viết bộ dựng
haystack và bộ chấm có test, chạy một lưới thí nghiệm có cache, và viết báo cáo cho đồng nghiệp sắp đưa tài liệu dài
vào prompt.

## Đề bài

**Phần cứng:** GPU 4GB · ~180 phút

Thời gian trên là thời gian làm bài. Thời gian máy chạy, đo trên PC của track với `qwen2.5:3b` hết trên GPU: lưới 40 ô
(4 độ dài × 5 vị trí × 2 `num_ctx`) khoảng 1.5 phút, prompt 12 000 token khoảng 4 giây. `qwen2.5:3b` ở `num_ctx` 16 384
cần khoảng 0.6 GiB KV cache fp16 cộng trọng số, vẫn vừa GPU 4 GB. Chỉ có CPU: trên PC, Ollama giới hạn 4 luồng đọc
prompt khoảng 500 token/s, nên **ước lượng** khoảng 25 giây cho mỗi prompt 12 000 token và khoảng 15 phút cho cả lưới
(chưa chạy cả lưới ở chế độ CPU).

1. Trong `starter/needle.ipynb`, cell chấm điểm: `build_haystack` và `needle_found` theo mô tả trong notebook.
2. Cell `explore`: filler là các bài Wikipedia tiếng Việt (cell có sẵn), đếm token bằng tokenizer Qwen2.5 (cùng
   tokenizer với 3B). Chạy lưới: độ dài filler {1 000, 3 000, 6 000, 12 000} token × vị trí needle {0, 0.25, 0.5, 0.75,
   1} × `num_ctx` {mặc định, 16 384}. Needle là một câu chứa mã số 4 chữ số khác nhau cho mỗi ô; câu hỏi đặt ở **cuối**
   prompt. `temperature` 0. Ghi cho mỗi ô: số token bạn đếm, `prompt_eval_count`, câu trả lời, đúng/sai, thời gian.
3. Bảng hoặc heatmap đúng/sai theo (độ dài, vị trí) cho từng `num_ctx`, và một bảng so `prompt_eval_count` với số token
   đếm được. Giải thích **từng** ô sai bằng cơ chế, không bằng "model yếu".
4. Mở rộng tuỳ chọn (không chấm, cần GPU 12GB hoặc chịu chạy chậm): lặp lại với `qwen2.5:7b`, hoặc với độ dài 24 000
   token ở `num_ctx` 32 768; ghi rõ máy đo.
5. Viết `starter/REPORT.md` theo khung có sẵn, rồi làm phần trắc nghiệm của bài trong app.

**Một `REPORT.md` tốt** trả lời được câu hỏi của đồng nghiệp: "tôi đưa hợp đồng 10 000 token vào `qwen2.5:3b` qua
Ollama, có ổn không, phải cấu hình gì?" Nó tách hai hiện tượng khác nhau (runtime cắt prompt, và model không dùng được
thông tin dù đã đọc), nói rõ bài test này dễ hay khó so với việc thật, và có con số cho từng khẳng định.

## Tiêu chí đạt

- `build_haystack` lấy filler theo vòng, đếm token từng đoạn (không đếm needle, không đếm lại cả văn bản), dừng ngay khi
  đủ, chèn needle ở `round(depth * số đoạn)`, báo lỗi với `depth` ngoài `[0, 1]` hoặc filler rỗng.
- `needle_found` chấp nhận dấu phân cách nghìn (`7.429`, `7 429`), không nhận số dính chữ số khác (`17429`, `74290`),
  không nhận một phần số.
- `REPORT.md` không còn TODO, ít nhất 400 từ, có bảng kết quả lưới và bảng `prompt_eval_count`.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Trước khi nhìn tỉ lệ đúng, nhìn `prompt_eval_count`. Nếu nó dừng ở cùng một con số cho mọi prompt dài, mọi kết luận về
"vị trí" ở các ô đó là kết luận về **phần nào của prompt còn lại**, không phải về khả năng của model. Thử đoán trước:
runtime giữ phần đầu hay phần cuối của prompt, và vị trí needle nào sống sót. Ô nào không khớp dự đoán thì xem log
server (`journalctl -u ollama` trên Linux) và nghĩ xem cache còn chỗ cho câu trả lời không.

### Gợi ý 2

Một needle duy nhất, câu hỏi gần như chép lại câu chứa needle, là bài kiểm tra dễ nhất có thể: model chỉ cần khớp chuỗi.
Đúng 100% ở bài này chưa nói gì về tóm tắt, so sánh hay suy luận trên cả tài liệu. Đọc cách RULER (link ở mục 8 lý
thuyết) làm khó dần bài kiểm tra, và nói trong báo cáo kết quả của bạn đứng ở đâu so với đó.
