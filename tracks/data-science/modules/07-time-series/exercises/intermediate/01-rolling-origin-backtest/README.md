---
title: Tự viết backtest rolling origin
level: intermediate
services: []
files:
  - path: starter/backtest.py
    note: 4 hàm TODO
  - path: tests/test_backtest.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/07-time-series/exercises/intermediate/01-rolling-origin-backtest -q
---

## Mục tiêu

Viết engine backtest mà mọi so sánh model dự báo trong module này dựa vào: nhiều origin, expanding
hoặc sliding window, không bao giờ cho model nhìn thấy tương lai. Sau bài này bạn đọc được
`TimeSeriesSplit` của sklearn hay `cross_validation` của Prophet và biết chúng khác nhau ở đâu.

## Đề bài

Trong `starter/backtest.py`; `forecast_fn(train: np.ndarray, horizon: int) -> array`:

1. `rolling_origin_splits(n, initial, horizon, step=1, window=None)`: list `(train_idx, test_idx)`
   theo vị trí. Origin đầu ở `initial` (train là `0..initial-1`), dời `step` mỗi lần, chỉ giữ
   split đủ `horizon` điểm test. `window=None` là expanding; `window=k` chỉ giữ `k` điểm train gần
   nhất. `ValueError` nếu không có split nào hoặc `window > initial`.
2. `backtest(y, forecast_fn, initial, horizon, step=1, window=None)`: DataFrame cột
   `cutoff, h, y_true, y_pred` (`cutoff` là vị trí điểm test đầu, `h` từ 1). `forecast_fn` chỉ được
   nhận **bản sao** train: model sửa mảng đầu vào cũng không được làm hỏng dữ liệu gốc.
3. `error_by_horizon(results)`: MAE theo từng `h`.
4. `compare(y, forecasters, initial, horizon, step=1, window=None, m=1)`: bảng index là tên model,
   cột `mae`, `mase`, sắp tăng theo `mase`. MASE của mỗi origin dùng mẫu số tính trên train **của
   origin đó**, rồi lấy trung bình qua các origin.

## Tiêu chí đạt

- Split đúng số lượng, đúng vị trí, không chồng lấn train/test; sliding window đúng độ dài.
- Forecaster chỉ thấy dữ liệu trước origin, và không sửa được dữ liệu gốc.
- Với random walk và dự báo naive, MAE ở bước 10 xấp xỉ $$\sqrt{10}$$ lần MAE ở bước 1.
- `compare` xếp seasonal naive trên naive ở chuỗi mùa vụ tuần; MASE theo từng origin đúng ví dụ tính tay.

## Gợi ý

### Gợi ý 1

`range(initial, n - horizon + 1, step)` cho mọi origin hợp lệ.

### Gợi ý 2

Vì sao MASE tính theo từng origin: mức của chuỗi thay đổi theo thời gian (Olist năm 2018 gấp gần 3
lần đầu 2017). Chia cho một mẫu số chung làm các origin sau có trọng số lớn hơn mà không có lý do.
