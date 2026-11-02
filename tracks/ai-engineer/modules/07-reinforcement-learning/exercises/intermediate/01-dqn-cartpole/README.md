---
title: DQN tự viết trên CartPole, replay buffer và target network
level: intermediate
services: []
files:
  - path: starter/dqn.ipynb
    note: 8 hàm/lớp TODO
  - path: tests/test_dqn.py
    note: Không sửa
run:
  - uv run jupyter lab tracks/ai-engineer/modules/07-reinforcement-learning/exercises/intermediate/01-dqn-cartpole/starter/dqn.ipynb
  - uv run pytest tracks/ai-engineer/modules/07-reinforcement-learning/exercises/intermediate/01-dqn-cartpole -q
---

## Mục tiêu

Thay bảng Q của bài Basic 02 bằng một MLP và tự viết hai mảnh làm DQN train được: replay buffer và target network (hard và soft
update), cộng Double DQN. Rồi đo bằng 3 seed xem bỏ target network thì chuyện gì xảy ra, vì sao phải giữ checkpoint tốt nhất, và Q dự
đoán lệch khỏi return thật bao nhiêu.

## Đề bài

**Phần cứng:** CPU · ~150 phút

Thời gian trên là thời gian làm bài. Cell train của notebook lời giải (3 cấu hình × 3 seed × 50 000 bước) chạy khoảng 13 phút (mỗi lần 80 tới 90 giây) trên CPU 4
luồng, chủ yếu là bước học (forward, backward, Adam mỗi bước env); GPU không giúp gì với MLP 4-128-128-2.

Đọc mục 4 phần lý thuyết. Trong `starter/dqn.ipynb`, điền các cell theo đặc tả ngay trên mỗi cell:

1. `ReplayBuffer`: mảng numpy cấp sẵn, ghi vòng tròn, `sample` bằng rng riêng, trả dict tensor.
2. `QNetwork`, `linear_epsilon`, `select_action`.
3. `td_targets` (DQN và Double DQN, không mang gradient) và `dqn_loss` (Huber trên $$Q(s, a)$$ của action đã làm).
4. `evaluate_policy` và `train_dqn` theo đúng 5 bước trong notebook: soft update khi `tau < 1`, hard update mỗi `target_update` bước
   khi `tau = 1`, đánh giá greedy định kỳ và giữ bản sao checkpoint tốt nhất.

Rồi chạy các cell `explore`: mốc của policy ngẫu nhiên, train 3 cấu hình × 3 seed (soft update, hard update mỗi 500 bước, không
target network), đường cong, đánh giá cuối trên 20 episode cố định, và so Q dự đoán với return chiết khấu thật. Sau đó làm phần trắc
nghiệm của bài trong app.

## Tiêu chí đạt

- `ReplayBuffer` ghi đè chuyển cũ nhất khi đầy, chỉ lấy mẫu trong phần đã ghi, đúng dtype và shape, cùng seed cho cùng mẫu.
- `td_targets` dùng target net (không phải mạng online), `terminated` không bootstrap, không mang gradient; Double DQN chọn action
  bằng mạng online và không bao giờ lớn hơn target của DQN thường; `dqn_loss` đúng giá trị, gradient chỉ vào mạng online, đúng cả khi
  hai mạng là một.
- `train_dqn`: đúng số bước học và mốc đánh giá, lịch ε đúng từng bước, `best_state` là bản sao, cùng seed cho cùng kết quả; giải được
  một hành lang 5 ô; trên env reward 1 mỗi bước bị cắt sau 10 bước Q tiến tới $$1/(1-\gamma)$$ (`truncated` vẫn bootstrap); target net gần
  như đứng yên (hard update thưa hoặc $$\tau$$ rất nhỏ) thì Q dừng ở gần 1, $$\tau = 0.05$$ thì Q theo kịp tới 10.
- Trên CartPole, kết luận của bạn khớp bảng mục 4 lý thuyết: cấu hình nào ổn định, cấu hình nào sụp.

## Gợi ý

### Gợi ý 1

Target là hằng số với gradient: nghĩ xem phần nào của loss không được ghi graph autograd. In shape của $$Q(s, a)$$ và của target
trước khi gọi loss: hai tensor phải cùng shape. Test `EndlessReward` (một observation, reward 1 mỗi bước, cắt sau 10 bước) là phép thử
nhanh nhất cho cả `truncated` lẫn target network.

### Gợi ý 2

Soft update cập nhật mọi cặp tham số tại chỗ, ngoài autograd, ngay sau bước optimizer. Đánh giá định kỳ dùng policy greedy
(ε = 0) trên seed riêng, tách khỏi seed của đánh giá cuối.
