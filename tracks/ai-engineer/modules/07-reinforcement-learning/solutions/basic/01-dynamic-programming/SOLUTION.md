# Lời giải: dynamic programming trên FrozenLake

## Cách làm

| Hàm | Công thức | Ghi chú |
| --- | --- | --- |
| `q_from_v` | $$Q(s,a) = \sum_{s'} p(s' \mid s,a)\,[r + \gamma (1 - d)\,V(s')]$$ | $$d$$ là cờ `terminated` của từng chuyển |
| `policy_evaluation` | $$V_{k+1}(s) = \sum_a \pi(a \mid s)\,Q_k(s,a)$$ | dừng khi thay đổi lớn nhất < `tol` |
| `greedy_policy` | one-hot tại `Q.argmax(axis=1)` | `argmax` lấy chỉ số nhỏ nhất khi hoà |
| `value_iteration` | $$V_{k+1}(s) = \max_a Q_k(s,a)$$ | cuối cùng lấy greedy theo $$Q$$ của $$V^*$$ |
| `policy_iteration` | evaluate → greedy → lặp tới khi policy không đổi | bắt đầu từ policy đều |

Quét đồng bộ: tính cả mảng $$V_{k+1}$$ từ $$V_k$$, như đề yêu cầu. Quét tại chỗ (Gauss-Seidel, dùng ngay giá trị mới của các trạng
thái đã cập nhật trong cùng lần quét) cũng hội tụ về cùng $$V^*$$ và thường cần ít lần quét hơn, nhưng số lần quét khi đó phụ thuộc
thứ tự duyệt trạng thái nên đề cố định cách đồng bộ để số đo so được.

## Số đo trên FrozenLake

`gym.make("FrozenLake-v1")` (4x4, trơn: đi đúng hướng chỉ với xác suất 1/3), `tol = 1e-10`:

| $$\gamma$$ | $$V^*(0)$$ | Value iteration | Policy iteration |
| --- | --- | --- | --- |
| 0.9 | 0.0689 | 145 lần quét | 2 lần evaluate |
| 0.99 | 0.5420 | 571 lần quét | 3 lần evaluate |
| 1.0 | 0.8235 | 806 lần quét | 3 lần evaluate |

Policy ngẫu nhiên đều có $$V(0) = 0.0124$$ với $$\gamma = 0.99$$. Policy iteration ít vòng vì mỗi vòng giải trọn một policy (mỗi
lần evaluate tự nó cũng là hàng trăm lần quét), còn value iteration chỉ nhích một bước Bellman mỗi lần. Tổng số phép tính của hai
cách cùng cỡ; trên MDP lớn, policy iteration thường thắng khi evaluate giải trực tiếp bằng hệ tuyến tính.

## Bẫy thường gặp

- Cộng $$\gamma V(s')$$ cả khi `terminated`: với FrozenLake bạn không thấy sai vì giá trị ở hố và đích tự nhiên bằng 0 (chuyển tự
  quay về có reward 0). Test dùng một MDP mà trạng thái kết thúc tự quay về với reward 5 để lộ lỗi này.
- Nhân $$\gamma$$ vào cả reward: $$\gamma(r + V)$$ thay vì $$r + \gamma V$$.
- Dùng `max` trong policy evaluation: đó là value iteration, không còn là giá trị của policy đang xét.
- So `policy` mới với cũ bằng `V`: hai policy khác nhau có thể cùng $$V$$ (hoà), vòng lặp không dừng. So mảng policy.
