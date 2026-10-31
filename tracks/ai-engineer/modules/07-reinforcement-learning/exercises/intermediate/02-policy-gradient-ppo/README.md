---
title: REINFORCE, baseline và PPO tự viết trên CartPole
level: intermediate
services: []
files:
  - path: starter/pg.ipynb
    note: 9 hàm/lớp TODO
  - path: tests/test_pg.py
    note: Không sửa
run:
  - uv run jupyter lab tracks/ai-engineer/modules/07-reinforcement-learning/exercises/intermediate/02-policy-gradient-ppo/starter/pg.ipynb
  - uv run pytest tracks/ai-engineer/modules/07-reinforcement-learning/exercises/intermediate/02-policy-gradient-ppo -q
---

## Mục tiêu

Tự viết hai thế hệ policy gradient trên cùng một bài: REINFORCE (không và có baseline) và PPO với GAE, nhiều env song song, clipped
objective, rồi so chúng trên 3 seed với cùng ngân sách bước env. Làm xong bạn có một cài đặt PPO đúng tới từng chi tiết (mặt nạ
`terminated`/`truncated`, chuẩn hoá advantage theo minibatch, lr giảm dần), đọc được approx KL và clip fraction, và có bộ khung cho
bài Advanced 01.

## Đề bài

**Phần cứng:** CPU · ~150 phút

Thời gian trên là thời gian làm bài. Cell train của notebook lời giải (3 thuật toán × 3 seed × 150 000 bước) chạy khoảng 12 phút trên
CPU 4 luồng: REINFORCE khoảng 95 giây mỗi seed (một env, một forward mỗi bước), PPO khoảng 37 giây mỗi seed.

Đọc mục 5 và 6 phần lý thuyết. Trong `starter/pg.ipynb`, điền các cell theo đặc tả ngay trên mỗi cell:

1. `ActorCritic`: actor và critic là hai MLP tách rời, khởi tạo orthogonal (actor head gain 0.01, critic head gain 1);
   `value` trả shape `(B,)`.
2. `reinforce_loss`, `ppo_policy_loss` (trả cả `clipfrac` và `approx_kl`), và `gae` dán từ bài Basic 03.
3. `train_reinforce`: batch 8 episode, reward-to-go có chiết khấu, baseline là critic học song song.
4. `collect_rollout` trên `SyncVectorEnv` chế độ SAME_STEP: bootstrap từ `info["final_obs"]` khi env vừa kết thúc, return của
   episode dở dang sống qua các lần gọi.
5. `ppo_update` và `train_ppo` theo đúng thứ tự trong notebook.

Rồi chạy các cell `explore`: kiểm entropy ban đầu, train 3 thuật toán × 3 seed, vẽ đường cong và bảng return theo cửa sổ 10 000 bước,
xem chẩn đoán PPO, đánh giá policy greedy và lấy mẫu. Sau đó làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `ActorCritic`: đúng số tham số hai mạng tách rời, `value` shape `(B,)`, entropy ban đầu bằng $$\ln n_A$$ (sai số 0.01).
- `reinforce_loss` đúng giá trị và gradient, không để gradient chảy vào baseline; `ppo_policy_loss` đúng giá trị trên 5 ratio tính
  tay, gradient bằng 0 đúng ở hai nhánh bị cắt, `clipfrac` và `approx_kl` đúng.
- `collect_rollout` trên env đếm bước bị cắt sau 3 bước: `next_values` ở bước bị cắt là $$V$$ của final observation, return từng
  episode đúng qua hai lần gọi, log-prob khớp action đã lấy mẫu.
- Một bước `ppo_update` với SGD khớp loss tham chiếu (advantage chuẩn hoá trong minibatch, value loss có hệ số 1/2, trừ entropy) và
  tôn trọng `max_grad_norm`; `train_ppo` đặt lr giảm tuyến tính, làm phẳng `(T, N)` theo thứ tự bước rồi env, critic học `returns`.
- REINFORCE (có và không baseline) và PPO học được bandit theo ngữ cảnh (return > 0.9); cùng seed cho cùng kết quả.
- Trên CartPole, PPO tới gần 500 sớm hơn REINFORCE trong cùng 150 000 bước (so với bảng mục 5 lý thuyết).

## Gợi ý

### Gợi ý 1

Viết và test từng hàm trên dữ liệu tí hon trước khi train: `ppo_policy_loss` với vài ratio bạn tính tay được, `collect_rollout` với
một env bạn tự viết (reward 1 mỗi bước, cắt sau 3 bước) để nhìn từng ô của buffer. Một cài đặt PPO sai thường vẫn học được
CartPole, chỉ kém hơn: train xong mà thấy "cũng lên 400" chưa chứng minh gì.

### Gợi ý 2

Thứ tự trong `collect_rollout` mỗi bước: tính `dist`, `value` của observation hiện tại (không ghi graph), lấy mẫu action, `envs.step`,
ghi buffer, dựng observation thật sau bước (thay bằng `info["final_obs"][i]` ở env vừa kết thúc), tính `next_values` từ đó, cộng
reward vào return dở dang, ghi và reset return của env vừa kết thúc, rồi mới gán observation mới. Trong `ppo_update`, chuẩn hoá
advantage **sau** khi cắt minibatch.
