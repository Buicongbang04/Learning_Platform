---
title: Fit phân phối cho giá trị đơn Olist - MLE, QQ-plot, KS test
level: intermediate
services: []
files:
  - path: starter/distribution.ipynb
    note: 5 hàm TODO + khuyến nghị
  - path: tests/test_distribution.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/05-econometrics-regression/exercises/intermediate/03-order-value-distribution/starter/distribution.ipynb
  - uv run pytest tracks/data-science/modules/05-econometrics-regression/exercises/intermediate/03-order-value-distribution -q
---

## Mục tiêu

Fit phân phối tham số cho dữ liệu kinh doanh thật, so sánh bằng nhiều công cụ, và học bài học quan
trọng nhất của phần này: phân phối "thắng" về tổng thể có thể sai hoàn toàn ở phần mà quyết định
kinh doanh phụ thuộc vào.

## Đề bài

Mở `starter/distribution.ipynb`, làm theo thứ tự:

1. `order_values(items, orders) -> Series`: tổng `price` + `freight_value` mỗi đơn giao xong.
2. `fit_lognormal(x) -> (mu, sigma)`: MLE nghiệm đóng.
3. `fit_gamma(x) -> (shape, scale)`: MLE với `loc = 0`.
4. `compare_fits(x, threshold=1000.0) -> DataFrame`: index `["lognorm", "gamma"]`, cột `loglik`,
   `aic`, `ks_stat`, `p_exceed` (xác suất model gán cho giá trị vượt `threshold`).
5. `qq_points(x, dist, params) -> (theoretical, sample)` với vị trí $$p_i = (i - 0.5)/n$$.
6. Chạy các cell `explore` (histogram, QQ-plot, KS trên toàn bộ và trên 500 đơn), rồi viết khuyến
   nghị 4–6 câu cho đội tài chính trong cell markdown cuối.

## Tiêu chí đạt

- MLE lognormal khớp nghiệm đóng và `scipy.stats.lognorm.fit(floc=0)`; MLE gamma khớp
  `scipy.stats.gamma.fit(floc=0)` và giữ đúng trung bình mẫu.
- `compare_fits` chọn đúng phân phối trên dữ liệu mô phỏng; `aic`, `ks_stat`, `p_exceed` khớp scipy.
- `qq_points` sắp xếp đúng, dùng đúng vị trí quantile.
- Trên Olist thật: 96 470 đơn, $$\hat\mu \approx 4.691$$, $$\hat\sigma \approx 0.808$$, lognormal có
  AIC thấp hơn gamma, nhưng P(X > 1 000) theo lognormal nhỏ hơn 1/3 tỉ lệ thực tế.
- Khuyến nghị phân biệt được dùng cho thân (doanh thu) và dùng cho đuôi (đơn lớn).

## Gợi ý

### Gợi ý 1

`stats.lognorm` của scipy tham số hoá lạ: `s` là $$\sigma$$, `scale` là $$e^{\mu}$$, `loc` là dịch
chuyển (để 0). Tạo phân phối "đóng băng" một lần, `dist = stats.lognorm(s=sigma, scale=np.exp(mu))`,
rồi dùng `dist.logpdf`, `dist.cdf`, `dist.sf`, `dist.ppf`.

### Gợi ý 2

`stats.kstest(x, dist.cdf).statistic` cho KS statistic với một CDF bất kỳ. Với gamma, quên `floc=0`
thì scipy fit thêm `loc` và thường cho shape vô nghĩa.
