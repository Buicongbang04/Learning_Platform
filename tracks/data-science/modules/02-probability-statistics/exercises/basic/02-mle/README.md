---
title: Tự viết Maximum Likelihood Estimation
level: basic
services: []
files:
  - path: starter/mle.py
    note: 6 hàm TODO
  - path: tests/test_mle.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/02-probability-statistics/exercises/basic/02-mle -q
---

## Mục tiêu

Hiểu MLE bằng cách tự làm cả hai đường: công thức đóng (lấy đạo hàm log-likelihood bằng 0) và tối ưu
số (cực tiểu negative log-likelihood). Mọi model ML phía sau (logistic regression, neural network
với cross-entropy) đều là đường thứ hai.

## Đề bài

Trong `starter/mle.py`:

1. `bernoulli_mle`, `poisson_mle`: công thức đóng.
2. `exponential_mle(x)`: trả **rate** λ, không phải scale = 1/λ (scipy dùng scale; nhầm hai thứ là
   lỗi hay gặp).
3. `lognormal_mle(x) -> (mu, sigma)`: trung bình và độ lệch chuẩn (`ddof=0`) của `log(x)`.
4. `lognormal_nll(mu, sigma, x)`: negative log-likelihood, là **tổng** trên các quan sát.
5. `fit_lognormal_numeric(x)`: dùng `scipy.optimize.minimize` cực tiểu `lognormal_nll`, tối ưu theo
   `(mu, log_sigma)` để sigma luôn dương, khởi đầu từ `(0, 0)`.

Log-likelihood của Lognormal:

$$
\ell(\mu, \sigma) = \sum_{i=1}^{n} \left[ -\log x_i - \log \sigma - \tfrac{1}{2}\log(2\pi) - \frac{(\log x_i - \mu)^2}{2\sigma^2} \right]
$$

## Tiêu chí đạt

- Ước lượng khớp `scipy.stats.*.fit` (loc cố định 0) tới 1e-6.
- `lognormal_nll` khớp `-lognorm.logpdf(...).sum()`.
- Lời giải dạng đóng là cực tiểu của NLL: dịch tham số theo bất kỳ hướng nào thì NLL tăng.
- Tối ưu số và công thức đóng khớp nhau tới 1e-3.

## Gợi ý

### Gợi ý 1

Exponential: `ℓ(λ) = n log λ − λ Σx`, đạo hàm bằng 0 cho `λ = n / Σx = 1 / mean(x)`.
`stats.lognorm` dùng tham số `s = sigma`, `scale = exp(mu)`.

### Gợi ý 2

```text
objective(theta) = lognormal_nll(theta[0], exp(theta[1]), x) / len(x)
```

Chia cho n để hàm mục tiêu có độ lớn cỡ 1, optimizer (BFGS mặc định) hội tụ ổn định hơn với dữ
liệu lớn.
