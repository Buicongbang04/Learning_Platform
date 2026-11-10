# Lời giải: Q-learning và SARSA dạng bảng

## Cách làm

| Hàm | Cài đặt |
| --- | --- |
| `linear_epsilon` | `start + min(step / decay_steps, 1) * (end - start)`, `decay_steps <= 0` trả `end` |
| `epsilon_greedy` | `rng.random() < ε` thì `rng.integers(nA)`, ngược lại `rng.choice(flatnonzero(q == q.max()))` |
| `q_learning_update` | target $$r + \gamma(1-d)\max_{a'}Q(s',a')$$, `Q[s,a] += α·(target − Q[s,a])` |
| `sarsa_update` | target $$r + \gamma(1-d)\,Q(s',a')$$ với $$a'$$ là action sẽ làm thật |
| `train_td` | một vòng chung cho hai method, khác nhau ở thứ tự chọn $$a'$$ và hàm cập nhật |

Trong `train_td`, $$d$$ là `terminated`, không phải `terminated or truncated`. CliffWalking không có time limit, FrozenLake cắt ở
100 bước; env thử `EndlessReward` của test cắt ở 5 bước để lộ lỗi: coi `truncated` là kết thúc thì bước cuối có target chỉ là
$$r = 1$$, Q hội tụ về một số nhỏ hơn hẳn 10.

## Vì sao Q-learning và SARSA khác nhau trên CliffWalking

Q-learning là **off-policy**: target dùng $$\max_{a'}$$, tức là giá trị của policy greedy, không phải policy ε-greedy đang chạy. Nó
học đúng đường tối ưu sát vực (13 bước, return −13), nhưng khi vẫn khám phá ε = 0.1 thì đi sát vực thỉnh thoảng rơi xuống (−100),
nên return lúc train tệ. SARSA là **on-policy**: target dùng action thật của policy ε-greedy, nên giá trị các ô sát vực đã tính cả
rủi ro bị đẩy xuống vực. Nó học đường vòng an toàn (15 tới 19 bước) và return lúc train cao hơn. Khi ε về 0, hai cách hội tụ
về cùng policy tối ưu.

Hệ quả thực tế: chọn on-policy khi agent phải hành xử an toàn **trong lúc học** (robot thật), off-policy khi chỉ policy cuối
cùng quan trọng hoặc khi muốn học từ dữ liệu cũ (replay buffer của DQN, mục 4 lý thuyết).

## Bẫy thường gặp

- `argmax` không tie-break ngẫu nhiên: lúc đầu mọi Q bằng 0, agent luôn chọn action 0.
- Khám phá chỉ chọn trong các action **không** greedy: tần suất action greedy thành $$1 - \varepsilon$$ thay vì
  $$1 - \varepsilon + \varepsilon/n_A$$; test đo tần suất này.
- Lịch ε không bao giờ giảm: Q-learning vẫn học đúng Q (off-policy, học được từ hành vi ngẫu nhiên), nhưng return lúc train mãi
  như ngẫu nhiên. Test kiểm cả return lúc train để bắt lỗi này.
- Trả TD error **sau** khi cập nhật: $$(1 - \alpha)$$ lần giá trị đúng.
