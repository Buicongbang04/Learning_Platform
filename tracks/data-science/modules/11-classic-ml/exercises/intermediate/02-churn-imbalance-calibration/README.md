---
title: Imbalanced data và calibration trên Telco churn
level: intermediate
services: []
files:
  - path: starter/calibration.ipynb
    note: 5 hàm TODO + câu hỏi cuối notebook
  - path: tests/test_calibration.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py telco-churn
  - uv run jupyter lab tracks/data-science/modules/11-classic-ml/exercises/intermediate/02-churn-imbalance-calibration/starter/calibration.ipynb
  - uv run pytest tracks/data-science/modules/11-classic-ml/exercises/intermediate/02-churn-imbalance-calibration -q
---

## Mục tiêu

Thấy tận mắt `class_weight="balanced"` làm gì với xác suất, đo calibration bằng reliability table và ECE, và sửa
xác suất bằng prior correction, Platt, isotonic.

## Đề bài

Bộ Telco Customer Churn (7 043 khách, 26.5% churn). Mở `starter/calibration.ipynb`:

1. `load_telco(path) -> (X, y)`: bỏ `customerID`, `y` là `Churn == "Yes"` dạng int, `TotalCharges` đổi sang số
   (11 ô trống thành 0).
2. `reliability_table(y, p, n_bins=10)`: khoảng đều trên [0, 1], bỏ khoảng rỗng, cột `mean_pred`, `frac_pos`, `n`.
3. `expected_calibration_error(y, p, n_bins=10)`: $$\sum_b \frac{n_b}{n}\,|\bar p_b - \bar y_b|$$.
4. `prior_correct(p, train_rate, target_rate)`: sửa xác suất của model học trên tỉ lệ dương `train_rate`.
5. `recalibrate(p_cal, y_cal, p_new, method)`: `"sigmoid"` (Platt trên logit) hoặc `"isotonic"`.
6. Chạy các cell `explore` (chia train / calibration / test 60/20/20, so có và không có class_weight, sửa xác
   suất bằng ba cách) và trả lời câu hỏi cuối notebook.

## Tiêu chí đạt

- `reliability_table` khớp `sklearn.calibration.calibration_curve(strategy="uniform")`.
- ECE dưới 0.02 với xác suất calibrated, trên 0.15 khi xác suất bị méo.
- `prior_correct` đưa xác suất trung bình của logistic `class_weight="balanced"` về đúng tỉ lệ dương (sai số
  dưới 1.5 điểm %) và giảm Brier.
- `recalibrate` cả hai cách: ECE dưới 0.04, Brier giảm, không đảo thứ hạng.
- Trên Telco thật: 7 043 × 19, tỉ lệ churn 0.2654, 11 khách có `TotalCharges = 0`.

## Gợi ý

### Gợi ý 1

`np.searchsorted(np.linspace(0, 1, n_bins + 1)[1:-1], p, side="right")` cho chỉ số khoảng giống sklearn
(p = 1 vào khoảng cuối). Prior correction làm trên odds: odds mới = odds cũ chia cho
`(train_rate / (1 − train_rate)) / (target_rate / (1 − target_rate))`.

### Gợi ý 2

Platt: `LogisticRegression(C=1e6).fit(logit(p_cal).reshape(-1, 1), y_cal)` (C lớn để gần như không
regularize). Isotonic: `IsotonicRegression(out_of_bounds="clip")`, nếu không p_new ngoài khoảng của p_cal cho NaN.
