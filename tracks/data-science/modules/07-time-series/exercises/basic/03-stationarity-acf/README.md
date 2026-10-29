---
title: Sai phân, ACF và đọc ADF cùng KPSS
level: basic
services: []
files:
  - path: starter/stationarity.py
    note: 6 hàm TODO
  - path: tests/test_stationarity.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/07-time-series/exercises/basic/03-stationarity-acf -q
---

## Mục tiêu

Biết biến một chuỗi có xu hướng thành chuỗi dừng (và đưa dự báo về mức gốc), tự tính ACF, và kết
hợp hai kiểm định có giả thuyết ngược nhau (ADF, KPSS) thành một kết luận dùng được.

## Đề bài

Trong `starter/stationarity.py`:

1. `difference(y, lag=1)` và `inverse_difference(diff_forecast, history, lag=1)`: sai phân, và
   dựng lại mức gốc từ dự báo trên chuỗi đã sai phân.
2. `acf(y, nlags)`: tự viết bằng numpy, cùng định nghĩa với `statsmodels.tsa.stattools.acf`:

$$
r_k = \frac{\sum_{t=k+1}^{T} (y_t - \bar y)(y_{t-k} - \bar y)}{\sum_{t=1}^{T} (y_t - \bar y)^2}
$$

3. `verdict(adf_p, kpss_p, alpha=0.05)`: theo bảng 4 trường hợp dưới đây.
4. `stationarity_report(y, alpha=0.05)`: dict `adf_p`, `kpss_p`, `verdict`, dùng
   `adfuller(y, autolag="AIC", result_object=False)` và
   `kpss(y, regression="c", nlags="auto", result_object=False)`.
5. `n_diffs(y, max_d=2, alpha=0.05)`: số lần sai phân nhỏ nhất để KPSS không bác bỏ stationarity.

| ADF (H0: có unit root) | KPSS (H0: stationary) | `verdict` | Làm gì |
| --- | --- | --- | --- |
| bác bỏ (p < α) | không bác bỏ | `stationary` | dùng trực tiếp |
| không bác bỏ | bác bỏ | `non_stationary` | sai phân |
| không bác bỏ | không bác bỏ | `trend_stationary` | bỏ xu hướng (detrend) |
| bác bỏ | bác bỏ | `difference_stationary` | sai phân, kiểm lại |

## Tiêu chí đạt

- Sai phân và phép ngược khớp nhau (cả `lag = 7`).
- ACF khớp statsmodels tới 1e-10; chuỗi mùa vụ tuần có đỉnh ACF ở lag 7 hoặc 14.
- `verdict` đúng cả 4 trường hợp và theo `alpha`.
- Trên 20 chuỗi mô phỏng mỗi loại: random walk là `non_stationary`, white noise là `stationary`,
  `n_diffs` cho 0 / 1 / 2 với white noise / random walk / tích luỹ của random walk, ít nhất 15/20
  lần. Không đòi 20/20: mỗi kiểm định sai 5% số lần theo đúng thiết kế.

## Gợi ý

### Gợi ý 1

Phép ngược của sai phân bậc `lag`: mức ở bước `k` bằng sai phân dự báo ở bước `k` cộng mức ở
bước `k − lag`. Giữ một list gồm `lag` quan sát cuối của `history`, rồi nối dần.

### Gợi ý 2

KPSS cảnh báo `InterpolationWarning` khi p nằm ngoài bảng tra (p bị chặn ở 0.01 hoặc 0.1). Bọc
lời gọi trong `warnings.catch_warnings()` + `warnings.simplefilter("ignore")`.
