---
title: Đo bias và variance bằng mô phỏng
level: basic
services: []
files:
  - path: starter/bias_variance.py
    note: 3 hàm TODO
  - path: tests/test_bias_variance.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/11-classic-ml/exercises/basic/03-bias-variance -q
---

## Mục tiêu

Thấy bias-variance bằng số thay vì bằng hình minh hoạ: rút nhiều tập train từ cùng một "thế giới", fit cùng
một model, đo dự đoán lệch trung bình bao nhiêu (bias) và dao động bao nhiêu (variance).

## Đề bài

Thế giới: $$x \sim \text{Uniform}(0, 1)$$, $$y = f(x) + \varepsilon$$, $$\varepsilon \sim N(0, \sigma^2)$$.

Trong `starter/bias_variance.py`:

1. `simulate_predictions(fit_predict, f, x_test, n_train, noise_sd, n_rep, seed)`: lặp `n_rep` lần, mỗi lần
   rút một tập train mới cỡ `n_train`, gọi `fit_predict(x_train, y_train, x_test)`. Trả mảng
   `(n_rep, len(x_test))`. Một `np.random.default_rng(seed)` cho cả lần chạy.
2. `decompose(preds, f_test, noise_sd)`: dict `bias2`, `variance`, `noise`, `expected_mse`, trung bình trên các
   điểm test:

   $$
   \text{bias}^2 = \overline{\big(\bar{\hat f}(x) - f(x)\big)^2}, \qquad
   \text{variance} = \overline{\mathrm{Var}_{\text{rep}}\big(\hat f(x)\big)}, \qquad
   \text{expected\_mse} = \text{bias}^2 + \text{variance} + \sigma^2
   $$

3. `knn_fit_predict(k)`: trả một hàm `fit_predict` dùng `KNeighborsRegressor(k)`.

## Tiêu chí đạt

- Cùng seed cùng kết quả; mỗi lần lặp một tập train mới đúng cỡ.
- `bias2 + variance` bằng đúng MSE trung bình giữa dự đoán và f.
- Model hằng số (dự đoán trung bình y) có bias² ≈ trung bình f² và variance nhỏ.
- kNN với k = 1 có variance gấp hơn 3 lần k = 30; k = 30 có bias² gấp hơn 3 lần k = 1; k = 7 có tổng sai số
  nhỏ hơn cả hai.

## Gợi ý

### Gợi ý 1

`preds.mean(axis=0)` là dự đoán trung bình tại mỗi điểm test; `preds.var(axis=0)` là variance tại mỗi điểm
(ddof = 0). Lấy trung bình trên các điểm.

### Gợi ý 2

`KNeighborsRegressor` cần X hai chiều: `x.reshape(-1, 1)`. `knn_fit_predict(k)` trả một hàm lồng (closure)
dùng biến `k` của hàm ngoài.
