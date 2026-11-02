# Lời giải: objective của GRPO

## Cách làm

**Advantage theo nhóm.** `rewards.view(-1, G)` cho một hàng mỗi prompt. Trừ trung bình hàng; nếu `scale` thì chia cho
`std(dim=1) + eps` (Bessel, giống `nanstd` của TRL). Nhóm mà mọi reward bằng nhau có tử số bằng 0 chính xác, `eps` chỉ
để mẫu số khác 0: kết quả 0, không `nan`. Đó là phần lớn nhóm khi câu hỏi quá dễ (mọi lời giải đúng) hoặc quá khó (mọi
lời giải sai): những prompt đó không đóng góp gradient, và tỉ lệ nhóm như vậy (`frac_reward_zero_std` trong TRL) là một
chỉ số phải theo dõi.

**KL k3.** Với $$r = \pi_{\text{ref}}(o_t)/\pi_\theta(o_t)$$ và $$o_t \sim \pi_\theta$$:

$$
k_3 = r - \log r - 1 \;\ge 0, \qquad \mathbb E_{o_t \sim \pi_\theta}[k_3] = \mathbb E[r] - 1 + \mathrm{KL}(\pi_\theta\|\pi_{\text{ref}}) = \mathrm{KL}(\pi_\theta\|\pi_{\text{ref}})
$$

vì $$\mathbb E_{\pi_\theta}[r] = \sum \pi_{\text{ref}} = 1$$. Ước lượng thô $$k_1 = -\log r$$ cũng không chệch nhưng âm được ở
từng token và phương sai lớn; k3 không âm và phương sai nhỏ khi hai policy gần nhau (Schulman, "Approximating KL
divergence", 2020). Test lấy mẫu 400 000 token từ một phân phối 3 lớp và thấy k3 trung bình khớp KL(policy ‖ ref) trong
3%, còn chiều ngược lại lệch xa: đổi chỗ `logp` và `ref_logp` là lỗi cài đặt hay gặp, và nó **vẫn không âm**, nên chỉ
thí nghiệm Monte Carlo mới bắt được.

**Clipped objective.** `torch.min(ratio * A, clamp(ratio, 1 - eps_low, 1 + eps_high) * A)` với `A` broadcast theo
token. Bảng 6 ô của test là bảng ở mục 6 module 07: phép cắt chỉ tắt gradient khi nó đẩy policy **đi xa hơn theo hướng
có lợi** (ratio đã trên 1.2 với A dương, hoặc đã dưới 0.8 với A âm). `eps_high > eps_low` (DAPO "clip-higher") cho token
có A dương tăng xác suất nhiều hơn trước khi bị cắt, giúp token xác suất thấp (thường là token "khám phá") không bị khoá.

**Gộp loss.** Loss theo token là `-surrogate + beta * k3`. Hai cách gộp khác nhau ở **trọng số của mỗi token**:

| Cách | Công thức | Trọng số một token của chuỗi dài L |
| --- | --- | --- |
| `"sequence"` (GRPO gốc) | $$\frac1B\sum_i \frac{1}{\lvert o_i\rvert}\sum_t \ell_{i,t}$$ | $$1/(B L)$$: chuỗi dài, token nhẹ |
| `"token"` (DAPO) | $$\sum_{i,t} \ell_{i,t} \big/ \sum_i \lvert o_i\rvert$$ | như nhau mọi token |

Với `"sequence"`, một lời giải **sai và dài** bị phạt nhẹ trên từng token hơn một lời giải sai và ngắn; Dr. GRPO (Liu
và cộng sự, 2025) chỉ ra đây là một nguồn khiến độ dài câu trả lời sai tăng dần khi train. Test kiểm điều này qua
gradient: khi policy trùng policy cũ, gradient theo log-prob của mỗi token là $$-\hat A_i / (|o_i| B)$$.

`clip_frac` đếm token bị cắt **theo hướng làm mất gradient**, chỉ trên token hợp lệ, giống `clip_ratio/low_mean`,
`clip_ratio/high_mean` của TRL. Với `num_iterations = 1` (mỗi batch chỉ một bước gradient, mặc định của TRL), ratio luôn
bằng 1 ở bước đó và `clip_frac` bằng 0: phép cắt chỉ có tác dụng khi dùng lại một batch nhiều bước.

## Bẫy thường gặp

- Chuẩn hoá trên cả batch thay vì từng nhóm: câu dễ và câu khó trộn lẫn, advantage đo độ khó của câu chứ không đo lời
  giải nào tốt hơn.
- Quên `eps`: nhóm reward bằng nhau cho `0/0 = nan`, cả loss thành `nan`.
- `max` thay cho `min`: objective thành cận trên lạc quan, phép cắt không còn giữ policy gần policy cũ.
- Lấy trung bình trên cả padding: token pad có log-prob rác kéo loss đi; lỗi này không báo gì, chỉ làm train kém đi.
