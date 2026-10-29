---
title: SARIMA so với seasonal naive trên số đơn Olist mỗi ngày
level: intermediate
services: []
files:
  - path: starter/sarima.ipynb
    note: 5 hàm TODO + phần kết luận
  - path: tests/test_sarima.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/07-time-series/exercises/intermediate/02-olist-sarima-vs-naive/starter/sarima.ipynb
  - uv run pytest tracks/data-science/modules/07-time-series/exercises/intermediate/02-olist-sarima-vs-naive -q
---

## Mục tiêu

Làm trọn một vòng forecasting cổ điển trên dữ liệu thật: dựng chuỗi đúng, đọc cấu trúc (STL,
ADF/KPSS, ACF/PACF), fit SARIMA, và kiểm tra bằng backtest nhiều origin xem nó có thật sự thắng
baseline không.

## Đề bài

Chuỗi: số đơn Olist (mọi trạng thái) theo ngày mua, 2017-01-09 tới 2018-08-19. Mở
`starter/sarima.ipynb` và làm theo thứ tự:

1. `daily_orders(orders, start, end)`: Series float, index mọi ngày trong `[start, end]`, ngày không
   có đơn là 0.
2. Chạy các cell `explore`: STL, ADF/KPSS, ACF/PACF.
3. `seasonal_naive(train, h, m=7)` và `sarima_forecast(train, h)` với cấu hình cố định
   SARIMA(1,1,1)(0,1,1)[7].
4. `backtest_mase(series, forecasters, cutoffs, h=14, m=7)` và
   `summarize(table, baseline="seasonal_naive")` theo mô tả trong notebook.
5. Backtest 12 origin cách nhau 14 ngày từ 2018-03-04, viết kết luận cho đội vận hành.

## Tiêu chí đạt

- `daily_orders` điền đủ ngày; trên dữ liệu thật: 588 ngày, 97 845 đơn, cao nhất 1 176 đơn ngày
  2017-11-24 (Black Friday).
- `sarima_forecast` đúng model đề bài; thắng seasonal naive trên chuỗi mô phỏng có xu hướng.
- Backtest chỉ dùng quá khứ; MASE đúng mẫu số theo origin.
- Trên dữ liệu thật: MASE trung bình của seasonal naive 1.261, của SARIMA khoảng 1.19.
- Phần kết luận nói được mức thắng so với độ dao động giữa các origin (không chấm tự động).

## Gợi ý

### Gợi ý 1

`pd.to_datetime(...).dt.normalize().value_counts().reindex(pd.date_range(start, end), fill_value=0)`.

### Gợi ý 2

SARIMAX có thể báo `ConvergenceWarning` trên chuỗi có Black Friday. Bọc phần fit trong
`warnings.catch_warnings()`; kết quả vẫn dùng được, nhưng đó là dấu hiệu nên cân nhắc biến ngoại
sinh cho ngày đặc biệt.
