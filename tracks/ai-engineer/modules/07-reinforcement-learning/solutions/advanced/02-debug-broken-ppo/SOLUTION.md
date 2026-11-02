# Hướng làm: gỡ lỗi PPO hỏng mà không báo lỗi

Bài không có code lời giải: bản sửa chỉ là 5 dòng, giá trị nằm ở quy trình khoanh vùng và `BUGS.md`. Dưới đây là 5 bug, triệu chứng đo
được của **từng bug khi chỉ còn mình nó** (4 bug kia đã sửa), cách phát hiện và cách sửa. Số liệu: CartPole-v1, `train_ppo` mặc định
(150 000 bước, 4 env × 128 bước), 3 seed, CPU 4 luồng, ngày 2026-11-01.

## Năm bug

Return trung bình của episode kết thúc trong cửa sổ 10 000 bước trước mốc 150 000 (như log lúc train), policy greedy cuối trên 20 episode
cố định (seed 10 000..10 019), và chẩn đoán lớn nhất trong cả lần train; seed 0 / 1 / 2:

| # | Bug | Ở đâu | Return lúc train ở 150k | Greedy cuối | approx KL lớn nhất | Entropy cuối |
| --- | --- | --- | --- | --- | --- | --- |
| | Đã sửa cả 5 | | 463 / 450 / 488 | 500 / 500 / 500 | 0.007 / 0.006 / 0.009 | 0.540 / 0.532 / 0.534 |
| | Đủ 5 bug (notebook gốc) | | 36 197 / 36 157 / 36 155 (log sai) | 448.8 / 386.8 / 500 | 0.028 / 0.022 / 0.027 | 0.401 / 0.473 / 0.500 |
| 1 | `value` trả `(B, 1)` | `ActorCritic.value` | 182 / 260 / 217 | 204.5 / 426.7 / 338.8 | 0.004 / 0.013 / 0.007 | 0.511 / 0.530 / 0.475 |
| 2 | `truncated` coi là kết thúc trong $$\delta_t$$ | `gae` | 218 / 450 / 497 | 277.6 / 500 / 500 | 0.005 / 0.007 / 0.007 | 0.521 / 0.521 / 0.524 |
| 3 | `max` thay `min` | `ppo_policy_loss` | 320 / 472 / 475 | 445.8 / 500 / 500 | 0.004 / **0.044** / 0.017 | 0.523 / 0.552 / 0.519 |
| 4 | dấu entropy | `ppo_update` | 229 / 442 / 476 | 301.9 / 500 / 495.3 | 0.009 / 0.007 / 0.008 | 0.437 / 0.497 / 0.495 |
| 5 | return không reset | `collect_rollout` | (chỉ sai số log) | không đổi | không đổi | không đổi |

Mỗi dòng 1–4 là bản đã sửa cộng đúng một bug (bug 5 không đổi việc học nên không có dòng riêng: nó chỉ làm số log tăng dần, như
dòng "đủ 5 bug"). Clip fraction lớn nhất: bản sửa 0.086 / 0.094 / 0.141, bug 3 lên tới 0.375, notebook gốc 0.266 / 0.312 / 0.297.

Đọc bảng:

- **Không bug nào làm notebook hỏng hẳn.** Nhiều seed vẫn đạt greedy 500 với một bug; chỉ khi so 3 seed với bản đúng mới thấy độ
  kém. Bug 1 rõ nhất (return lúc train còn 182 tới 260 ở mốc cuối). Bug 2 chỉ hại một seed (seed 0); hai seed kia thậm chí ngang bản
  sửa: tác hại của nó phụ thuộc agent có hay chạm 500 bước không.
- **Bug 3 lộ ở chẩn đoán ở 2 trên 3 seed**: approx KL lớn nhất 0.044 và clip fraction 0.375 ở seed 1 (gấp khoảng 5 lần bản sửa) trong
  khi return của seed đó vẫn đẹp; seed 2 có 0.017 và 0.250. Seed 0 thì không (KL lớn nhất 0.0037, thấp hơn cả bản sửa): chẩn đoán giúp
  nhưng không thay được test so với cài đặt tham chiếu.
- **Bug 4** kéo entropy cuối xuống ở cả 3 seed (0.44 tới 0.50 so với 0.53 tới 0.54); với hệ số 0.01 tác hại nhỏ, ở bài khám phá khó
  (reward thưa) nó đủ để agent không bao giờ tìm thấy reward.
- **Bug 5 che mọi thứ**: đường cong của notebook gốc tăng đều tới khoảng 37 000, trên một env có return tối đa 500. Không sửa nó trước
  thì không đọc được tác động của bất kỳ bug nào khác.

### Bug 1: `value` trả shape `(B, 1)`

- **Ở đâu.** `ActorCritic.value`: `return self.critic(obs)` thiếu `.squeeze(-1)`. `collect_rollout` che lỗi bằng `.reshape(-1)` nên
  buffer vẫn đúng shape.
- **Triệu chứng.** Trong `ppo_update`, `model.value(obs) - returns` là `(128, 1) - (128,)` (minibatch 128 mẫu), broadcasting ra ma trận `(128, 128)`: value loss
  là trung bình bình phương của **mọi cặp** dự đoán và return, critic học về trung bình của return trong minibatch thay vì return của
  từng trạng thái. Không lỗi, value loss vẫn giảm.
