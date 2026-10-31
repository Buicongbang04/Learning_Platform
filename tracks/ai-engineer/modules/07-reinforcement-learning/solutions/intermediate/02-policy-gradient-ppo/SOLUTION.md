# Lời giải: REINFORCE, baseline và PPO trên CartPole

## Các hàm

| Hàm | Cài đặt | Điểm dễ sai |
| --- | --- | --- |
| `ActorCritic` | hai `Sequential` Linear-Tanh-Linear-Tanh-Linear, `layer_init` orthogonal, actor head gain 0.01 | chung thân cho actor và critic (được, nhưng gradient của value loss kéo cả đặc trưng của actor; cần cân `vf_coef`); quên `squeeze(-1)` ở `value` |
| `reinforce_loss` | `-(logp * (G - b).detach()).mean()` | thiếu `detach`: policy loss kéo cả critic |
| `ppo_policy_loss` | `ρ = exp(new − old)`, `−min(ρA, clip(ρ)A).mean()`; `clipfrac`, `approx_kl` dưới `no_grad` | `max` thay `min`; đảo `new − old`; KL ngây thơ `mean(−log ρ)` (nhiễu, có thể âm) |
| `train_reinforce` | 8 episode lấy mẫu, reward-to-go, một bước Adam mỗi batch | lấy action bằng `argmax`; tính $$G$$ không chiết khấu |
| `collect_rollout` | xem Gợi ý 2 của đề | bootstrap từ observation sau reset; không reset return dở dang |
| `ppo_update` | K epoch × minibatch, chuẩn hoá advantage trong minibatch, `pl + 0.5·½MSE − 0.01·H` | dấu entropy; chuẩn hoá trước khi chia minibatch; quên clip norm |
| `train_ppo` | lr giảm tuyến tính, `collect_rollout` → `gae` → làm phẳng → `ppo_update` | critic học advantage thay vì `returns` |

`approx_kl` dùng ước lượng $$(\rho - 1) - \log\rho$$ (Schulman, "Approximating KL divergence", 2020): không âm với mọi mẫu và ít nhiễu
hơn $$-\log\rho$$. Test kiểm đúng công thức này.

## Kết quả của notebook lời giải

CartPole-v1, 150 000 bước env, CPU 4 luồng (Xeon E5-2696 v3, máy dùng chung). Return trung bình của các episode kết thúc trong cửa sổ
10 000 bước trước mốc, seed 0 / 1 / 2:

| Thuật toán | 50k | 100k | 150k | Greedy cuối, 20 episode | Lấy mẫu cuối, 20 episode | Thời gian / seed |
| --- | --- | --- | --- | --- | --- | --- |
| REINFORCE | 218 / 206 / 244 | 335 / 379 / 295 | 362 / 408 / 446 | 496.5 / 500 / 500 | 315.6 / 404.7 / 427.2 | 94 s |
| REINFORCE + baseline | 270 / 231 / 187 | 387 / 410 / 439 | 417 / 431 / 472 | 495.1 / 500 / 500 | 454.6 / 441.6 / 465.2 | 95 s |
| PPO | 288 / 377 / 286 | 416 / 374 / 420 | 463 / 450 / 488 | 500 / 500 / 500 | 483.8 / 449.1 / 495.6 | 37 s |

Đọc kết quả:

- Ở mốc 100k và 150k, baseline cho return cao hơn REINFORCE trần ở cả 3 seed, và policy lấy mẫu cuối cùng ổn định hơn hẳn (442 tới
  465 so với 316 tới 427). Ở 50k thì chưa rõ: chênh lệch nằm trong dao động giữa seed. Với 3 seed, chỉ kết luận được hướng, không
  kết luận được độ lớn.
- PPO dẫn ở mọi mốc và nhanh hơn 2.5 lần wall-clock: một forward cho 4 env cùng lúc, và mỗi mẫu được dùng 4 epoch.
- Policy greedy của cả ba đều gần 500: CartPole dễ tới mức "lấy argmax" che hết khác biệt. Con số phân biệt được thuật toán là
  return **lúc train** và return của policy **lấy mẫu**.
- Chẩn đoán PPO (seed 0): approx KL lớn nhất 0.0066, clip fraction lớn nhất 0.086, entropy cuối 0.54 (ban đầu 0.693). Cả hai số đầu
  nằm sâu trong vùng an toàn: với CartPole, lr $$2.5\times10^{-4}$$ còn thận trọng, tăng lr là cách đầu tiên để nhanh hơn.

## Bẫy thường gặp

- Lỗi nào cũng "vẫn học được CartPole": một bản PPO đổi `min` thành `max`, quên `final_obs`, hay sai dấu entropy vẫn có thể lên vài
  trăm điểm. Chỉ test so với cài đặt tham chiếu trên dữ liệu nhỏ mới bắt được chắc chắn (bài Advanced 02 xoay quanh đúng điều này).
- `value` trả `(B, 1)`: `(v - returns) ** 2` broadcasting thành `(B, B)`, critic học trung bình của mọi return.
- Chuẩn hoá advantage bằng `std` lệch (numpy mặc định) thay vì `torch.std` không lệch: khác 4% với minibatch 12 mẫu của test.
