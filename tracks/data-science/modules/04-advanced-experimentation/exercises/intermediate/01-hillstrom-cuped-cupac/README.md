---
title: CUPED, hồi quy và CUPAC trên thí nghiệm email Hillstrom
level: intermediate
services: []
files:
  - path: starter/variance_reduction.ipynb
    note: 3 hàm TODO + phần kết luận
  - path: tests/test_variance_reduction.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py hillstrom
  - uv run jupyter lab tracks/data-science/modules/04-advanced-experimentation/exercises/intermediate/01-hillstrom-cuped-cupac/starter/variance_reduction.ipynb
  - uv run pytest tracks/data-science/modules/04-advanced-experimentation/exercises/intermediate/01-hillstrom-cuped-cupac -q
---

## Mục tiêu

Áp ba kỹ thuật giảm variance (CUPED một covariate, hồi quy nhiều covariate, CUPAC dùng model ML) lên
một thí nghiệm thật, đo mỗi cách giảm được bao nhiêu, và giải thích được vì sao con số thật có thể
rất khiêm tốn.

## Đề bài

Bộ Hillstrom: 64 000 khách, 3 nhánh. `history` (chi tiêu 12 tháng trước) và các cột hồ sơ khác đều
có **trước** khi gửi email. Mở `starter/variance_reduction.ipynb`:

1. Xem tương quan của các cột trước thí nghiệm với `visit`, `conversion`, `spend`.
2. `cuped_effect(df, metric, covariate, arm, control="No E-Mail") -> dict` với `diff`, `se`,
   `diff_raw`, `se_raw`, `theta`, `var_reduction`. Chỉ dùng hai nhánh `arm` và `control`.
3. `regression_effect(df, metric, covariates, arm, control="No E-Mail") -> (diff, se)`: OLS
   `metric ~ treat + covariates`, SE robust `HC1`, cột chuỗi đưa vào dạng `C(cột)`.
4. `cupac_covariate(df, features, metric, n_splits=5, seed=0) -> np.ndarray`: dự đoán
   **out-of-fold** (cross-fitting) của metric từ các cột trước thí nghiệm.
5. Viết kết luận 4–6 câu trong cell markdown cuối.

## Tiêu chí đạt

- `cuped_effect` đúng số liệu thô, `theta` tính trên đúng hai nhánh, hỗ trợ đổi control.
- `regression_effect` không covariate cho đúng hiệu trung bình; với một covariate cho kết quả gần
  như trùng CUPED; covariate phân loại giải thích thêm variance.
- `cupac_covariate` không rò rỉ: đổi outcome của một dòng không làm đổi dự đoán của chính dòng đó.
- Trên dữ liệu thật: email nữ tăng `visit` khoảng 4.52 điểm phần trăm; CUPED với `history` giảm
  dưới 1% variance; hồi quy đủ cột hồ sơ làm SE nhỏ đi; CUPAC đạt $$\rho^2 > 0.015$$ với `visit`.
- Kết luận chấm theo `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`smf.ols("visit ~ treat + history + C(channel)", data=two).fit(cov_type="HC1")`, rồi lấy
`fit.params["treat"]` và `fit.bse["treat"]`. Kiểm kiểu cột bằng `two[c].dtype == object`.

### Gợi ý 2

`pd.get_dummies(df[features], dtype=float)` biến cột chuỗi thành one-hot. Với `KFold(n_splits,
shuffle=True, random_state=seed)`, chia fold chỉ phụ thuộc số dòng và seed, không phụ thuộc
outcome; mỗi fold dự đoán bằng model huấn luyện trên các fold còn lại. `HistGradientBoostingRegressor`
hay `LinearRegression` đều được, miễn là out-of-fold.
