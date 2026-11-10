---
title: Vòng GRPO tự viết trên Qwen2.5-0.5B với GSM8K
level: intermediate
services: []
files:
  - path: starter/grpo_loop.ipynb
    note: 2 hàm TODO, dán answers.py (Basic 01) và grpo.py (Basic 03)
  - path: tests/test_grpo_loop.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py gsm8k
  - uv run jupyter lab tracks/ai-engineer/modules/15-reasoning-models/exercises/intermediate/02-grpo-from-scratch/starter/grpo_loop.ipynb
  - uv run pytest tracks/ai-engineer/modules/15-reasoning-models/exercises/intermediate/02-grpo-from-scratch -q
---

## Mục tiêu

Ghép các mảnh của bài Basic 01 (reward kiểm được) và Basic 03 (objective GRPO) thành một vòng train RL thật trên một
LLM, không qua thư viện: sinh nhóm lời giải, chấm, advantage theo nhóm, log-prob của policy cũ và reference (bằng cách
tắt LoRA), clipped objective có KL. Bạn sẽ thấy tận mắt GRPO tiêu thời gian vào đâu, log những gì để biết nó có đang học
không, và vì sao "reward tăng" chưa phải là "model giỏi hơn".

## Đề bài

**Phần cứng:** GPU 4GB · ~120 phút

Thời gian trên là thời gian làm bài. Notebook lời giải train 30 bước (8 câu × 8 lời giải mỗi bước) và đo trước/sau trên
200 câu test; số phút và VRAM đỉnh đo trên PC của track ghi ở `SOLUTION.md` (cấu hình chọn để vừa GPU 4GB: micro-batch 2,
gradient checkpointing, logits chỉ cho phần completion). Kernel CPU chạy bản thu nhỏ (2 bước, 6 câu đo) để kiểm code.
Đọc mục 4 lý thuyết. Chạy bằng kernel `ai-gpu`.

Mở `starter/grpo_loop.ipynb`:

1. Dán toàn bộ `answers.py` của bài Basic 01 và `grpo.py` của bài Basic 03 vào hai cell có sẵn.
2. `completion_mask(completion_ids, stop_ids)`: 1 tới và gồm token dừng đầu tiên, 0 sau đó.
3. `completion_logprobs(model, prompt_ids, prompt_mask, completion_ids, completion_mask, temperature=1.0)`: log-prob từng
   token completion, một lượt forward với `logits_to_keep`, chia logits cho `temperature`, 0 ngoài mask, giữ gradient.

Rồi chạy các cell `explore`: đo model gốc, train, đo lại, vẽ đường cong reward, độ dài, tỉ lệ nhóm std = 0, KL, clip
fraction. Sau đó làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- Các hàm dán qua kiểm tra nhanh (advantage nhóm, clip, k3, reward `\boxed{}`).
- `completion_mask` giữ token dừng đầu tiên, bỏ mọi thứ sau; hàng không có token dừng là 1 cả hàng.
- `completion_logprobs` khớp lượt forward không pad của từng chuỗi (model Qwen2 tí hon khởi tạo ngẫu nhiên, prompt pad
  trái), trả 0 ngoài mask, có gradient, gọi model đúng một lần với `logits_to_keep = C + 1`, đúng khi `temperature` khác 1.
- Các cell `explore` chạy hết và in bảng trước/sau cùng đường cong.

## Gợi ý

### Gợi ý 1

`completion_mask`: tổng tích luỹ (`cumsum`) của "là token dừng" theo chiều thời gian cho biết token dừng đã xuất hiện ở
**trước** vị trí hiện tại chưa. Với log-prob, viết một bản chậm (vòng lặp từng chuỗi, không pad) trước để có số so, như
test làm.

### Gợi ý 2

Khi ghép prompt pad trái với completion, completion luôn nằm ở C vị trí cuối, nên `logits_to_keep = C + 1` cho đúng các
logits cần: logits ở vị trí `i` dự đoán token `i + 1`, bỏ logits cuối cùng. Log-softmax trên cả vocab ở fp32 tốn bộ nhớ:
`gather` logit của token cần rồi trừ `logsumexp` là đủ.
