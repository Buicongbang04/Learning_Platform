---
title: Tự viết OLS bằng ma trận và so với statsmodels
level: basic
services: []
files:
  - path: starter/ols.py
    note: 2 hàm TODO
  - path: tests/test_ols.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/05-econometrics-regression/exercises/basic/01-ols-matrix -q
---

## Mục tiêu

Tự tính mọi con số trong bảng `summary()` của một hồi quy OLS: hệ số, SE, t, p-value, $$R^2$$.
Làm xong bạn biết SE đến từ đâu, nên hiểu vì sao robust SE, cluster SE (bài sau) chỉ thay đúng một
mảnh của công thức.

## Đề bài

Trong `starter/ols.py`:

1. `add_intercept(X) -> np.ndarray`: thêm cột 1 vào **đầu** ma trận X (nhận cả mảng 1 chiều, coi
   như một cột).
2. `ols_fit(X, y) -> dict` với X **đã có** cột hằng số. Trả dict có đúng các khoá:
   - `beta`: hệ số, tính bằng `np.linalg.lstsq` (không nghịch đảo $$X^\top X$$ để giải hệ).
   - `resid`: residual $$y - X\hat\beta$$.
   - `sigma2`: $$\hat\varepsilon^\top \hat\varepsilon / (n - k)$$.
   - `se`: căn đường chéo của $$\hat\sigma^2 (X^\top X)^{-1}$$.
   - `t`, `p`: thống kê t và p-value hai phía theo phân phối t với $$n - k$$ bậc tự do.
   - `r2`, `adj_r2`: $$R^2 = 1 - \mathrm{SSR}/\mathrm{SST}$$ (SST quanh trung bình của y),
     $$\bar R^2 = 1 - (1 - R^2)\frac{n-1}{n-k}$$.

   Nếu X không đủ rank cột (có cột là tổ hợp tuyến tính của cột khác), raise `ValueError` có thông
   báo rõ ràng thay vì trả về hệ số vô nghĩa.

Được dùng `numpy`, `scipy.stats.t`. Không dùng statsmodels trong lời giải; test sẽ so với statsmodels
tới sai số 1e-8.

## Tiêu chí đạt

- `beta`, `se`, `t`, `p`, `r2`, `adj_r2` khớp `statsmodels.OLS` trên dữ liệu mô phỏng và trên
  Grunfeld (`invest ~ value + capital`: hệ số 0.1145 và 0.2275).
- `resid` có tổng bằng 0 (vì có hằng số) và trực giao với mọi cột của X.
- Ma trận thiếu rank làm `ols_fit` raise `ValueError`.

## Gợi ý

### Gợi ý 1

`np.linalg.lstsq(X, y, rcond=None)` trả về `(beta, residuals, rank, singular_values)`. Dùng
`rank` để kiểm tra đủ rank cột: `rank < X.shape[1]` là có cột thừa.

### Gợi ý 2

p-value hai phía: `2 * t.sf(abs(t_stat), df)`. Ma trận $$(X^\top X)^{-1}$$ chỉ cần cho SE; tính bằng
`np.linalg.inv(X.T @ X)` ở bước này là chấp nhận được vì đã kiểm rank. Statsmodels dùng
pseudo-inverse, cho cùng kết quả khi X đủ rank.
