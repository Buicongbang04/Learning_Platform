---
title: Beta-Binomial - so tỉ lệ review xấu giữa các category ít đơn
level: intermediate
services: []
files:
  - path: starter/bayes.py
    note: 6 hàm TODO
  - path: tests/test_bayes.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run pytest tracks/data-science/modules/02-probability-statistics/exercises/intermediate/03-beta-binomial-categories -q
---

## Mục tiêu

Xếp hạng category theo tỉ lệ review xấu mà không bị những category 2 đơn, 7 đơn đứng đầu / cuối bảng
chỉ vì may rủi. Bạn dùng Bayesian Beta-Binomial với prior ước lượng từ chính dữ liệu (empirical
Bayes), kỹ thuật dùng hằng ngày cho rating sản phẩm, CTR quảng cáo, tỉ lệ lỗi theo seller.

## Đề bài

Trong `starter/bayes.py`:

1. `category_counts(orders, reviews, items, products, translation)`: số đơn có review `n` và số
   review xấu `bad` theo category tiếng Anh. Dùng đúng định nghĩa chung của track (đơn giao xong,
   review mới nhất, review xấu là score ≤ 2). Category của đơn là category của item
   `order_item_id == 1`. Đọc `product_category_name_translation.csv` với `encoding="utf-8-sig"`.
2. `beta_posterior(a, b, k, n)` và `credible_interval(a, b, level=0.95)`.
3. `fit_beta_prior(k, n)`: method of moments theo docstring.
4. `prob_greater(a1, b1, a2, b2, n_draws=200_000, seed=0)`: Monte Carlo.
5. `shrinkage_table(counts, a, b, level=0.95)`: thêm `raw_rate, post_mean, ci_lo, ci_hi`, sắp theo
   `post_mean` giảm dần.

Prior Beta(a, b), quan sát k review xấu trên n đơn:

$$
p \sim \mathrm{Beta}(a, b),\quad k \mid p \sim \mathrm{Binomial}(n, p)
\;\Longrightarrow\;
p \mid k \sim \mathrm{Beta}(a + k,\ b + n - k),
\qquad
\mathbb{E}[p \mid k] = \frac{a + k}{a + b + n}
$$

Sau đó, trong một notebook hoặc script riêng (không chấm), trả lời: category nào thật sự tệ nhất?
`fashion_male_clothing` (24/105 xấu) có tệ hơn `bed_bath_table` (1 427/9 072) không?

## Tiêu chí đạt

- Các hàm Bayesian khớp công thức / `scipy.stats.beta`; `prob_greater` sai số dưới 0.005 so với tích phân số.
- `fit_beta_prior` khôi phục được prior thật trên dữ liệu mô phỏng; báo `ValueError` khi không có dị
  biệt giữa nhóm.
- `category_counts` đúng trên dữ liệu nhỏ (lọc đơn, dedupe review, bỏ đơn thiếu category).
- Trên Olist thật: 71 category, 94 455 đơn; prior mean ≈ 12.75%; đứng đầu bảng theo posterior là
  `office_furniture`; `security_and_services` (1/2) co về dưới 14%.

## Gợi ý

### Gợi ý 1

`a + b` là "số đơn ảo" mà prior đóng góp. Category có n nhỏ hơn nhiều so với `a + b` thì posterior
gần như bằng prior; n lớn hơn nhiều thì posterior gần tỉ lệ thô. Kiểm tra trực giác này trên kết quả.

### Gợi ý 2

`s2` trong `fit_beta_prior` gồm hai phần: phương sai thật giữa các category (`tau2`) và nhiễu
Binomial (mỗi category đóng góp khoảng `m(1 − m)/n_i`, nhân trọng số `n_i` rồi chia tổng n). Trừ
phần nhiễu đi mới được `tau2`. Rồi khớp moment: Beta(a, b) có variance `m(1 − m)/(a + b + 1)`.
