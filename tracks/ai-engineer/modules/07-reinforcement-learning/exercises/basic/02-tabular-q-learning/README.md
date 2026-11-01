---
title: Q-learning và SARSA dạng bảng, ε-greedy, time limit
level: basic
services: []
files:
  - path: starter/qlearn.py
    note: 5 hàm TODO
  - path: tests/test_qlearn.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/07-reinforcement-learning/exercises/basic/02-tabular-q-learning -q
---

## Mục tiêu

Bỏ giả định "biết trước mô hình" của bài Basic 01: agent chỉ được tương tác với env và học Q từ từng chuyển. Bạn tự viết
ε-greedy, lịch ε, cập nhật Q-learning và SARSA, vòng train dùng API Gymnasium, rồi thấy tận mắt khác biệt off-policy và
on-policy trên CliffWalking. Đây là bộ khung mà DQN (Intermediate 01) thay bảng bằng mạng nơ-ron.

## Đề bài

**Phần cứng:** CPU · ~75 phút

Đọc mục 1 (API `terminated`/`truncated`) và mục 3 phần lý thuyết. Trong `starter/qlearn.py`, chỉ dùng numpy:

1. `linear_epsilon(step, start, end, decay_steps)`: giảm tuyến tính rồi giữ ở `end`.
2. `epsilon_greedy(q_row, epsilon, rng)`: khám phá chọn đều trong **mọi** action (kể cả action greedy); khai thác chọn
   action có Q lớn nhất, hoà thì chọn ngẫu nhiên đều giữa các action hoà. Mọi ngẫu nhiên lấy từ `rng`.
3. `q_learning_update` và `sarsa_update`: cập nhật `Q[s, a]` tại chỗ, trả TD error tính **trước** khi cập nhật.
4. `train_td(env, method, ...)`: vòng train theo docstring, chạy được cả `"q_learning"` và `"sarsa"`. Chỉ `terminated` mới cắt
   bootstrap; `truncated` (time limit) chỉ kết thúc episode.

Chạy thử trên `gym.make("FrozenLake-v1", is_slippery=False)` và `gym.make("CliffWalking-v1")`, so đường đi greedy của
Q-learning và SARSA với mục 3 lý thuyết.

## Tiêu chí đạt

- `linear_epsilon` đúng ở đầu, giữa, cuối và sau lịch; `epsilon_greedy` với ε = 0.4 trên 4 action chọn action greedy với tần
  suất 0.7 (sai số 0.015), hoà thì chọn ngẫu nhiên giữa các action hoà, cùng seed cho cùng chuỗi action.
- Hai hàm cập nhật đúng từng số, sửa đúng một ô, `terminated` không bootstrap; SARSA dùng `Q[s', a']` chứ không dùng max.
- Một env reward 1 mỗi bước bị cắt sau 5 bước: Q tiến tới $$1/(1-\gamma) = 10$$ (sai số 0.05), tức là `truncated` vẫn bootstrap.
- FrozenLake không trơn, 500 episode: đường greedy tới đích trong 6 bước, return trung bình 100 episode cuối lúc train > 0.8,
  cùng seed cho cùng `Q`.
- CliffWalking, $$\alpha = 0.2$$, ε = 0.1 cố định, 500 episode: Q-learning greedy đi sát vực (return −13); SARSA greedy đi đường
  vòng (return −15 tới −19); return lúc train (200 episode cuối) của SARSA cao hơn Q-learning ít nhất 10.

## Gợi ý

### Gợi ý 1

Viết hai hàm cập nhật trước, chúng chỉ khác nhau ở một số hạng trong target. Trong vòng train, thứ tự của SARSA là: thực hiện
`a`, nhận `s'`, **chọn** `a'` từ `s'`, rồi mới cập nhật bằng `(s, a, r, s', a')`, và `a'` chính là action làm ở bước sau.

### Gợi ý 2

Lúc đầu mọi Q bằng 0, nên cách bạn phá thế hoà quyết định agent có khám phá được gì không: nếu luôn chọn action có chỉ số nhỏ nhất,
trên FrozenLake agent đi mãi vào góc trái. Nếu Q-learning trên CliffWalking học được đường −13 mà return lúc train vẫn tệ hơn SARSA,
đó là kết quả **đúng**: mục 3 lý thuyết giải thích vì sao.
