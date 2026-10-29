---
title: Tự cài z-test, khoảng tin cậy và Welch t-test
level: basic
services: []
files:
  - path: starter/stat_tests.py
    note: 3 hàm TODO
  - path: tests/test_stat_tests.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/03-ab-testing/exercises/basic/01-two-sample-tests -q
---

## Mục tiêu

Tự viết ba kiểm định dùng nhiều nhất trong A/B testing để hiểu chúng tính gì, thay vì gọi thư viện
như một hộp đen. Sau bài này bạn đọc được output của bất kỳ experimentation platform nào.

## Đề bài

Trong `starter/stat_tests.py`, mọi chênh lệch tính theo hướng **B − A** (treatment − control):

1. `two_proportion_ztest(x_a, n_a, x_b, n_b) -> (z, p_value)`: z-test hai tỉ lệ, **pooled**
   (giả định H0 là hai tỉ lệ bằng nhau), hai phía.
2. `diff_proportion_ci(x_a, n_a, x_b, n_b, alpha=0.05) -> (lo, hi)`: khoảng tin cậy Wald cho
   `p_b − p_a`, **không pooled** (vì không còn giả định H0).
3. `welch_ttest(a, b) -> (t, p_value)`: Welch t-test hai phía cho `mean(b) − mean(a)`, variance
   mẫu dùng `ddof=1`, bậc tự do Welch-Satterthwaite.

Được dùng `numpy`, `scipy.stats.norm`, `scipy.stats.t`. Không dùng hàm kiểm định dựng sẵn; test sẽ
so kết quả của bạn với `statsmodels` và `scipy` tới sai số 1e-9.

Test dùng cả số thật: retention 7 ngày của Cookie Cats (8 502/44 700 và 8 279/45 489) và
conversion của bộ ab_data sau khi làm sạch.

## Tiêu chí đạt

- Kết quả z, p, CI, t khớp `statsmodels` / `scipy` tới 1e-9 trên mọi bộ số trong test.
- Dấu của z và t đi theo hướng B − A.
- CI 99% rộng hơn CI 95%.
- Welch cho p-value khác Student t-test khi hai nhóm khác variance và khác cỡ mẫu.

## Gợi ý

### Gợi ý 1

p-value hai phía từ thống kê chuẩn: `2 * norm.sf(abs(z))`. Từ phân phối t: `2 * t.sf(abs(stat), df)`.
`sf` (survival function) chính xác hơn `1 - cdf` khi p rất nhỏ.

### Gợi ý 2

Đặt `va = var(a, ddof=1) / n_a`, `vb = var(b, ddof=1) / n_b`. Khi đó
`t = (mean_b − mean_a) / sqrt(va + vb)` và
`df = (va + vb)² / (va² / (n_a − 1) + vb² / (n_b − 1))`.
