---
title: Tự viết DPO loss và một bước train với reference đóng băng
level: basic
services: []
files:
  - path: starter/dpo.py
    note: 3 hàm TODO
  - path: tests/test_dpo.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/14-fine-tuning-llm/exercises/basic/03-dpo-loss -q
---

## Mục tiêu

Viết lõi của DPO bằng PyTorch: log-xác suất của một câu trả lời dưới model, loss trên hiệu log-ratio so với reference,
và một bước train mà reference không bao giờ bị đổi. Làm xong bạn đọc được các cột `rewards/chosen`, `rewards/margins`,
`rewards/accuracies` mà `DPOTrainer` của TRL in ra và biết chúng đến từ đâu.

## Đề bài

**Phần cứng:** CPU · ~45 phút

Đọc mục 6 phần lý thuyết (và mục 7 module 07 cho nghiệm đóng của RLHF). Trong `starter/dpo.py`:

1. `sequence_logps(logits, labels) -> Tensor`: `logits` shape `(B, T, V)`, `labels` shape `(B, T)` theo quy ước của bài
   Basic 02 (chưa dịch, `-100` ở chỗ không tính). Trả tổng log-xác suất (theo `log_softmax`, tính ở `float32`) của mọi
   token có label trong mỗi chuỗi, shape `(B,)`. Chuỗi không có token nào có label cho 0.
2. `dpo_loss(policy_chosen, policy_rejected, ref_chosen, ref_rejected, beta=0.1)`: bốn tensor shape `(B,)` là tổng log-prob
   của câu được chọn và câu bị loại dưới policy và reference. Trả bộ ba `(loss, chosen_rewards, rejected_rewards)`:
   `loss` là trung bình theo batch của loss DPO ở mục 6 lý thuyết; reward ngầm của mỗi câu là
   $$\beta\,\big(\log\pi_\theta - \log\pi_{\text{ref}}\big)$$, trả về **không** mang gradient (chỉ để log).
3. `dpo_step(policy, reference, batch, beta, optimizer) -> dict`: `batch` có `chosen_input_ids`, `chosen_attention_mask`,
   `chosen_labels` và ba khoá `rejected_...` tương ứng. Tính log-prob của reference **không** tính gradient, của policy có
   gradient, loss, một bước `optimizer` (zero grad, backward, step). Trả `{"loss", "reward_margin", "reward_accuracy"}`
   kiểu `float`: margin là trung bình `chosen_rewards - rejected_rewards`, accuracy là tỉ lệ cặp có margin dương.

## Tiêu chí đạt

- `sequence_logps` khớp vòng lặp tính tay tới `1e-5`; logits ở vị trí không dự đoán token có label không ảnh hưởng.
- Policy trùng reference thì loss đúng bằng $$\log 2$$, reward bằng 0.
- Loss khớp công thức với hai giá trị $$\beta$$; đảo chosen và rejected thì loss vượt $$\log 2$$; bỏ reference thì sai.
- Gradient đẩy log-prob của chosen lên, của rejected xuống; reward trả về không mang gradient.
- Trên một Qwen2 tí hon: bước đầu loss bằng $$\log 2$$, sau 12 bước loss dưới 0.3 và accuracy 1.0; reference không đổi
  một bit và không có `.grad`.

## Gợi ý

### Gợi ý 1

Bắt đầu từ quy ước của bài Basic 02: logits ở vị trí `t - 1` dự đoán token ở vị trí `t`. `torch.gather` trên chiều từ vựng
lấy log-prob của đúng token label; label `-100` không phải chỉ số hợp lệ, thay tạm bằng 0 trước khi `gather` rồi nhân với
mask. Viết loss bằng `F.logsigmoid` thay vì `log(sigmoid(...))` để không tràn số khi margin lớn.

### Gợi ý 2

Tự kiểm bằng tay trường hợp policy trùng reference: hai log-ratio bằng 0, sigmoid của 0 là 0.5. Một reference "đóng
băng" cần hai điều: không nằm trong optimizer, **và** không tạo đồ thị tính gradient (nếu không, `backward` vẫn ghi
`.grad` vào tham số của nó và tốn bộ nhớ như một model thứ hai đang train).
