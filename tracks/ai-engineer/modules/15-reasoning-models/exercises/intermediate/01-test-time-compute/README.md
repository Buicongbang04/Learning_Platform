---
title: Test-time compute trên GSM8K - CoT, self-consistency, best-of-N
level: intermediate
services: []
files:
  - path: starter/ttc.ipynb
    note: 3 hàm TODO, 7 hàm dán từ Basic 01 và 02
  - path: tests/test_ttc.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py gsm8k
  - ollama pull qwen2.5:3b
  - uv run jupyter lab tracks/ai-engineer/modules/15-reasoning-models/exercises/intermediate/01-test-time-compute/starter/ttc.ipynb
  - uv run pytest tracks/ai-engineer/modules/15-reasoning-models/exercises/intermediate/01-test-time-compute -q
---

## Mục tiêu

Đo bằng số hai cách tiêu thêm compute lúc inference trên cùng 200 câu GSM8K: cho model viết lời giải (chain-of-thought)
thay vì trả lời thẳng, và sinh nhiều lời giải rồi gộp (self-consistency, best-of-N). Kết quả là một bảng có khoảng tin
cậy và một đường cong accuracy theo số token, thứ bạn cần để trả lời câu hỏi thật của sản phẩm: tiêu thêm token ở đâu
thì đáng.

## Đề bài

**Phần cứng:** GPU 4GB · ~90 phút

Thời gian trên là thời gian làm bài. Máy chạy riêng khoảng 40 phút trên PC của track (RTX 3060, dùng chung): phần Ollama
khoảng 400 lượt gọi `qwen2.5:3b` (khoảng 19 phút), phần Transformers 3 400 lời giải của `Qwen2.5-0.5B-Instruct` (khoảng
22 phút). Trên GPU 4GB của laptop phần Transformers chậm hơn (chưa đo). Phần 2 chạy bằng kernel `ai-gpu`; chỉ có CPU thì
kernel gốc chạy bản thu nhỏ (8 câu, 4 lời giải mỗi câu) để kiểm code, và bạn đọc kết quả 200 câu trong lời giải. Đọc mục
1, 2 lý thuyết.

Mở `starter/ttc.ipynb`. Trong cell chấm điểm:

1. Dán `normalize_number`, `extract_answer` (và hàm phụ) từ Basic 01; `majority_vote`, `best_of_n`, `pass_at_k`,
   `maj_at_k`, `coverage_at_k` (và `weighted_vote` nếu bạn dùng nó) từ Basic 02.
2. `build_messages(question, mode)`: `"direct"` hoặc `"cot"`, system là hằng `SYSTEM_DIRECT` / `SYSTEM_COT` có sẵn.
3. `scaling_table(answers, tokens, logprobs, golds, ks)`: một dòng mỗi `k` với `maj`, `pass`, `bon_logprob`, `tokens`
   (định nghĩa từng cột trong notebook).
4. `paired_bootstrap(correct_a, correct_b, n_boot, seed)`: hiệu accuracy B − A và khoảng tin cậy 95% theo cặp.

Rồi chạy các cell `explore`: direct so với CoT với `qwen2.5:3b` (`temperature` 0, `seed` 0), rồi greedy và 16 lời giải
lấy mẫu mỗi câu với `Qwen2.5-0.5B-Instruct`, bảng và đường cong theo token. Sau đó làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- Các hàm dán qua kiểm tra nhanh (phẩy hàng nghìn, `\boxed`, khoảng `3-4`, hoà phiếu, pass@k).
- `build_messages` đúng hai vai, đúng hằng system, câu hỏi giữ nguyên; mode lạ thì `ValueError`.
- `scaling_table` đúng cột và giá trị trên ví dụ tính tay (khối liên tiếp, bỏ phần dư, best-of-N theo log-prob, token
  của khối).
- `paired_bootstrap`: hai cột giống nhau cho `(0, 0, 0)`; cùng seed cùng kết quả; độ rộng khoảng khớp lý thuyết của hiệu
  theo cặp trong 20% và hẹp hơn hẳn khi so hai cột độc lập.
- Các cell `explore` chạy hết, in bảng direct/CoT và bảng scaling.

## Gợi ý

### Gợi ý 1

`scaling_table` dùng lại đúng các hàm đã dán: cột `maj` và `pass` là một lời gọi mỗi cột. Cột `bon_logprob` và `tokens`
cần duyệt khối giống hệt cách `maj_at_k` duyệt, nên viết vòng khối một lần cho cả hai cột. Kiểm bằng ví dụ trong test
trước khi chạy model.

### Gợi ý 2

Bootstrap viết được không cần vòng lặp Python nếu bạn sinh một lần cả ma trận chỉ số lấy mẫu lại. Điều quyết định là
"theo cặp": mỗi lần lấy mẫu lại, hai cột phải dùng **cùng** các câu.
