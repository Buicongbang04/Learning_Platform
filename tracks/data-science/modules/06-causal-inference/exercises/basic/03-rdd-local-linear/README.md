---
title: Regression Discontinuity bằng local linear
level: basic
services: []
files:
  - path: starter/rdd.py
    note: 3 hàm TODO
  - path: tests/test_rdd.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/06-causal-inference/exercises/basic/03-rdd-local-linear -q
---

## Mục tiêu

Tự cài ước lượng RDD chuẩn (local linear, kernel tam giác), thấy vì sao bandwidth là đánh đổi
bias–variance, và viết kiểm tra manipulation đơn giản nhất: có ai "chen" qua ngưỡng không.

## Đề bài

Bối cảnh: một sàn thương mại điện tử tặng gói "seller ưu tiên" cho seller có điểm chất lượng
`x >= 0` (điểm đã chuẩn hoá về khoảng [−1, 1]). Muốn biết gói này làm doanh thu `y` tăng bao nhiêu.
Seller ngay trên và ngay dưới ngưỡng gần như giống nhau, nên bước nhảy của `E[y | x]` tại ngưỡng là
tác động của gói (với seller quanh ngưỡng).

Trong `starter/rdd.py`:

1. `rdd_estimate(x, y, cutoff, bandwidth) -> (estimate, se)`: hồi quy WLS
   `y ~ 1 + d + r + d·r` trên cửa sổ `|r| < bandwidth`, với `r = x − cutoff`, `d = 1{r >= 0}`, trọng
   số tam giác `1 − |r| / bandwidth`, SE HC1. Trả hệ số của `d`.
2. `bandwidth_sensitivity(x, y, cutoff, bandwidths) -> DataFrame` cột `bandwidth, estimate, se, n`.
3. `density_check(x, cutoff, width) -> p_value`: binomial test hai phía cho số quan sát ngay bên
   phải trên tổng số quan sát hai bên, trong cửa sổ rộng `width` mỗi bên.

Dữ liệu trong test là mô phỏng: bước nhảy thật là 0.3, và bên phải ngưỡng `E[y | x]` cong.

## Tiêu chí đạt

- `rdd_estimate` khớp `statsmodels.WLS` tới 1e-8.
- Bandwidth 0.2 tìm lại bước nhảy 0.3 (sai số dưới 0.12) qua 5 seed; bandwidth 1.0 (gần như hồi quy
  tuyến tính toàn cục) bị đường cong kéo lệch xuống dưới 0.2.
- Bảng độ nhạy đúng cột; bandwidth hẹp có SE lớn hơn.
- `density_check` đúng trên ví dụ 8 điểm và phát hiện được khi 30% người ngay dưới ngưỡng đẩy được
  điểm lên ngay trên ngưỡng (p < 0.001).

## Gợi ý

### Gợi ý 1

Tạo ma trận thiết kế bằng `np.column_stack([np.ones_like(r), d, r, d * r])`, rồi
`sm.WLS(y, X, weights=w).fit(cov_type="HC1")`. Hệ số thứ hai (`params[1]`) là bước nhảy, vì tại
`r = 0` hai đường hồi quy cách nhau đúng bằng hệ số của `d`.

### Gợi ý 2

Cửa sổ bên trái là `[cutoff − width, cutoff)`, bên phải là `[cutoff, cutoff + width)`.
`scipy.stats.binomtest(k_right, n_total, 0.5).pvalue`. Kiểm tra này chỉ hợp lý khi mật độ của x gần
như phẳng quanh ngưỡng; công cụ đầy đủ là McCrary test hoặc `rddensity` (Cattaneo, Jansson, Ma),
ước lượng mật độ bằng local polynomial mỗi bên.
