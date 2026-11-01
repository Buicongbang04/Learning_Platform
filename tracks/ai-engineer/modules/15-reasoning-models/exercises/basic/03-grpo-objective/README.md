---
title: Objective của GRPO tự viết bằng PyTorch
level: basic
services: []
files:
  - path: starter/grpo.py
    note: 4 hàm TODO
  - path: tests/test_grpo.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/15-reasoning-models/exercises/basic/03-grpo-objective -q
---

## Mục tiêu

GRPO là PPO bỏ critic: advantage lấy từ chính nhóm lời giải của cùng một câu hỏi. Bài này viết bốn mảnh toán của nó
trên tensor nhỏ, kiểm từng mảnh bằng ví dụ tính tay và bằng gradient: advantage theo nhóm (kể cả nhóm mọi lời giải cùng
reward), ước lượng KL k3, clipped objective, và hai cách gộp loss theo token. Bài Intermediate 02 ghép chúng vào một
vòng train thật trên Qwen2.5-0.5B.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Đọc mục 4 lý thuyết (và mục 6 module 07 về PPO). Trong `starter/grpo.py`:

1. `group_advantages(rewards, group_size, scale=True, eps=1e-4)`: `rewards` shape `(B * G,)`, mỗi `G` phần tử liên tiếp
   là một nhóm (cùng prompt). Trả advantage cùng shape: reward trừ trung bình **của nhóm đó**; nếu `scale` thì chia
   thêm cho (độ lệch chuẩn của nhóm, có hiệu chỉnh Bessel, cộng `eps`). Nhóm mọi reward bằng nhau phải cho 0, không `nan`.
   `group_size < 2` hoặc không chia hết thì `ValueError`.
2. `kl_k3(logp, ref_logp)`: ước lượng k3 theo từng token của $$\mathrm{KL}(\pi_\theta \,\|\, \pi_{\text{ref}})$$, với token đã
   lấy mẫu từ $$\pi_\theta$$ (công thức ở mục 4 lý thuyết).
3. `clipped_surrogate(logp, old_logp, advantages, eps_low=0.2, eps_high=None)`: objective PPO-clip theo token, shape
   `(B, T)`; `advantages` shape `(B,)` dùng chung cho mọi token của chuỗi; `eps_high=None` nghĩa là bằng `eps_low`
   (cắt đối xứng), khác `None` thì cắt trên ở `1 + eps_high` (DAPO "clip-higher").
4. `grpo_loss(logp, old_logp, ref_logp, advantages, mask, beta=0.04, eps_low=0.2, eps_high=None, aggregation="sequence")`:
   loss theo token là `-(clipped objective) + beta * k3` (bỏ phần KL khi `beta == 0` hoặc `ref_logp is None`), rồi gộp
   **chỉ trên token có `mask = 1`**:
   - `"sequence"`: trung bình trong từng chuỗi, rồi trung bình các chuỗi (GRPO gốc);
   - `"token"`: tổng mọi token hợp lệ chia tổng số token hợp lệ (DAPO); giá trị khác thì `ValueError`.

   Trả thêm `{"kl": ..., "clip_frac": ...}` dạng `float`: KL k3 trung bình trên token hợp lệ (0.0 khi không tính KL), và
   tỉ lệ token hợp lệ bị cắt **theo hướng làm mất gradient** (ratio dưới `1 - eps_low` khi advantage âm, hoặc trên
   `1 + eps_high` khi advantage dương).

## Tiêu chí đạt

- Advantage đúng ví dụ tính tay, các nhóm độc lập nhau, nhóm reward bằng nhau cho 0, `eps` và `scale` có tác dụng.
- `kl_k3` bằng 0 khi hai policy trùng, không âm ở từng token, và trung bình trên 400 000 token lấy mẫu từ policy khớp
  KL(policy ‖ ref) chính xác trong 3% (và không khớp chiều ngược lại).
- Bảng 6 ô của clipped objective (dấu advantage × ratio) đúng giá trị và đúng chỗ gradient bằng 0; cắt bất đối xứng đúng.
- `grpo_loss` khớp tính tay với cả hai cách gộp và hai giá trị `beta`; token ngoài mask không ảnh hưởng; khi policy
  trùng policy cũ thì gradient theo log-prob là $$-\hat A_i / (|o_i| \cdot B)$$; thống kê đúng.

## Gợi ý

### Gợi ý 1

`rewards.view(-1, group_size)` cho ma trận một hàng một nhóm; `mean`/`std` với `dim=1, keepdim=True` để trừ, chia theo
hàng. `torch.std` mặc định đã có hiệu chỉnh Bessel. Trong `clipped_surrogate`, `advantages.unsqueeze(-1)` để nhân với
ma trận `(B, T)`.

### Gợi ý 2

Đừng lọc token bằng chỉ số boolean rồi mới tính: nhân với `mask` rồi cộng giữ nguyên shape, dễ gộp theo hai cách. Kiểm
`clip_frac` bằng tay trên một ví dụ hai chuỗi trước khi chạy test, và nhớ rằng token bị cắt nhưng nằm ngoài mask không
được đếm.
