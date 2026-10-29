---
title: Tự tính xác suất từ Binomial, Poisson và Lognormal
level: basic
services: []
files:
  - path: starter/distributions.py
    note: 5 hàm TODO
  - path: tests/test_distributions.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/02-probability-statistics/exercises/basic/01-distributions -q
---

## Mục tiêu

Tự viết các hàm xác suất mà bạn sẽ gọi bằng `scipy.stats` cả đời, để biết chúng tính gì, chỗ nào
tràn số, và cách kiểm tra nhanh một giả định phân phối (Poisson) trên dữ liệu đếm thật.

## Đề bài

Trong `starter/distributions.py`, chỉ dùng `math` và `numpy`:

1. `binom_pmf(k, n, p)`: xác suất đúng k đơn trễ trong n đơn. Với tỉ lệ trễ thật của Olist (8.1%),
   một seller giao 20 đơn mà không có đơn nào trễ thì xác suất là bao nhiêu?
2. `prob_at_least(k, n, p)`: xác suất có ít nhất k đơn trễ. Seller có 3 đơn trễ trên 20 có "tệ bất
   thường" không?
3. `poisson_pmf(k, lam)`: chạy đúng cả khi `lam = 250, k = 300`. Gợi ý: làm trên log.
4. `lognormal_from_mean_median(mean, median) -> (mu, sigma)`: dựng một Lognormal khớp mean và median
   cho trước (giá trị đơn Olist: mean 159.83, median 105.28 BRL). Báo `ValueError` nếu
   `mean <= median`.
5. `dispersion_index(counts)`: `var(ddof=1) / mean`. Poisson có tỉ số này gần 1; lớn hơn nhiều là
   **overdispersion**.

Các công thức:

$$
P(X = k) = \binom{n}{k} p^k (1-p)^{n-k},
\qquad
P(N = k) = \frac{\lambda^k e^{-\lambda}}{k!},
\qquad
\text{median} = e^{\mu},\ \text{mean} = e^{\mu + \sigma^2/2}
$$

## Tiêu chí đạt

- `binom_pmf`, `prob_at_least`, `poisson_pmf` khớp `scipy.stats` tới sai số tương đối 1e-9, kể cả
  `poisson_pmf(300, 250)`.
- `lognormal_from_mean_median` cho đúng median và mean khi dựng lại phân phối; báo lỗi khi mean ≤ median.
- `dispersion_index` gần 1 với dữ liệu Poisson và lớn hơn 3 với hỗn hợp Poisson có λ thay đổi.

## Gợi ý

### Gợi ý 1

`math.comb(n, k)` cho hệ số nhị thức. `math.lgamma(k + 1)` bằng `log(k!)` mà không tính `k!`.
`prob_at_least(0, n, p)` là 1.

### Gợi ý 2

Từ hai phương trình `median = exp(mu)` và `mean = exp(mu + sigma²/2)`: lấy log rồi trừ vế theo vế,
`sigma = sqrt(2 (log(mean) − log(median)))`.
