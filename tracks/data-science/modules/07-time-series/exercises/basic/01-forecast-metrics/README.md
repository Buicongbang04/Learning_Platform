---
title: Tự cài metric dự báo, từ MAE tới MASE
level: basic
services: []
files:
  - path: starter/metrics.py
    note: 5 hàm TODO
  - path: tests/test_metrics.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/07-time-series/exercises/basic/01-forecast-metrics -q
---

## Mục tiêu

Tự viết năm metric hay dùng nhất khi chấm dự báo để biết mỗi cái phạt điều gì, hỏng ở đâu (MAPE khi
có số 0, sMAPE bất đối xứng) và vì sao MASE là lựa chọn mặc định khi so model trên nhiều chuỗi.

## Đề bài

Trong `starter/metrics.py`, mọi hàm nhận array-like và trả `float`:

1. `mae(y_true, y_pred)`, `rmse(y_true, y_pred)`.
2. `mape(y_true, y_pred)`: dạng **tỉ lệ** (giống sklearn), `ValueError` nếu `y_true` có số 0.
3. `smape(y_true, y_pred)`: trung bình của $$2|y - \hat y| / (|y| + |\hat y|)$$, nằm trong
   $$[0, 2]$$; cặp $$y = \hat y = 0$$ tính là 0.
4. `mase(y_true, y_pred, y_train, m=1)`: MAE của dự báo chia cho MAE in-sample của seasonal naive
   bậc `m` trên `y_train`. `ValueError` nếu mẫu số bằng 0.

$$
\mathrm{MASE} = \frac{\frac{1}{H}\sum_{h=1}^{H} |y_{T+h} - \hat y_{T+h}|}{\frac{1}{T-m}\sum_{t=m+1}^{T} |y_t - y_{t-m}|}
$$

## Tiêu chí đạt

- MAE, RMSE, MAPE khớp `sklearn.metrics`.
- MAPE báo lỗi khi có số 0 và thể hiện tính bất đối xứng (dự báo thấp bị chặn ở 100%, dự báo cao
  không có trần).
- sMAPE đúng công thức, xử lý 0/0, trần là 2.
- MASE đúng trên ví dụ tính tay, đúng với `m = 7`, bằng 1 khi chính seasonal naive in-sample được
  chấm, không đổi khi nhân cả chuỗi với một hằng số.

## Gợi ý

### Gợi ý 1

`np.asarray(x, dtype=float)` ở đầu mỗi hàm để nhận cả list lẫn `pd.Series` (và tránh căn index
của pandas khi trừ hai Series có index khác nhau).

### Gợi ý 2

Với sMAPE, `np.divide(a, b, out=np.zeros_like(b), where=b > 0)` chia an toàn mà không sinh cảnh
báo chia cho 0.
