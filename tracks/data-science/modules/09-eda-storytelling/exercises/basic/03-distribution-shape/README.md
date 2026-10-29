---
title: Hình dạng phân phối, thang log và số bins
level: basic
services: []
files:
  - path: starter/distribution.py
    note: 4 hàm TODO
  - path: tests/test_distribution.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run pytest tracks/data-science/modules/09-eda-storytelling/exercises/basic/03-distribution-shape -q
---

## Mục tiêu

Tóm tắt một biến số đúng cách (hình dạng trước, trung bình sau) và biến các quyết định vẽ
histogram (thang tuyến tính hay log, bao nhiêu bins) thành quy tắc có thể kiểm thử.

## Đề bài

Trong `starter/distribution.py`, cài theo docstring:

1. `shape_summary(s) -> dict`: `n`, `n_missing`, `mean`, `median`, `std`, `skew`, `p01`, `p99`,
   `zero_share`, `tail_ratio` (= p99 / median, NaN nếu median ≤ 0). Mọi thống kê trên phần không
   thiếu, dùng mặc định của pandas.
2. `suggest_scale(s, tail_threshold=10) -> str`, xét theo thứ tự: có số âm → `"linear"`; `tail_ratio`
   không xác định hoặc nhỏ hơn ngưỡng → `"linear"`; có số 0 → `"log1p"`; còn lại → `"log"`.
3. `fd_bins(s) -> int`: số bins Freedman–Diaconis với độ rộng
   $$h = 2\,\mathrm{IQR}\,n^{-1/3}$$ và số bins $$\lceil (\max - \min)/h \rceil$$. IQR bằng 0 thì
   dùng Sturges $$\lceil \log_2 n \rceil + 1$$. Khi IQR > 0, kết quả phải khớp `np.histogram_bin_edges(x, "fd")`; khi IQR = 0 bài dùng Sturges
   (numpy xử lý trường hợp này khác).
4. `ecdf(s) -> DataFrame` cột `x` (sắp tăng, bỏ NaN) và `y = i/n`.

Sau khi xong, chạy trên `price`, `freight_value` (bảng items) và `payment_value` (bảng payments) của
Olist thật. Trả lời:

- Vì sao giá item cần thang log còn phí vận chuyển thì không?
- `fd_bins` cho bao nhiêu bins với `price` trên thang tuyến tính, và bao nhiêu với `log10(price)`?
  Con số nào vẽ được một histogram đọc được?
- Phần trăm item có giá không quá 100 BRL là bao nhiêu (đọc từ ECDF)?

## Tiêu chí đạt

- `shape_summary` đúng mọi khoá trên dữ liệu nhỏ, `tail_ratio` là NaN khi median không dương.
- `suggest_scale` đúng thứ tự quy tắc, kể cả ngưỡng tuỳ chỉnh.
- `fd_bins` khớp numpy trên nhiều phân phối có IQR > 0, bỏ NaN, dùng Sturges khi IQR = 0.
- `ecdf` sắp đúng và bỏ NaN.
- Trên Olist thật: giá median 74.99, p99 890, `tail_ratio` ≈ 11.87 → `"log"`; phí vận chuyển →
  `"linear"`; `payment_value` → `"log1p"`; `fd_bins(price) = 1712`.

## Gợi ý

### Gợi ý 1

`x = s.dropna()` một lần ở đầu. `x.quantile([0.01, 0.99])` trả Series hai phần tử. `skew()` của
pandas là skewness đã hiệu chỉnh theo cỡ mẫu (không phải `scipy.stats.skew` mặc định).

### Gợi ý 2

numpy tính IQR bằng `np.percentile(x, [25, 75])` (nội suy tuyến tính, giống pandas) và làm tròn lên
số bins bằng `ceil`. Với ECDF: `np.sort` rồi `np.arange(1, n + 1) / n`.