- **Phát hiện.** `print(model.value(obs).shape)` hoặc `assert v.shape == returns.shape` trong `ppo_update`.
- **Sửa.** `return self.critic(obs).squeeze(-1)`.

### Bug 2: `gae` coi `truncated` là kết thúc

- **Ở đâu.** `gae`: `delta = rewards[t] + gamma * not_done[t] * next_values[t] - values[t]` (dùng `not_done` thay `not_term`).
- **Triệu chứng.** Ở bước 500 của CartPole (bị cắt), target là $$r$$ thay vì $$r + \gamma V(s')$$: trạng thái tốt nhất bị dạy là có giá trị
  gần 1, trong khi trạng thái giống hệt ở bước 300 có giá trị gần 100. Chỉ lộ khi agent đã đủ giỏi để chạm 500.
- **Phát hiện.** Env tí hon reward 1 mỗi bước, cắt sau 3 bước, `next_values` biết trước: advantage ở bước bị cắt sai đúng một
  lượng $$\gamma V(s')$$. Hoặc so với `gae` của bài Basic 03.
- **Sửa.** Dùng `not_term[t]` trong `delta`; `not_done` chỉ dùng cho đệ quy.

### Bug 3: `max` thay `min` trong clipped objective

- **Ở đâu.** `ppo_policy_loss`: `-torch.max(ratio * adv, clipped * adv)`.
- **Triệu chứng.** Mất trust region: action có advantage dương bị đẩy lên không giới hạn, action có advantage dương đã bị giảm quá tay
  thì gradient bị tắt. Return vẫn có thể đẹp (seed 1: 472 ở mốc cuối), nhưng approx KL lớn nhất 0.044 và clip fraction 0.375, gấp khoảng 5 lần bản sửa.
- **Phát hiện.** Tính tay vài ratio: với $$\rho = 1.5, A = 1$$ loss phải là $$-1.2$$, bản lỗi cho $$-1.5$$; gradient theo $$\rho$$ ở nhánh bị cắt
  phải bằng 0.
- **Sửa.** `torch.min`.

### Bug 4: sai dấu entropy bonus

- **Ở đâu.** `ppo_update`: `loss = policy_loss + vf_coef * value_loss + ent_coef * entropy`.
- **Triệu chứng.** Tối thiểu hoá loss thành **giảm** entropy: policy bị đẩy về tất định sớm, mất khám phá. Entropy cuối 0.437 / 0.497 / 0.495 so với 0.540 / 0.532 / 0.534 của bản sửa; seed 0 chỉ còn 229 ở mốc cuối.
- **Phát hiện.** Vẽ entropy theo lần cập nhật; hoặc đặt `ent_coef` lớn (0.5) trên một batch cố định và xem entropy sau một bước tăng
  hay giảm.
- **Sửa.** `- ent_coef * entropy`.

### Bug 5: return của episode không được reset

- **Ở đâu.** `collect_rollout`: sau khi ghi `envs.ep_returns[i]` vào `episode_returns` thì không gán lại 0.
- **Triệu chứng.** Không ảnh hưởng việc học, nhưng **đường cong nói dối**: return ghi lại là tổng cộng dồn của mọi episode từng chạy
  trên env đó, tăng đều theo thời gian kể cả khi agent không học gì. Notebook gốc log trung bình khoảng 11 000 ở mốc 50 000 bước và khoảng 36 000 ở mốc cuối. CartPole không thể vượt 500.
- **Phát hiện.** So return log với giới hạn lý thuyết; hoặc đánh giá policy bằng một hàm độc lập (Intermediate 01, 02) và so với số
  log lúc train.
- **Sửa.** `envs.ep_returns[i] = 0.0` sau khi ghi.

## Thứ tự gỡ nên đi

1. Bug 5 trước: khi metric sai, mọi kết luận khác đều vô nghĩa. Kiểm mọi con số với giới hạn của nó (return ≤ 500, entropy ≤ ln 2,
   KL ≥ 0).
2. Shape (bug 1): rẻ nhất, `assert` mọi shape trong loss.
3. Từng hàm thuần (bug 2, 3) trên đầu vào tính tay được.
4. Dấu và hệ số của loss tổng (bug 4) bằng một bước cập nhật trên batch cố định, so với loss viết tay.
5. Chỉ sau đó mới train lại trên CartPole, 3 seed, so với bảng mục 5 lý thuyết.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 15 | Mọi test pass, siêu tham số mặc định không đổi |
| Tìm đủ và sửa đúng gốc | 25 | 5 bug, mỗi bug sửa đúng dòng gốc; không bù bằng siêu tham số, không thêm code che triệu chứng (ví dụ `reshape` thêm ở chỗ khác) |
| Bằng chứng định lượng | 25 | Mỗi bug có con số trước/sau (shape, giá trị tính tay, entropy, approx KL, return) |
| Phương pháp | 20 | Mỗi bug có phép thử độc lập, tất định, rẻ; có thứ tự gỡ và giải thích bug nào che bug nào |
| Checklist và bài học | 15 | Checklist dùng lại được cho cài đặt RL khác (giới hạn lý thuyết của metric, assert shape, env tí hon có đáp án, so với tham chiếu, nhiều seed) |

Đạt từ 70 điểm. `BUGS.md` chỉ liệt kê dòng đã sửa mà không có triệu chứng đo được và cách phát hiện thì không quá 50 điểm.
