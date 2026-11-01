# Lời giải: return, n-step return, GAE

## Cách làm

| Hàm | Cài đặt |
| --- | --- |
| `reward_to_go` | vòng ngược `running = r[t] + γ·running` |
| `n_step_returns` | với mỗi $$t$$, cộng dần tối đa $$n$$ reward, giữ mặt nạ `alive` theo env; ở bước dừng cộng $$\gamma^{m}V(s_{t+m})$$ nếu không phải `terminated` |
| `gae` | vòng ngược: $$\delta_t = r_t + \gamma(1-\text{term}_t)V(s_{t+1}) - V(s_t)$$, $$\hat A_t = \delta_t + \gamma\lambda(1-\text{done}_t)\hat A_{t+1}$$ |
| `normalize_advantages` | `(adv − mean) / (std + eps)` |

Hai mặt nạ trong `gae`:

- `1 − terminated` trong $$\delta_t$$: trạng thái kết thúc thật có giá trị 0, nên không cộng $$\gamma V(s_{t+1})$$.
- `1 − done` với `done = terminated or truncated` trong đệ quy: bước sau thuộc episode khác (env đã reset), không được cộng
  advantage của nó vào.

Với `truncated`, $$\delta_t$$ vẫn bootstrap từ `next_values[t]`, giá trị của final observation thật. Vì vậy quy ước buffer cần
`next_values` riêng cho từng bước thay vì chỉ một `last_value` như nhiều cài đặt ngắn gọn (CleanRL dùng `values[t+1]` và một
`next_value` cuối buffer): cách đó không phân biệt được `truncated` với `terminated`, và với env bị cắt thường xuyên (CartPole
dừng ở 500 bước, MuJoCo ở 1 000) critic bị dạy rằng trạng thái tốt ở bước cuối có giá trị 0.

## Kiểm bằng gì

Test so với ba "nghiệm biết trước": $$\lambda = 0$$ là TD error, $$\lambda = 1$$ là Monte Carlo trừ baseline, và tổng
$$\sum_k(\gamma\lambda)^k\delta_{t+k}$$ tính thẳng theo định nghĩa (vòng lồng, chậm nhưng không thể sai theo cách đệ quy sai). Cộng
thêm các buffer tí hon tính tay cho `terminated` khác `truncated` và cho "rò" reward qua ranh giới episode.

## Bẫy thường gặp

- Một mặt nạ cho cả hai việc: hoặc coi `truncated` là `terminated` (mất bootstrap), hoặc quên cắt đệ quy ở `truncated` (cộng
  advantage của episode sau).
- Duyệt xuôi thay vì ngược: $$\hat A_{t+1}$$ chưa được tính khi cần.
- Trả `returns = advantages`: critic học advantage thay vì giá trị, value loss không giảm.
- Chuẩn hoá không có `eps`: advantage hằng (ví dụ mọi episode đều được 500 trên CartPole) cho `0/0 = nan` và phá cả model.
