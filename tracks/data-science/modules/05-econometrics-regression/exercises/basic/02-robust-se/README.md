---
title: Robust SE (HC0, HC1, HC3) và kiểm định Breusch-Pagan
level: basic
services: []
files:
  - path: starter/robust.py
    note: 3 hàm TODO
  - path: tests/test_robust.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/05-econometrics-regression/exercises/basic/02-robust-se -q
---

## Mục tiêu

Tự viết sandwich estimator để thấy robust SE chỉ thay "phần thịt" của công thức SE, và tự kiểm
bằng mô phỏng rằng khi có heteroskedasticity, khoảng tin cậy 95% cổ điển **không còn** chứa giá trị
thật 95% số lần.

## Đề bài

Trong `starter/robust.py` (X luôn đã có cột hằng số):

1. `hc_cov(X, resid, kind="HC3") -> np.ndarray`: ma trận hiệp phương sai $$k \times k$$ của
   $$\hat\beta$$ theo công thức sandwich

$$
(X^\top X)^{-1} \left( \sum_i w_i \hat\varepsilon_i^2 \, x_i x_i^\top \right) (X^\top X)^{-1}
$$

   với $$w_i = 1$$ (`HC0`), $$w_i = n/(n-k)$$ (`HC1`), $$w_i = 1/(1-h_{ii})^2$$ (`HC3`), trong đó
   $$h_{ii}$$ là đường chéo của hat matrix $$X(X^\top X)^{-1}X^\top$$. `kind` khác thì raise
   `ValueError`.
2. `robust_se(X, y, kind="HC3") -> np.ndarray`: fit OLS rồi trả SE robust.
3. `breusch_pagan(X, resid) -> (lm, p_value)`: hồi quy $$\hat\varepsilon^2$$ lên X, $$LM = nR^2$$
   của hồi quy phụ đó, so với $$\chi^2$$ với $$k - 1$$ bậc tự do.

Không dùng `get_robustcov_results`, `cov_type=` hay `het_breuschpagan` trong lời giải; test so với
chúng tới 1e-8.

## Tiêu chí đạt

- `hc_cov` khớp `cov_HC0`, `cov_HC1`, `cov_HC3` của statsmodels; `breusch_pagan` khớp `het_breuschpagan`.
- Không tạo ma trận $$n \times n$$ (test chạy với n = 200 000 phải nhanh).
- Trên dữ liệu mô phỏng có variance tăng theo x: Breusch-Pagan bác bỏ, CI 95% dựng bằng SE HC3 chứa
  hệ số thật 92–97% số lần, CI cổ điển dưới 90%.

## Gợi ý

### Gợi ý 1

Phần giữa không cần vòng lặp: `(X * (w * resid**2)[:, None]).T @ X`. Đường chéo hat matrix cũng
không cần dựng cả ma trận: `h = np.einsum("ij,jk,ik->i", X, XtX_inv, X)`, hoặc
`((X @ XtX_inv) * X).sum(axis=1)`.

### Gợi ý 2

$$R^2$$ của hồi quy phụ: fit OLS `resid**2 ~ X` bằng `np.linalg.lstsq`, rồi `1 - SSR/SST` như bài
Basic 01. p-value: `scipy.stats.chi2.sf(lm, k - 1)`.
