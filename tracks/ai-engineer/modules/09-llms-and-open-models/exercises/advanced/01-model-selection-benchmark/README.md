---
title: Chọn model local cho phân loại chủ đề tiếng Việt bằng benchmark của chính bạn (portfolio)
level: advanced
services: []
files:
  - path: starter/benchmark.ipynb
    note: 4 hàm TODO, thí nghiệm TODO
  - path: starter/REPORT.md
    note: Báo cáo khuyến nghị model
  - path: tests/test_benchmark.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py uit-vsfc
  - ollama pull qwen2.5:3b
  - ollama pull qwen2.5:7b
  - uv run jupyter lab tracks/ai-engineer/modules/09-llms-and-open-models/exercises/advanced/01-model-selection-benchmark/starter/benchmark.ipynb
  - uv run pytest tracks/ai-engineer/modules/09-llms-and-open-models/exercises/advanced/01-model-selection-benchmark -q
---

## Mục tiêu

Làm đúng việc mà mục 2 lý thuyết nói là quan trọng nhất khi chọn model: đo các ứng viên trên **tập eval của chính bài
toán**, cùng mẫu, cùng prompt, cùng cách chấm, cả chất lượng lẫn chi phí, rồi viết một khuyến nghị mà người đọc tin được
vì nó nói rõ chênh lệch nào là thật, chênh lệch nào là nhiễu.

## Đề bài

**Phần cứng:** GPU 4GB · ~240 phút

Thời gian trên là thời gian làm bài (viết hàm, thiết kế prompt, chạy, đọc lỗi, viết báo cáo). Thời gian máy chạy cho
120 câu mỗi cấu hình, đo trên PC của track: `qwen2.5:3b` hết trên GPU khoảng 1 phút; `qwen2.5:7b` với một nửa số tầng
trên GPU (giống laptop 4 GB) khoảng 3 phút; `Qwen2.5-0.5B-Instruct` bằng `transformers` trên CPU 4 luồng khoảng 2 phút.
Laptop chỉ có CPU vẫn làm được: `qwen2.5:3b` chạy CPU khoảng 1.2 giây một câu, `qwen2.5:7b` chậm hơn vài lần.

Bài toán: tính năng "tự gắn chủ đề cho phản hồi của sinh viên" trên UIT-VSFC (4 chủ đề: giảng viên, chương trình đào
tạo, cơ sở vật chất, khác). Ứng viên bắt buộc: `Qwen/Qwen2.5-0.5B-Instruct` (Hugging Face), `qwen2.5:3b`,
`qwen2.5:7b` (Ollama). Thêm ít nhất một biến thể cấu hình bạn tự chọn (ví dụ `format` là JSON schema có `enum` nhãn,
few-shot, hoặc chạy cùng model trên CPU thay vì GPU).

1. Trong `starter/benchmark.ipynb`, cell chấm điểm: `stratified_sample`, `parse_label`, `macro_f1`,
   `latency_summary` theo mô tả trong notebook.
2. Cell `explore`: lấy 30 câu mỗi chủ đề từ tập test (seed 0, 120 câu), viết **một** prompt dùng chung cho mọi model,
   chạy từng cấu hình với `temperature` 0, cache từng câu trả lời ra đĩa (độ trễ, số token sinh, thời gian sinh), ghi
   bộ nhớ từ `/api/ps`. Bảng so sánh: macro-F1, accuracy, số câu không đọc được nhãn, p50/p95 độ trễ, token/s, bộ nhớ,
   VRAM; confusion matrix từng cấu hình.
3. Ước lượng độ bất định: 120 câu là ít. Dùng bootstrap theo cặp (lấy lại cùng các chỉ số câu cho hai cấu hình) để
   có khoảng tin cậy cho **chênh lệch** macro-F1 giữa hai cấu hình bạn định so.
4. Viết `starter/REPORT.md` theo khung có sẵn, rồi làm phần trắc nghiệm của bài trong app.

**Một `REPORT.md` tốt** để trưởng nhóm quyết định trong 5 phút:

- Mở bằng khuyến nghị có số (model, chất lượng, độ trễ, bộ nhớ, điều kiện phần cứng), không mở bằng định nghĩa LLM.
- Bảng đủ cột, và câu đọc bảng tách chênh lệch có khoảng tin cậy không chứa 0 khỏi chênh lệch trong mức nhiễu.
- Phân tích lỗi từ confusion matrix: model nhầm cặp nhãn nào, vì sao (đọc câu thật), nhãn nào prompt định nghĩa mơ hồ.
- Nói về phân phối thật: mẫu cân bằng 30 câu mỗi nhãn khác hẳn tập test thật; con số nào đổi khi áp lên lưu lượng thật.
- Giới hạn: 120 câu, một prompt, giấy phép từng model (`/api/show`), máy đo.

## Tiêu chí đạt

- `stratified_sample` giữ index gốc, nhãn tăng dần, nhãn ít hơn `n` thì lấy hết, đúng `random_state`.
- `parse_label` đọc được nhãn trong câu trả lời tự do (hoa thường, NFC, dấu câu, câu dài), trả `None` khi không có hoặc
  có hơn một nhãn, không khớp "khác" bên trong "khách".
- `macro_f1` khớp ví dụ tính tay và `sklearn.metrics.f1_score(average="macro")`, `None` là dự đoán sai.
- `latency_summary` đúng p50, p95 nội suy tuyến tính và trung bình, kiểu `float`.
- `REPORT.md` không còn TODO, ít nhất 500 từ, có bảng và khoảng tin cậy bootstrap cho ít nhất một chênh lệch.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Đừng để cách đọc câu trả lời quyết định thứ hạng: in vài câu trả lời thô của mỗi model trước khi tin bảng. Model nhỏ
hay chép lại cả danh sách nhãn trong system prompt; một parser "lấy nhãn đầu tiên tìm thấy" sẽ chấm câu đó đúng hoặc sai
một cách ngẫu nhiên. Đếm số câu không đọc được thành một cột riêng.

### Gợi ý 2

Bootstrap theo cặp: lặp vài nghìn lần, rút 120 chỉ số câu có hoàn lại, tính macro-F1 của **cả hai** cấu hình trên cùng
các chỉ số đó, lưu hiệu. Khoảng 2.5% tới 97.5% của các hiệu là khoảng tin cậy 95%. Trên cùng dữ liệu, chạy lại cùng một
model trên phần cứng khác (GPU và CPU) cũng là một phép đo nhiễu đáng làm.
