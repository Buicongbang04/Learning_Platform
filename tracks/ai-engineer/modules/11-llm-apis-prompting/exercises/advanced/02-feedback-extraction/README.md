---
title: Ứng dụng trích xuất phản hồi sinh viên có schema, quy tắc nghiệp vụ và chấm điểm (portfolio)
level: advanced
services: []
files:
  - path: starter/extract.ipynb
    note: 2 hàm TODO, ứng dụng tự thiết kế
  - path: starter/REPORT.md
    note: Báo cáo kết quả và khuyến nghị
  - path: tests/test_extract.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py uit-vsfc
  - ollama pull qwen2.5:3b
  - uv run jupyter lab tracks/ai-engineer/modules/11-llm-apis-prompting/exercises/advanced/02-feedback-extraction/starter/extract.ipynb
  - uv run pytest tracks/ai-engineer/modules/11-llm-apis-prompting/exercises/advanced/02-feedback-extraction -q
---

## Mục tiêu

Làm một ứng dụng LLM hoàn chỉnh cỡ nhỏ có thể đưa vào portfolio: biến phản hồi tự do của sinh viên thành bản ghi có
cấu trúc (cảm xúc, chủ đề, khía cạnh, có việc cần làm không, gợi ý), với schema, quy tắc nghiệp vụ mà schema không
diễn đạt được, vòng gọi lại khi sai, chấm điểm trên nhãn thật, tự chấm phần không có nhãn, và ước lượng chi phí vận
hành. Đây là dạng bài toán "LLM thay cho một pipeline NLP" gặp nhiều nhất ngoài thực tế.

## Đề bài

**Phần cứng:** CPU · ~300 phút

Thời gian trên là thời gian làm bài (thiết kế, code, chạy, tự chấm 30 câu, viết báo cáo). Một lượt trích xuất trên
150 câu mất khoảng 4 tới 6 phút trên PC của track với `qwen2.5:3b` (output JSON vài chục token mỗi câu); chỉ CPU thì
lâu hơn vài lần. Làm bài Basic 03 và Intermediate 02 trước.

1. Trong `starter/extract.ipynb`, cell chấm điểm (notebook mô tả đủ):
   - `check_record(record) -> list[str]`: lỗi schema theo `EXTRACTION_SCHEMA` (bằng `jsonschema`), rồi hai quy tắc
     nghiệp vụ: `suggestion` phải có khi và chỉ khi `actionable` là `true`; `aspects` không có phần tử rỗng, không trùng.
   - `score_batch(records, golds) -> dict`: tỉ lệ hợp lệ, accuracy và macro-F1 cho cảm xúc (3 nhãn) và chủ đề (4 nhãn)
     theo nhãn thật UIT-VSFC (bản ghi không hợp lệ tính là sai), tỉ lệ `actionable`.
2. Cell `explore`, thiết kế của bạn: prompt, gọi `qwen2.5:3b` với schema, gọi lại khi `check_record` báo lỗi, chạy trên
   150 câu ghim (như Intermediate 02) có cache, so ít nhất hai cấu hình (ví dụ: chỉ dặn trả JSON trong prompt, ép bằng
   JSON schema, ép schema và gọi lại), **tự chấm 30 câu** cho `aspects`, `actionable`, `suggestion`, ước lượng chi phí
   10 000 phản hồi mỗi học kỳ nếu dùng model API (hàm của bài Basic 02, bảng giá có ngày kiểm hoặc "giả định").
   Tuỳ chọn: CLI hoặc giao diện nhỏ đọc CSV phản hồi, xuất CSV kết quả.
3. Viết `starter/REPORT.md` theo khung có sẵn, rồi làm phần trắc nghiệm của bài trong app.

Lưu ý dữ liệu: tập ghim cân bằng theo **cảm xúc**, nên phân phối **chủ đề** trong đó vẫn lệch (phần lớn là giảng viên);
macro-F1 chủ đề dao động mạnh theo vài câu `facility` và `others`. Nhãn UIT-VSFC có nhiễu (mục 7 lý thuyết): trước khi
nói model sai, đọc câu.

**Một `REPORT.md` tốt**: mở bằng khuyến nghị có số ("dùng cho cảm xúc và chủ đề với độ đúng X, chưa dùng trường gợi ý
vì chỉ Y/30 câu đạt"), bảng so cấu hình, mục tự chấm có tỉ lệ đồng ý và hướng sai, phân tích lỗi có ví dụ thật, chi phí
và rủi ro dữ liệu cá nhân, giới hạn.

## Tiêu chí đạt

- `check_record`: bản ghi hợp lệ cho `[]`; 9 kiểu lỗi schema đều bắt đầu bằng `"schema: "` và không kiểm quy tắc khi
  schema đã sai; 6 ca quy tắc cho đúng danh sách lỗi theo thứ tự.
- `score_batch`: đúng mọi khoá trên lô 5 câu có bản ghi đúng, sai nhãn, sai quy tắc và `None`; macro-F1 khớp
  `sklearn` với bản ghi không hợp lệ tính là sai; không có câu hợp lệ thì tỉ lệ `actionable` là 0; độ dài lệch hoặc
  rỗng thì `ValueError`.
- `REPORT.md` không còn TODO, ít nhất 500 từ, có bảng.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`jsonschema.Draft202012Validator(schema).iter_errors(record)` liệt kê mọi lỗi, mỗi lỗi có `.message`. Trong
`score_batch`, đổi bản ghi không hợp lệ thành `None` một lần ở đầu, rồi mọi thước đo dùng cùng danh sách đó.

### Gợi ý 2

Mô tả mỗi trường trong prompt bằng một câu và một ví dụ; giữ tên khoá trong prompt khớp schema. Để chấm trường tự do,
viết tiêu chí trước khi đọc output (ví dụ: `actionable` đúng khi phản hồi nêu một việc mà trường hoặc giảng viên làm
được trong một học kỳ), rồi chấm mù (ẩn tên cấu hình).
