---
title: Bốn baseline mọi dự báo phải thắng
level: basic
services: []
files:
  - path: starter/baselines.py
    note: 4 hàm TODO
  - path: tests/test_baselines.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/07-time-series/exercises/basic/02-baseline-forecasts -q
---

## Mục tiêu

Viết naive, mean, drift và seasonal naive: bốn "model" không cần fit nhưng là thước đo bắt buộc.
Một model ARIMA hay LightGBM không thắng được seasonal naive trong backtest thì không có lý do để
tồn tại trong production.

## Đề bài

Trong `starter/baselines.py`, mỗi hàm nhận `y` (array-like, theo thứ tự thời gian) và `h`, trả
`np.ndarray` độ dài `h`:

1. `naive(y, h)`: lặp lại quan sát cuối.
2. `mean_forecast(y, h, window=None)`: trung bình toàn bộ lịch sử, hoặc của `window` điểm cuối.
3. `drift(y, h)`: kéo dài đường thẳng nối quan sát đầu và cuối,
   $$\hat y_{T+k} = y_T + k\,\frac{y_T - y_1}{T - 1}$$.
4. `seasonal_naive(y, h, m)`: lặp lại mùa vụ cuối, đúng pha với mọi `h` (kể cả `h > m` và chuỗi
   kết thúc giữa tuần). `ValueError` nếu chưa có đủ một mùa vụ.

## Tiêu chí đạt

- Đúng giá trị trên các ví dụ tính tay; drift khớp chính xác chuỗi tuyến tính.
- Seasonal naive đúng pha khi `h` không chia hết cho `m`.
- Nhận cả `pd.Series`.
- Trên chuỗi có mùa vụ tuần, seasonal naive có MAE nhỏ hơn 1/3 MAE của naive.

## Gợi ý

### Gợi ý 1

`y[-m:]` là mùa vụ cuối, phần tử đầu của nó ứng với bước dự báo 1, `m + 1`, `2m + 1`…

### Gợi ý 2

Chỉ số `np.arange(h) % m` lấy đúng phần tử trong mùa vụ cuối cho từng bước.
