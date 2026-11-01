# Lời giải: DQN tự viết trên CartPole

## Các hàm

| Hàm | Cài đặt | Điểm dễ sai |
| --- | --- | --- |
| `ReplayBuffer` | mảng cấp sẵn, `ptr = (ptr + 1) % capacity`, `size = min(size + 1, capacity)`, `rng.integers(0, size, B)` | lấy mẫu trong cả `capacity` (dính các dòng 0 chưa ghi); dùng `np.random` toàn cục (không tái lập) |
| `QNetwork` | Linear-ReLU-Linear-ReLU-Linear | |
| `select_action` | `rng.random() < ε` thì ngẫu nhiên, ngược lại `argmax` dưới `no_grad` | ghi graph autograd ở mỗi bước env (chậm, tốn bộ nhớ) |
| `td_targets` | `@torch.no_grad()`, `r + γ(1 − d)·max Q_target(s')`; Double: `gather` Q_target tại `argmax Q_online(s')` | dùng mạng online cho max; quên mặt nạ `terminated` |
| `dqn_loss` | `gather(1, a.unsqueeze(1)).squeeze(1)`, `smooth_l1_loss` | quên `squeeze`: `(B, 1)` trừ `(B,)` thành `(B, B)`, loss vẫn là một số |
| `train_dqn` | 5 bước của notebook; soft update `lerp_` sau mỗi `opt.step()` | lưu `terminated or truncated`; `best_state` không deepcopy |

Test `EndlessReward` (một observation, reward 1 mỗi bước, cắt sau 10 bước, $$\gamma = 0.9$$) là trụ cột: Q đúng là $$1/(1-\gamma) = 10$$.
Lưu cờ `truncated` vào buffer thì bước cuối có target 1, Q hội tụ về một số thấp hơn hẳn. Cùng env đó phân biệt được target network
đứng yên (Q dừng gần $$1 + 0.9\,Q_{\text{ban đầu}} \approx 1$$) với target network theo kịp mạng online (Q tới 10): một bản cài quên chép hay
quên `lerp_` cho kết quả sai rõ ràng chỉ sau 600 bước.

## Kết quả của notebook lời giải

CPU 4 luồng (Xeon E5-2696 v3, máy dùng chung), 50 000 bước env mỗi lần, khoảng 13 phút cả cell. Policy ngẫu nhiên: 21.4 ± 9.8 trên 100
episode (seed 10 000..10 099).

Eval greedy 10 episode mỗi 5 000 bước (seed 100 000..100 009):

| Cấu hình | seed 0 | seed 1 | seed 2 |
| --- | --- | --- | --- |
| Soft update $$\tau = 0.005$$ | 218, 244, 242, 141, 142, 444, 237, 429, 500, 500 | 188, 214, 170, 93, 100, 109, 113, 116, 140, 485 | 140, 221, 208, 165, 177, 194, 206, 237, 392, 500 |
| Hard update mỗi 500 bước | 414, 234, 305, 297, 302, 365, 133, 165, 158, 113 | 232, 267, 226, 220, 500, 112, 114, 115, 111, 107 | 171, 275, 251, 246, 242, 248, 174, 228, 169, 260 |
| Không target network | 9 ở mọi mốc | 9 ở mọi mốc | 9 ở mọi mốc |

Đánh giá cuối trên 20 episode (seed 10 000..10 019), và Q dự đoán so với return chiết khấu thật ở trạng thái đầu:

| Cấu hình | Trọng số cuối | Checkpoint tốt nhất | $$\max_a Q(s_0, a)$$ | Return chiết khấu thật | Số episode / 50k bước |
| --- | --- | --- | --- | --- | --- |
| Soft update | 500.0 / 488.4 / 500.0 | 500.0 / 488.4 / 500.0 | 98.7 / 97.9 / 96.6 | 99.3 / 99.0 / 99.3 | 352 / 508 / 378 |
| Hard update 500 | 111.7 / 108.3 / 239.3 | 444.3 / 500.0 / 281.4 | 65.5 / 69.7 / 64.7 | 67.4 / 66.3 / 90.1 | 380 / 463 / 340 |
| Không target | 9.4 / 9.4 / 9.4 | 9.4 / 9.4 / 9.4 | 1 319 539 / 1 185 389 / 1 271 744 | 9.0 / 9.0 / 9.0 | 4 873 / 4 881 / 4 882 |

Đọc kết quả:

- Không có target network: Q tăng tới hơn một triệu (giá trị thật tối đa khoảng 99) và policy sụp về một action ngay từ lần eval đầu,
  khoảng 10 bước mỗi episode. Đây là deadly triad đo được.
- Hard update chạm 500 rồi rơi về khoảng 110 ngay ở mốc sau (seed 1: 500 ở 25 000 bước, 112 ở 30 000): catastrophic forgetting. Checkpoint
  tốt nhất cứu được phần lớn, nhưng seed 2 không bao giờ vượt 300 ở các mốc eval.
- Soft update học chậm (seed 1 chỉ vượt 400 ở mốc cuối) nhưng không sụp, và Q dự đoán khớp return thật trong vòng 3%. Target trôi chậm
  và đều tốt hơn target nhảy bậc mỗi 500 bước ở thiết lập này. Với 3 seed, đó là kết luận về **thiết lập này**, không phải định luật.

## Bẫy thường gặp

- `best_state = q_net.state_dict()` không sao chép: "bản tốt nhất" luôn là trọng số hiện tại. Test kiểm `data_ptr` khác nhau.
- Đánh giá bằng ε-greedy của lúc train, hoặc trên chính các episode train.
- Đổi nhiều siêu tham số cùng lúc rồi kết luận về target network: cùng code với lr $$10^{-3}$$, học mỗi 4 bước, hard update thì kết quả rất
  khác (mục 4 lý thuyết). So từng thay đổi một, trên nhiều seed.
