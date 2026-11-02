---
title: Policy evaluation, value iteration, policy iteration trên FrozenLake
level: basic
services: []
files:
  - path: starter/dp.py
    note: 5 hàm TODO
  - path: tests/test_dp.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/07-reinforcement-learning/exercises/basic/01-dynamic-programming -q
---

## Mục tiêu

Tự viết ba thuật toán dynamic programming của mục 2 phần lý thuyết trên MDP biết trước mô hình, rồi kiểm chúng trên một MDP
có nghiệm đóng và trên FrozenLake thật của Gymnasium. Làm xong bạn hiểu Bellman backup là phép tính gì, vì sao chuyển
`terminated` không được bootstrap, và vì sao policy iteration cần ít vòng hơn value iteration hàng trăm lần.

## Đề bài

**Phần cứng:** CPU · ~60 phút

MDP cho ở dạng `env.unwrapped.P` của Gymnasium toy_text: `P[s][a]` là danh sách `(prob, next_state, reward, terminated)`.
Trong `starter/dp.py`, chỉ dùng numpy, viết:

1. `q_from_v(P, V, gamma)`: một Bellman backup, trả `Q` shape `(nS, nA)`. Chuyển có `terminated=True` không cộng
   $$\gamma V(s')$$.
2. `policy_evaluation(P, policy, gamma, tol)`: lặp Bellman expectation backup từ $$V = 0$$ tới khi
   $$\max_s |V_{k+1}(s) - V_k(s)| < \text{tol}$$. `policy` shape `(nS, nA)`, mỗi dòng là một phân phối. Quét **đồng bộ**:
   tính cả mảng $$V_{k+1}$$ từ $$V_k$$ (test đếm số lần quét theo cách này).
3. `greedy_policy(Q)`: policy one-hot, hoà thì lấy chỉ số nhỏ nhất (đúng như `np.argmax`).
4. `value_iteration(P, gamma, tol)`: trả `(V, policy, n_iter)`, `n_iter` là số lần quét.
5. `policy_iteration(P, gamma, tol)`: bắt đầu từ policy đều; mỗi vòng một `policy_evaluation` rồi cải thiện greedy; dừng khi
   policy không đổi. Trả `(V, policy, n_iter)`, `n_iter` là số lần gọi `policy_evaluation` kể cả lần cuối.

Chạy thử trên `gym.make("FrozenLake-v1").unwrapped.P` với $$\gamma = 0.99$$ và so với mục 2 lý thuyết: $$V^*$$ của ô xuất phát,
số lần quét của value iteration, số vòng của policy iteration.

## Tiêu chí đạt

- `q_from_v` đúng từng số trên một MDP 2 trạng thái ngẫu nhiên; chuyển `terminated` không cộng $$\gamma V(s')$$ dù $$V(s')$$ lớn.
- `policy_evaluation` khớp nghiệm đóng $$V^\pi = (I - \gamma P_\pi)^{-1} r_\pi$$ tới `1e-6` với $$\gamma$$ 0.5, 0.9, 0.99.
- `value_iteration` và `policy_iteration` cho cùng $$V^*$$ (bằng policy tất định tốt nhất tìm vét cạn) và cùng policy.
- FrozenLake 4x4 trơn, $$\gamma = 0.99$$: $$V^*(0) = 0.5420$$ (sai số `5e-4`), giá trị ở hố và đích bằng 0, value iteration
  cần 400 tới 800 lần quét, policy iteration ổn định sau 2 tới 4 lần evaluate; policy ngẫu nhiên đều có $$V(0) \approx 0.0124$$.

## Gợi ý

### Gợi ý 1

Mọi hàm còn lại đều dựng trên `q_from_v`. Policy evaluation là "trung bình Q theo policy", value iteration là "max Q theo
action"; cả hai lặp tới khi hết thay đổi.

### Gợi ý 2

FrozenLake có trạng thái kết thúc (hố, đích) với chuyển tự quay về chính nó, `terminated=True`. Nếu giá trị ở hố không về 0,
hoặc $$V^*(0)$$ của bạn lớn hơn 0.542, kiểm lại chỗ bạn nhân $$(1 - \text{terminated})$$. Policy iteration dừng khi mảng policy mới
bằng đúng mảng cũ (`np.array_equal`).
