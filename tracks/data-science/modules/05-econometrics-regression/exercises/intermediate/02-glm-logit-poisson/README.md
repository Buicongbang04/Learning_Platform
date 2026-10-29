---
title: Diễn giải GLM - odds ratio, marginal effect, overdispersion
level: intermediate
services: []
files:
  - path: starter/glm.py
    note: 4 hàm TODO
  - path: tests/test_glm.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run pytest tracks/data-science/modules/05-econometrics-regression/exercises/intermediate/02-glm-logit-poisson -q
---

## Mục tiêu

Fit GLM thì dễ; khó là **đọc** nó đúng và chọn đúng family. Bài này viết các công cụ diễn giải mà
DS dùng hằng ngày: odds ratio kèm CI, average marginal effect cho biến 0/1 (con số stakeholder hiểu),
kiểm tra overdispersion, và tự chọn giữa Poisson và Negative Binomial.

## Đề bài

Trong `starter/glm.py`:

1. `odds_ratios(res, alpha=0.05) -> DataFrame`: cột `odds_ratio`, `ci_low`, `ci_high`, index là tên
   hệ số (kể cả `Intercept`).
2. `discrete_ame(res, df, var) -> float`: với biến 0/1 `var`, dự đoán xác suất cho **mọi dòng** của
   `df` khi đặt `var = 1` và khi đặt `var = 0`, trả trung bình chênh lệch. Đây là "nếu mọi đơn đều
   trễ so với nếu không đơn nào trễ".
3. `pearson_dispersion(res) -> float`: với GLM Poisson,

$$
\frac{1}{n - k} \sum_i \frac{(y_i - \hat\mu_i)^2}{\hat\mu_i}
$$

   tự tính từ `res.model.endog` và `res.fittedvalues` (không dùng `res.pearson_chi2`).
4. `fit_count_model(formula, df, threshold=1.5) -> (res, kind)`: fit Poisson; nếu dispersion vượt
   `threshold` thì fit `smf.negativebinomial` và trả `"negbin"`, ngược lại trả Poisson và `"poisson"`.

Test thật trên Olist: review xấu theo giao trễ, và số món thêm mỗi đơn (`n_items − 1`) theo log giá
trung bình mỗi món.

## Tiêu chí đạt

- Odds ratio là `exp` của hệ số; CI chứa giá trị thật trên dữ liệu mô phỏng; CI 99% rộng hơn CI 95%.
- `discrete_ame` khớp `get_margeff(dummy=True)` của statsmodels, và bằng đúng chênh lệch tỉ lệ thô khi
  model chỉ có một biến 0/1.
- `pearson_dispersion` ≈ 1 trên dữ liệu Poisson, > 1.5 trên dữ liệu Negative Binomial.
- `fit_count_model` chọn đúng model và hệ số gần giá trị thật.
- Trên Olist thật: OR của giao trễ ≈ 11.59, AME ≈ 0.449; dispersion của model số món ≈ 1.98, chọn
  `"negbin"`.

## Gợi ý

### Gợi ý 1

`res.conf_int(alpha=alpha)` trả DataFrame hai cột (cận dưới, cận trên) trên thang log-odds. Lấy `exp`
**sau** khi tính CI, không tính CI trên thang OR bằng `OR ± 1.96 × SE`.

### Gợi ý 2

`df.assign(**{var: 1})` tạo bản sao có cột `var` toàn 1. `res.predict(dataframe)` của formula API tự
dựng lại ma trận thiết kế (kể cả biến biến đổi trong công thức), nên đừng tự nhân ma trận.
