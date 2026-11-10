---
title: Hiệu chuẩn LLM judge với nhãn người trên UIT-VSFC và Zalo Legal
level: intermediate
services: []
files:
  - path: starter/judge.ipynb
    note: 9 hàm TODO, dán 4 hàm của Basic 02
  - path: tests/test_judge.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py uit-vsfc
  - uv run python data/download_dataset.py zalo-legal
  - ollama pull qwen2.5:3b
  - ollama pull bge-m3
  - uv run jupyter lab tracks/ai-engineer/modules/20-evaluation-production/exercises/intermediate/01-judge-calibration/starter/judge.ipynb
  - uv run pytest tracks/ai-engineer/modules/20-evaluation-production/exercises/intermediate/01-judge-calibration -q
---

## Mục tiêu

Biết một LLM judge đáng tin tới đâu **trước** khi dùng nó: đo độ khớp với nhãn người bằng accuracy và Cohen's kappa, judge
sai theo hướng nào, xác suất nó đưa ra có đúng nghĩa xác suất không, và khi so cặp thì nó chọn theo nội dung hay theo vị
trí và độ dài. Nhãn người lấy từ bộ dữ liệu có sẵn nên ai chạy lại cũng ra cùng tập.

## Đề bài

**Phần cứng:** GPU 4GB · ~150 phút

Thời gian trên là thời gian làm bài. Phần chạy: khoảng 600 lượt gọi `qwen2.5:3b`, khoảng 5 phút trên PC của track (GPU
dùng chung); judge `qwen2.5:7b` tuỳ chọn khoảng 7 phút trên CPU của PC (cell ghi `cpu=True`, 4 luồng). Laptop GPU 4GB: bỏ
`cpu=True` để Ollama tự chia, chậm hơn nhiều (chưa đo), hoặc đặt `M20_SKIP_7B=1` để bỏ qua. Cần cache `bge-m3.npy` của
module 13 (bài Intermediate 01) cho phần Zalo Legal.

Mở `starter/judge.ipynb`, viết các cell chấm điểm theo mô tả trong notebook:

1. Dán `cohen_kappa`, `calibration_report`, `resolve_swap`, `pairwise_summary` của bài Basic 02.
2. `make_items` (nhãn ứng viên, một nửa đổi sai theo đúng thứ tự gọi RNG đã cho), `judge_messages`, `parse_yes_no`,
   `p_yes` (xác suất "yes" từ `top_logprobs` của Ollama).
3. `expected_calibration_error`, `pick_threshold`.
4. `pair_messages`, `parse_choice`, `judge_pair` (hai lượt, đổi chỗ).

Rồi chạy các cell `explore`: judge pointwise trên 150 câu ghim của module 11, bảng sai theo lớp, biểu đồ độ tin cậy, judge
7B (tuỳ chọn), cặp Zalo Legal (điều luật đúng và hard negative) ở ba điều kiện (gốc, độn chữ vào đoạn sai, độn chữ vào
đoạn đúng). Trả lời các câu ở cuối notebook, rồi làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- Bốn hàm dán từ Basic 02 vẫn đúng.
- `make_items` đúng từng phần tử với công thức RNG; tỉ lệ đổi sai đúng `flip_rate`; `truth` khớp với việc ứng viên trùng gold.
- `judge_messages`, `pair_messages` đúng từng ký tự; `parse_yes_no` và `parse_choice` trả `None` cho mọi câu trả lời không
  đúng định dạng (8 và 11 trường hợp trong test).
- `p_yes` gộp các biến thể viết hoa và dấu cách của "yes"/"no", trả `None` khi không có token nào như vậy.
- `expected_calibration_error` đúng hai ví dụ tính tay, gần 0 trên dữ liệu được hiệu chỉnh hoàn hảo; `pick_threshold`
  chọn ngưỡng nhỏ nhất khi bằng nhau và có thể chọn "không cho qua câu nào".
- `judge_pair` gọi đúng hai lần, lần hai đổi chỗ hai đoạn.
- Notebook lời giải chạy hết với Ollama thật và in đủ các bảng.

## Gợi ý

### Gợi ý 1

Với `make_items`, viết vòng lặp tường minh và gọi `rng.random()` cho **mọi** câu trước khi quyết định, `rng.integers` chỉ
cho câu bị đổi: thứ tự gọi khác đi một lần là cả tập khác. Với `p_yes`, in vài phần tử `top_logprobs` thật ra xem token
trông thế nào (có dấu cách đầu không, viết hoa không).

### Gợi ý 2

`pick_threshold` chỉ cần thử các giá trị điểm có thật (cộng một giá trị lớn hơn mọi điểm), vì accuracy chỉ đổi khi ngưỡng
vượt qua một điểm. Trong `parse_choice`, JSON hợp lệ vẫn có thể sai cấu trúc (list, số thay chuỗi): kiểm kiểu trước khi tra
bảng.
