---
title: DDPM forward process, noise schedule và posterior
level: basic
services: []
files:
  - path: starter/ddpm.py
    note: 8 hàm TODO
  - path: tests/test_ddpm.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/06-generative-models/exercises/basic/03-ddpm-forward-posterior -q
---

## Mục tiêu

Viết phần toán không có tham số học của DDPM: hai noise schedule (linear, cosine), $$q(x_t \mid x_0)$$ dạng đóng, posterior
$$q(x_{t-1} \mid x_t, x_0)$$, và mean của bước ngược khi model dự đoán nhiễu. Test so dạng đóng với chuỗi Markov chạy từng bước và so
posterior với định lý Bayes tính theo cách khác, nên mọi lỗi căn bậc hai, lệch chỉ số một bước hay nhầm variance đều lộ ra. Bài
Intermediate 03 và Advanced 01 dựng model trên đúng các công thức này.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Đọc mục 5 phần lý thuyết. Trong `starter/ddpm.py`, schedule là tensor float64 dài $$T$$, chỉ số `t = 0..T-1` ứng với bước $$t + 1$$ của
bài báo: `alpha_bar[t]` là tích $$(1 - \beta_s)$$ với $$s = 0..t$$, và "trước bước 0" thì $$\bar\alpha = 1$$. `t` truyền vào các hàm là tensor
số nguyên shape `(B,)`, mỗi mẫu một bước; kết quả cùng shape và dtype với `x`.

1. `linear_betas(T=1000, beta_start=1e-4, beta_end=0.02)` và `cosine_betas(T=1000, s=0.008, max_beta=0.999)` (công thức trong docstring),
   `alpha_bars(betas)`.
2. `q_sample(x0, t, noise, alpha_bar)`: $$x_t$$ theo dạng đóng.
3. `q_posterior(x0, xt, t, betas)`: `(mean, variance)` của $$q(x_{t-1} \mid x_t, x_0)$$; variance broadcast được với `x0` (vd. shape `(B, 1, ...)`),
   bằng 0 tại `t = 0`.
4. `predict_x0(xt, t, eps, alpha_bar)`: đảo `q_sample` khi biết nhiễu.
5. `p_mean_variance(xt, t, eps, betas)`: mean của $$p_\theta(x_{t-1} \mid x_t)$$ khi mạng dự đoán nhiễu `eps`, variance là variance của posterior.
6. `snr(alpha_bar)`: $$\bar\alpha/(1 - \bar\alpha)$$.

## Tiêu chí đạt

- `linear_betas` đúng hai đầu và cách đều; `alpha_bars` là tích luỹ; `cosine_betas` cho $$\bar\alpha_t = f(t + 1)/f(0)$$ tới 9 chữ số ở các bước chưa
  bị chặn, $$\beta$$ lớn nhất đúng bằng 0.999, $$\bar\alpha$$ cuối dưới 1e-6.
- `q_sample` đúng công thức với mỗi mẫu một `t` khác nhau; 200 000 lần chạy chuỗi Markov từng bước và dạng đóng có cùng mean, phương sai.
- `q_posterior` khớp posterior tính bằng tích hai Gauss theo độ chính xác (precision) ở mọi `t`, kể cả `t = 0` (mean là $$x_0$$, variance 0).
- `predict_x0` đảo đúng `q_sample`; `p_mean_variance` với nhiễu thật cho đúng mean và variance của posterior.

## Gợi ý

### Gợi ý 1

Một hàm nhỏ lấy `values[t]` rồi reshape thành `(B, 1, 1, ...)` (số chiều 1 bằng số chiều của `x` trừ một) dùng được cho mọi hàm sau. Với
posterior, cần thêm mảng $$\bar\alpha_{t-1}$$: dịch `alpha_bar` sang phải một ô và đặt 1 ở đầu.

### Gợi ý 2

Mean của bước ngược theo nhiễu không cần nhớ: lấy $$x_0$$ từ `predict_x0`, thay vào mean của posterior, rút gọn. Test so `p_mean_variance` với
`q_posterior` đúng theo cách đó, nên nếu một trong hai sai bạn sẽ thấy ngay chúng lệch nhau.
