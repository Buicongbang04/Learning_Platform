# Lời giải: DDPM forward process, schedule và posterior

## Cách làm

Một hàm phụ `_gather(values, t, x)` lấy `values[t]` cho từng mẫu, đổi sang dtype và device của `x`, reshape thành `(B, 1, ..., 1)`. Mọi công
thức sau đó viết đúng như trên giấy:

| Hàm | Công thức |
| --- | --- |
| `alpha_bars` | `cumprod(1 - betas)` |
| `cosine_betas` | $$\bar\alpha(u) = f(u)/f(0)$$ với $$u = 0..T$$, $$\beta_t = 1 - \bar\alpha(t + 1)/\bar\alpha(t)$$, chặn 0.999 |
| `q_sample` | $$\sqrt{\bar\alpha_t}\,x_0 + \sqrt{1 - \bar\alpha_t}\,\varepsilon$$ |
| `q_posterior` | $$\tilde\mu = \frac{\sqrt{\bar\alpha_{t-1}}\beta_t}{1 - \bar\alpha_t}x_0 + \frac{\sqrt{\alpha_t}(1 - \bar\alpha_{t-1})}{1 - \bar\alpha_t}x_t$$, $$\tilde\beta = \frac{1 - \bar\alpha_{t-1}}{1 - \bar\alpha_t}\beta_t$$ |
| `predict_x0` | $$(x_t - \sqrt{1 - \bar\alpha_t}\,\varepsilon)/\sqrt{\bar\alpha_t}$$ |
| `p_mean_variance` | $$\frac{1}{\sqrt{\alpha_t}}\big(x_t - \frac{\beta_t}{\sqrt{1 - \bar\alpha_t}}\varepsilon\big)$$, variance $$\tilde\beta_t$$ |

$$\bar\alpha_{t-1}$$ là `cat([1], alpha_bar[:-1])`: tại `t = 0` nó bằng 1, nên hệ số của $$x_0$$ là $$\beta_0/(1 - \bar\alpha_0) = 1$$, hệ số của $$x_t$$ là 0 và
variance là 0: bước cuối của sampler trả đúng $$\hat x_0$$, không cộng nhiễu.

**Cosine.** Nichol và Dhariwal định nghĩa trực tiếp $$\bar\alpha$$ rồi suy $$\beta$$ từ tỉ số liên tiếp. Chuẩn hoá cho $$f(0)$$ không đổi $$\beta$$ (tỉ số liên
tiếp không đổi khi nhân cả dãy với một hằng), nhưng làm $$\bar\alpha$$ "trước bước 0" bằng đúng 1. Chặn $$\beta \le 0.999$$ cần thiết vì ở cuối
$$f(T) \approx 0$$ và tỉ số tiến về 0, $$\beta$$ tiến về 1: không chặn thì bước cuối của sampler chia cho $$\sqrt{\alpha_T} \approx 0$$.

## Vì sao test kiểm theo cách khác

- **Dạng đóng và chuỗi Markov**: test chạy 200 000 chuỗi $$x_t = \sqrt{1 - \beta}\,x_{t-1} + \sqrt\beta\,\varepsilon$$ qua 8 bước rồi so mean, phương sai với
  `q_sample` ở bước cuối. Dùng $$\bar\alpha$$ thay $$\sqrt{\bar\alpha}$$ (lỗi hay gặp nhất) làm mean lệch hẳn.
- **Posterior bằng Bayes**: $$q(x_{t-1} \mid x_t, x_0) \propto q(x_t \mid x_{t-1})\,q(x_{t-1} \mid x_0)$$, tích hai Gauss theo $$x_{t-1}$$: độ chính xác cộng lại
  $$\frac{1}{1 - \bar\alpha_{t-1}} + \frac{\alpha_t}{\beta_t}$$, mean là trung bình có trọng số theo độ chính xác. Test tính theo cách này, độc lập với công thức
  trong bảng; lệch chỉ số $$\bar\alpha_{t-1}$$ (dùng $$\bar\alpha_t$$) hay dùng $$\beta_t$$ làm variance đều bị bắt.
- **Mean theo nhiễu** được kiểm bằng tính nhất quán: với nhiễu thật, `p_mean_variance` phải trùng `q_posterior`.

## Số đo (dùng ở mục 5 lý thuyết)

Linear $$T = 1000$$: $$\sqrt{\bar\alpha}$$ tại `t` 0/99/249/499/749/999 là 0.9999 / 0.947 / 0.724 / 0.280 / 0.058 / 0.0064; $$\bar\alpha_{999} = 4.04 \times 10^{-5}$$; 32.6%
số bước có SNR dưới -20 dB. Cosine: 1.000 / 0.986 / 0.920 / 0.703 / 0.380 / 0.000, $$\bar\alpha_{999} = 2.4 \times 10^{-9}$$, 6.4% số bước dưới -20 dB.
