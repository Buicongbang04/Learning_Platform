---
title: Bootstrap CI cho median thời gian giao theo bang
level: intermediate
services: []
files:
  - path: starter/bootstrap.ipynb
    note: 5 hàm TODO + phần nhận xét
  - path: tests/test_bootstrap.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/02-probability-statistics/exercises/intermediate/02-bootstrap-median/starter/bootstrap.ipynb
  - uv run pytest tracks/data-science/modules/02-probability-statistics/exercises/intermediate/02-bootstrap-median -q
---

## Mục tiêu

Dựng khoảng tin cậy cho median, thống kê không có công thức SE gọn, bằng bootstrap và bằng CI chính
xác từ thống kê thứ tự; áp dụng cho dashboard "thời gian giao theo bang" và biết lúc nào bootstrap
hỏng.

## Đề bài

Thời gian giao = `order_delivered_customer_date − order_purchase_timestamp` (ngày, số thực) trên đơn
giao xong; bang lấy từ `customers.customer_state`. Mở `starter/bootstrap.ipynb`:

1. `bootstrap_stats(x, stat=np.median, n_boot=2000, seed=0)`: vector hoá, chia lô khi `x` lớn.
2. `percentile_ci(x, stat=np.median, n_boot=2000, seed=0, alpha=0.05)`.
3. `median_ci_exact(x, alpha=0.05)`: CI từ thống kê thứ tự (công thức trong notebook).
4. `ci_table(df, value, group, min_n=1, n_boot=2000, seed=0)`: bảng theo nhóm, cột
   `n, median, boot_lo, boot_hi, exact_lo, exact_hi`, sắp theo median giảm dần.
5. Chạy cell bootstrap cho max, rồi viết nhận xét 4–6 câu.

CI chính xác cho median: gọi B là số quan sát dưới median thật, B ~ Binomial(n, 0.5). Với j chọn
sao cho P(B ≤ j − 1) ≤ α/2:

$$
P\left(x_{(j)} \le \text{median} \le x_{(n-j+1)}\right) = 1 - 2P(B \le j-1) \ge 1 - \alpha
$$

## Tiêu chí đạt

- `bootstrap_stats` tái lập theo seed, chạy được với 100 nghìn quan sát × 2 000 lần.
- `percentile_ci` đúng bằng percentile của phân phối bootstrap; CI 90% nằm trong CI 95%.
- `median_ci_exact` đúng chỉ số thống kê thứ tự.
- Qua 200 lần mô phỏng, độ phủ của CI bootstrap trong khoảng 89–99%, của CI chính xác ít nhất 91%.
- `ci_table` đúng cấu trúc, lọc `min_n`, dùng cùng seed cho mọi nhóm.
- Trên Olist thật: RR có 41 đơn, median 25.01 ngày, CI chính xác [17.04, 30.19]; CI bootstrap của RR
  rộng hơn 10 ngày, của SP hẹp hơn 1 ngày.

## Gợi ý

### Gợi ý 1

`stat(x[idx], axis=1)` với `idx` có shape `(b, n)`. Số mẫu mỗi lô `b = max(1, 5_000_000 // n)`.
Một `rng` cho mọi lô, không tạo lại `rng` trong vòng lặp.

### Gợi ý 2

`stats.binom.ppf(alpha / 2, n, 0.5)` trả j nhỏ nhất có `P(B ≤ j) ≥ α/2`, nên `P(B ≤ j − 1) < α/2`.
Thống kê thứ tự thứ j (đánh số từ 1) là `xs[j - 1]` trong numpy; thứ n − j + 1 là `xs[n - j]`.
