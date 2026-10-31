---
title: Return, n-step return và GAE cho rollout buffer
level: basic
services: []
files:
  - path: starter/returns.py
    note: 4 hàm TODO
  - path: tests/test_returns.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/07-reinforcement-learning/exercises/basic/03-returns-gae -q
---

## Mục tiêu

Mọi thuật toán policy gradient (REINFORCE, A2C, PPO, cả PPO trong RLHF) đều cần biến một rollout buffer thành "action này tốt
hơn kỳ vọng bao nhiêu". Bạn tự viết reward-to-go, n-step return, GAE(λ) và chuẩn hoá advantage, đúng cả ở chỗ hay sai nhất:
ranh giới episode, `terminated` khác `truncated`, và buffer nhiều env song song. Hàm `gae` của bài này dùng lại ở Intermediate 02.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Đọc mục 1 (`terminated`/`truncated`) và mục 5 phần lý thuyết (GAE). Quy ước buffer ghi ở đầu `starter/returns.py`: mỗi bước
$$t$$ có `rewards[t]`, `values[t]` $$= V(s_t)$$, `next_values[t]` $$= V(s_{t+1})$$ (observation thật ngay sau bước $$t$$, kể cả khi
episode bị cắt), `terminated[t]`, `truncated[t]`. Mảng shape `(T,)` hoặc `(T, N)` cho N env. Chỉ dùng numpy:

1. `reward_to_go(rewards, gamma)`: $$G_t = \sum_{k \ge 0}\gamma^k r_{t+k}$$ cho một episode.
2. `n_step_returns(rewards, next_values, terminated, truncated, gamma, n)`:
   $$G_t^{(n)} = \sum_{k=0}^{m-1}\gamma^k r_{t+k} + \gamma^m V(s_{t+m})$$ với $$m \le n$$ là số bước tới chỗ dừng (đủ n bước, hết
   episode, hoặc hết buffer); không có số hạng bootstrap nếu chỗ dừng là `terminated`.
3. `gae(rewards, values, next_values, terminated, truncated, gamma, lam)`: trả `(advantages, returns)`,
   $$\hat A_t = \sum_k (\gamma\lambda)^k \delta_{t+k}$$ trong cùng episode, với
   $$\delta_t = r_t + \gamma(1 - \text{terminated}_t)\,V(s_{t+1}) - V(s_t)$$; `returns = advantages + values`. Một vòng lặp
   ngược, không vòng lồng.
4. `normalize_advantages(adv, eps)`: trừ mean, chia (std + eps).

## Tiêu chí đạt

- `gae` với $$\lambda = 0$$ là TD error; với $$\lambda = 1$$ và critic nhất quán, `returns` bằng reward-to-go Monte Carlo.
- `gae` khớp định nghĩa tổng $$\sum_k(\gamma\lambda)^k\delta_{t+k}$$ trên buffer có cả `terminated` và `truncated`; reward của
  episode sau không chảy về episode trước; `terminated` không bootstrap còn `truncated` thì có.
- `n_step_returns` với n = 1 là TD target, n lớn là Monte Carlo, đúng từng số khi n = 3, dừng đúng ở ranh giới episode.
- Buffer `(T, N)` cho kết quả bằng chạy từng cột riêng.
- `normalize_advantages` cho mean 0, std 1, giữ thứ tự, không chia cho 0 khi advantage hằng.

## Gợi ý

### Gợi ý 1

Viết `gae` bằng đệ quy ngược $$\hat A_t = \delta_t + \gamma\lambda\,(\ldots)\,\hat A_{t+1}$$. Có hai "công tắc" khác nhau: một
cái quyết định $$\delta_t$$ có bootstrap không (chỉ `terminated`), một cái quyết định đệ quy có nối sang bước sau không (hết episode
vì bất kỳ lý do gì). Nhầm hai công tắc là lỗi phổ biến nhất của code PPO tự viết.

### Gợi ý 2

Dùng phép nhân với mặt nạ `(1 - cờ)` thay vì `if`, code tự chạy cho cả `(T,)` lẫn `(T, N)`. Với `n_step_returns`, giữ một mặt
nạ "còn sống" cho từng env: khi một env đã dừng thì không cộng reward hay bootstrap thêm cho nó.
