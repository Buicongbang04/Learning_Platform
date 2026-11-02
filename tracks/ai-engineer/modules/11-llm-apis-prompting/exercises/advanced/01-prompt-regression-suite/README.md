---
title: Prompt regression suite - cổng chất lượng cho mọi thay đổi prompt (portfolio)
level: advanced
services: []
files:
  - path: starter/suite.ipynb
    note: 4 hàm TODO, suite tự thiết kế
  - path: starter/REPORT.md
    note: Báo cáo quyết định merge
  - path: tests/test_suite.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py uit-vsfc
  - ollama pull qwen2.5:3b
  - uv run jupyter lab tracks/ai-engineer/modules/11-llm-apis-prompting/exercises/advanced/01-prompt-regression-suite/starter/suite.ipynb
  - uv run pytest tracks/ai-engineer/modules/11-llm-apis-prompting/exercises/advanced/01-prompt-regression-suite -q
---

## Mục tiêu

Dựng công cụ mà một đội làm sản phẩm LLM dùng hằng ngày: chạy mọi phiên bản prompt trên cùng tập ghim, cache kết quả
theo khoá xác định, báo chất lượng kèm khoảng tin cậy, chi phí và độ trễ, và một **cổng** tự động trả lời "thay đổi
này có được merge không". Bạn dùng nó để chặn một thay đổi trông vô hại nhưng làm hỏng một lớp hiếm, và viết báo cáo
mà trưởng nhóm đọc trong 5 phút.

## Đề bài

**Phần cứng:** CPU · ~300 phút

Thời gian trên là thời gian làm bài (thiết kế, code, chạy, đọc lỗi, viết báo cáo). Chạy năm phiên bản trên 150 câu
mất khoảng 10 phút trên PC của track (GPU dùng chung, phần lớn là CoT); chỉ CPU thì lâu hơn vài lần (chưa đo hết).
Làm bài Intermediate 02 trước.

1. Trong `starter/suite.ipynb`, cell chấm điểm:
   - `macro_f1`, `paired_bootstrap`: dán lời giải bài Intermediate 02.
   - `cache_key(prompt, model, params, item_id)`: SHA-256 của JSON chuẩn hoá, định nghĩa chính xác trong notebook.
   - `regression_gate(y_true, base_pred, cand_pred, *, max_drop, class_max_drop, max_unparsed_increase, n_boot,
     seed) -> GateResult`: bốn lý do chặn theo thứ tự cố định (tụt có ý nghĩa, tụt quá ngưỡng, tụt ở một lớp, output
     hỏng nhiều hơn). Notebook mô tả đủ.
2. Cell `explore`, thiết kế của bạn:
   - phiên bản prompt là dữ liệu (dict hoặc YAML), baseline là zero-shot của Intermediate 02;
   - chạy có cache theo `cache_key`: sửa một chữ trong prompt phải tự chạy lại đúng phiên bản đó;
   - năm ứng viên: few-shot, JSON schema, CoT-lite, một "sửa vội" bạn nghĩ vô hại (ví dụ bỏ dòng định nghĩa neutral
     khỏi system prompt), và cùng baseline chạy lại hoặc chạy chỉ CPU để đo sàn nhiễu;
   - bảng markdown sinh tự động: macro-F1 [CI], F1 từng lớp, `None`, p50 giây, token vào/ra, chi phí ước lượng cho
     1 000 câu theo một bảng giá có ngày kiểm (mục 3 lý thuyết) hoặc ghi "giả định", quyết định của cổng và lý do.
3. Viết `starter/REPORT.md` theo khung có sẵn, rồi làm phần trắc nghiệm của bài trong app.

**Một `REPORT.md` tốt**:

- Mở bằng **quyết định cho từng thay đổi** (merge hay chặn) kèm số, ví dụ minh hoạ với số bịa: "chặn thay đổi X: F1
  lớp neutral tụt từ 0.7 xuống 0.5 dù macro-F1 chỉ tụt 0.03".
- Bảng kết quả đủ cột và câu đọc bảng tách **chênh lệch thật** khỏi **nhiễu 150 câu**.
- Giải thích **vì sao** cổng thiết kế như vậy (ngưỡng nào, vì sao không đòi "tốt hơn có ý nghĩa thống kê"), và một ca
  cổng ra quyết định mà bạn không đồng ý.
- Phân tích lỗi: ít nhất 5 câu bị thay đổi bị chặn làm sai, đọc tận mắt, xếp loại.
- Giới hạn: 150 câu, một model, nhãn UIT-VSFC có nhiễu, tập cân bằng khác phân phối thật.

## Tiêu chí đạt

- `macro_f1`, `paired_bootstrap` khớp ví dụ của Intermediate 02.
- `cache_key` đúng từng ký tự với định nghĩa, không phụ thuộc thứ tự khoá của `params`, đổi khi prompt, model, tham
  số hay câu đổi.
- `regression_gate` cho đúng lý do theo thứ tự ở 6 tình huống của test (giống hệt, cải thiện, tụt lớn, tụt quá
  ngưỡng nhưng CI chạm 0, hy sinh lớp hiếm, thêm output hỏng).
- `REPORT.md` không còn TODO, ít nhất 500 từ, có bảng.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

F1 từng lớp là phần bạn đã viết bên trong `macro_f1`: tách nó thành hàm riêng để dùng lại cho `class_drop`. Với
`cache_key`, thử đổi thứ tự khoá trong `params` và in khoá ra: phải giống nhau. Lưu cache là một tệp JSON
`{khoá: {reply, seconds, prompt_tokens, output_tokens}}` là đủ.

### Gợi ý 2

Định nghĩa một phiên bản prompt gồm cả cách **đọc** output (`parse`), vì đổi định dạng output mà quên đổi parser là
một kiểu hồi quy hay gặp. Chạy "sửa vội" trước khi đoán kết quả của nó, rồi xem F1 từng lớp chứ không chỉ macro-F1.
