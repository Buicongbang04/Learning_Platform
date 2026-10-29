---
title: "Instrumental variables: lợi suất của giáo dục (Card 1995)"
level: intermediate
services: []
files:
  - path: starter/iv.py
    note: 3 hàm TODO
  - path: tests/test_iv.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py card
  - uv run pytest tracks/data-science/modules/06-causal-inference/exercises/intermediate/03-card-2sls -q
---

## Mục tiêu

Tự viết 2SLS bằng ma trận, hiểu vì sao "chạy hai lần OLS" cho đúng hệ số nhưng sai standard error,
và biết kiểm tra instrument yếu bằng F-statistic của first stage.

## Đề bài

Học thêm một năm thì lương tăng bao nhiêu? Hồi quy OLS lương theo số năm học bị lệch vì
**năng lực** (không đo được) làm tăng cả số năm học lẫn lương. Card (1995) dùng instrument
`nearc4`: lớn lên gần một trường đại học 4 năm. Sống gần trường làm việc học đại học rẻ hơn (ảnh
hưởng tới `educ`), và lập luận là nó không tác động trực tiếp tới lương ngoài con đường giáo dục.

Bộ `card` có 3 010 nam giới (khảo sát NLS 1976): `lwage` (log lương), `educ`, `nearc4`, cùng các
biến kiểm soát `exper`, `expersq`, `black`, `south`, `smsa`, `smsa66`, `reg662`…`reg669`.

Trong `starter/iv.py`:

1. `wald_estimator(df, outcome, endog, instrument)`: instrument nhị phân, không biến kiểm soát.
2. `first_stage(df, endog, instrument, exog) -> (coef, F)`: hệ số của instrument và F-statistic
   (với một instrument, F = t² với SE thông thường).
3. `two_sls(df, outcome, endog, instrument, exog) -> (coef, se)`: 2SLS bằng numpy, SE thông thường
   với bậc tự do `n − k`.

## Tiêu chí đạt

- `first_stage` khớp `statsmodels`; `two_sls` khớp `linearmodels.IV2SLS(..., debiased=True)` tới
  1e-8, có và không có biến kiểm soát.
- SE của bạn khác SE của cách "OLS lần hai trên giá trị dự đoán" (dù hệ số trùng).
- Trên dữ liệu mô phỏng có biến năng lực ẩn: OLS lệch lên trên 1.5, 2SLS về gần tác động thật 1.0;
  instrument yếu cho F dưới 10.
- Trên Card thật: Wald ≈ 0.188; first stage ≈ 0.320 với F ≈ 13.26; 2SLS ≈ 0.1315 (SE ≈ 0.0550).

## Gợi ý

### Gợi ý 1

`X = np.column_stack([np.ones(n), df[[endog, *exog]]])`, tương tự `Z` với instrument thay endog.
Dùng `np.linalg.solve(A, b)` thay vì nghịch đảo ma trận khi chỉ cần giải hệ.

### Gợi ý 2

Hồi quy lần hai của "OLS hai lần" có phần dư `y − X̂β`. Nhưng mô hình thật là `y = Xβ + u`, nên
phần dư đúng phải tính bằng `X` thật: `u = y − Xβ`. Hệ số trùng nhau, chỉ có σ² khác, và vì thế SE
khác. Đây là lý do không bao giờ tự chạy hai lần OLS để báo cáo SE của 2SLS.
