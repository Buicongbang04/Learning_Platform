---
title: CLT trên giá trị đơn Olist - "n ≥ 30" có đủ không?
level: intermediate
services: []
files:
  - path: starter/clt.ipynb
    note: 3 hàm TODO + phần kết luận
  - path: tests/test_clt.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/02-probability-statistics/exercises/intermediate/01-clt-order-value/starter/clt.ipynb
  - uv run pytest tracks/data-science/modules/02-probability-statistics/exercises/intermediate/01-clt-order-value -q
---

## Mục tiêu

Thấy tận mắt Law of Large Numbers và Central Limit Theorem trên dữ liệu thật lệch phải, và đo bằng
mô phỏng xem quy tắc "n ≥ 30 là đủ để dùng phân phối chuẩn" sai bao nhiêu. Đây là kỹ năng kiểm tra
giả định mà DS senior làm trước khi tin một khoảng tin cậy.

## Đề bài

Giá trị đơn là tổng `price + freight_value` của mọi item trong một đơn giao xong (96 470 đơn). Coi
96 470 đơn này là **tổng thể**, lấy mẫu có hoàn lại từ đó. Mở `starter/clt.ipynb`:

1. Chạy các cell `explore` đầu: mean, median, skewness, phần doanh thu của 1% đơn lớn nhất; đồ thị
   trung bình chạy (LLN).
2. `sample_means(x, n, n_sims=2000, seed=0)`: `n_sims` trung bình mẫu, vector hoá.
3. `t_interval_coverage(x, n, n_sims=2000, seed=0, alpha=0.05)`: tỉ lệ khoảng t chứa `x.mean()`.
4. `min_n_for_coverage(x, ns, target=0.93, n_sims=2000, seed=0)`: n nhỏ nhất trong `ns` đạt
   coverage ≥ target, hoặc `None`.
5. Viết kết luận 4–6 câu trong cell markdown cuối (không chấm tự động; so với lời giải mẫu).

## Tiêu chí đạt

- `sample_means` tái lập được theo seed, tâm và độ phân tán khớp lý thuyết (σ/√n).
- Skewness của trung bình mẫu giảm khi n tăng.
- Coverage gần 95% với tổng thể chuẩn, dưới 78% với tổng thể Lognormal(0, 1.5) ở n = 10.
- `min_n_for_coverage` duyệt `ns` theo thứ tự tăng dần, trả `None` khi không đạt.
- Trên Olist thật: coverage ở n = 30 trong khoảng 80–89%, ở n = 2000 ít nhất 92%.

## Gợi ý

### Gợi ý 1

`idx = rng.integers(0, len(x), size=(n_sims, n))` rồi `x[idx]` là ma trận mẫu; `.mean(axis=1)` và
`.std(axis=1, ddof=1)` cho trung bình và độ lệch chuẩn từng mẫu. Nửa độ rộng khoảng t là
`stats.t.ppf(1 - alpha/2, n - 1) * s / sqrt(n)`.

### Gợi ý 2

Lý thuyết cho skewness của trung bình mẫu:

$$
\operatorname{skew}(\bar X_n) = \frac{\operatorname{skew}(X)}{\sqrt{n}}
$$

Với skew(X) ≈ 9.4, muốn skewness của trung bình dưới 0.3 thì cần n cỡ 1 000. Quy tắc "30" chỉ
đúng cho phân phối gần đối xứng.
