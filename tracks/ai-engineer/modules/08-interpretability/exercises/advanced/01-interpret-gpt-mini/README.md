---
title: Mổ xẻ GPT mini tiếng Việt của bạn (portfolio)
level: advanced
services: []
files:
  - path: starter/interpret_gpt_mini.ipynb
    note: 2 hàm chấm, còn lại tự thiết kế
  - path: starter/REPORT.md
    note: Báo cáo portfolio
  - path: tests/test_interpret_gpt_mini.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py iwslt15-en-vi
  - uv run jupyter lab tracks/ai-engineer/modules/08-interpretability/exercises/advanced/01-interpret-gpt-mini/starter/interpret_gpt_mini.ipynb
  - uv run pytest tracks/ai-engineer/modules/08-interpretability/exercises/advanced/01-interpret-gpt-mini -q
---

## Mục tiêu

Áp toàn bộ module lên model của chính bạn: GPT mini tiếng Việt đã pretrain ở module 05. Kết quả là một báo cáo interpretability
dùng được làm portfolio: bản đồ head, logit lens, probe có đối chứng, một thí nghiệm patching tự thiết kế và một SAE, mỗi kết luận có
bằng chứng, đối chứng, khoảng tin cậy và giới hạn. Câu hỏi trung tâm: một model 5 tới 14 triệu tham số train vài chục phút đã học được
những cơ chế nào trong số các cơ chế đã biết ở GPT-2, và bạn chứng minh được tới đâu.

## Đề bài

**Phần cứng:** CPU · ~480 phút

Thời gian trên là thời gian làm bài. GPT mini nhỏ hơn GPT-2 small khoảng 10 lần, nên mọi thí nghiệm chạy được trên CPU; trên bản
tham chiếu (CPU 4 luồng, PC dùng chung) thu activation cho SAE mất 90 giây và train SAE 143 giây. GPU 4GB giúp nhanh hơn nhưng không
bắt buộc.

**Checkpoint.** Đặt biến môi trường `GPT_MINI_CKPT` tới tệp `gpt-mini-v1` bạn lưu ở bài Advanced 01 của
[module 05](../../../../05-transformers-llm-architecture/exercises/advanced/01-gpt-mini-vietnamese/README.md) (định dạng đặc tả ở
notebook của bài đó: khoá `format`, `config`, `state_dict`, `tokenizer`). Chưa có checkpoint: train lại cấu hình laptop của bài đó
(4 tầng, `n_embd` 256, khoảng 5 phút trên GPU); không có GPU: train bản CPU của bài Intermediate 01 module 05 rồi lưu bằng
`save_checkpoint` (hàm bạn viết ở bài Advanced 01 module 05, định dạng `gpt-mini-v1`). Model càng nhỏ, càng ít cơ chế rõ: ghi điều đó vào báo cáo thay vì coi là thất bại.

1. Trong `starter/interpret_gpt_mini.ipynb`, viết 2 hàm được chấm: `top_examples` và `bootstrap_ci` (đặc tả trong notebook).
2. Thực hiện các phần theo khung gợi ý trong notebook: bản đồ head + ablation, logit lens, một probe có đủ đối chứng (thuộc tính tiếng
   Việt bạn chọn), một thí nghiệm activation patching tự thiết kế (cặp clean/corrupted khác nhau một token mà model của bạn làm đúng),
   một SAE trên một tầng giữa và đọc ít nhất 10 latent.
3. Mọi con số trung bình (accuracy probe, hiệu ứng patching) kèm khoảng tin cậy bootstrap theo ngữ cảnh hoặc theo cặp prompt.
4. Viết `starter/REPORT.md`, rồi làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `top_examples` và `bootstrap_ci` pass test (fixture).
- `REPORT.md` không còn TODO, ít nhất 800 từ, có mục bảng kết luận dạng bảng; hình (nếu có) phải tồn tại.
- Nội dung chấm theo rubric trong `SOLUTION.md`: mỗi kết luận có thí nghiệm, đối chứng, độ bất định và câu "không chứng minh".

## Gợi ý

### Gợi ý 1

Viết một tệp `.py` nhỏ cạnh notebook gom các hàm bạn đã viết ở các bài trước (cache, điểm head, lens, probe, patching, SAE) và
import nó, thay vì chép lại vào notebook. Chạy mọi thí nghiệm trên GPT-2 small trước một lần (bạn đã có số tham chiếu ở các bài
Intermediate) để chắc công cụ đúng, rồi mới chuyển sang GPT mini.

### Gợi ý 2

Model nhỏ tiếng Việt có thể không làm được bài IOI tiếng Anh. Chọn nhiệm vụ patching từ thứ model chắc chắn làm được: chép lại một
chuỗi đã xuất hiện (thay một token ở bản thứ nhất), hoàn thành một từ ghép quen thuộc, hoặc một mẫu câu lặp trong Wikipedia (tên
tỉnh, huyện). Kiểm trước rằng logit difference của run clean dương ở hầu hết cặp; nếu không, nhiệm vụ quá khó với model.
