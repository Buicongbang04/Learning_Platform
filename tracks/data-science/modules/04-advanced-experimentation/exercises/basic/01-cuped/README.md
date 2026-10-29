---
title: Tự viết CUPED và đo mức giảm variance
level: basic
services: []
files:
  - path: starter/cuped.py
    note: 5 hàm TODO
  - path: tests/test_cuped.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/04-advanced-experimentation/exercises/basic/01-cuped -q
---

## Mục tiêu

Hiểu CUPED từ bên trong: vì sao trừ đi một phần metric trước thí nghiệm lại không làm lệch ước
lượng mà làm khoảng tin cậy hẹp lại, và hẹp được bao nhiêu. Sau bài này bạn quy được "tương quan
0.8" ra "tiết kiệm 64% traffic".

## Đề bài

Trong `starter/cuped.py`, `y` là metric đo trong thí nghiệm, `x` là metric đo **trước** thí nghiệm
của cùng đơn vị, `treat` là mảng bool. Dùng `ddof=1` cho variance và covariance.

1. `cuped_theta(y, x)`: hệ số $$\theta = \mathrm{cov}(Y, X) / \mathrm{var}(X)$$.
2. `cuped_adjust(y, x, theta=None)`: $$Y_{\text{cuped}} = Y - \theta\,(X - \bar X)$$. Nếu `theta` là
   `None` thì tự tính.
3. `variance_reduction(y, x)`: $$1 - \mathrm{var}(Y_{\text{cuped}}) / \mathrm{var}(Y)$$.
4. `cuped_effect(y, x, treat, alpha=0.05) -> dict`: `diff`, `se`, `ci_low`, `ci_high` tính trên
   `y` đã điều chỉnh, cộng `diff_raw`, `se_raw` trên `y` gốc. `theta` tính trên dữ liệu **gộp** hai
   nhánh. SE theo Welch.
5. `n_after_cuped(n, rho)`: cỡ mẫu cần sau CUPED để giữ nguyên power, làm tròn lên.

## Tiêu chí đạt

- `theta` khớp `cov / var`; mức giảm variance đúng bằng $$\rho^2$$ của mẫu.
- Mean của `y` sau điều chỉnh không đổi.
- Với $$\rho = 0.8$$, SE còn khoảng 0.6 lần SE gốc.
- Qua 300 thí nghiệm mô phỏng, ước lượng CUPED không lệch (trung bình gần tác động thật) và dao
  động ít hơn ước lượng gốc; CI 95% chứa giá trị thật khoảng 95% số lần.
- Dùng "covariate" đo **sau** can thiệp thì tác động gần như biến mất (test minh hoạ lỗi này).
- `n_after_cuped(16930, 0.3) == 15407`.

## Gợi ý

### Gợi ý 1

`np.cov(y, x)[0, 1]` dùng ddof=1 sẵn; nhớ gọi `np.var(x, ddof=1)` cho khớp. Vì `x - x.mean()` có
trung bình 0, phép trừ không làm đổi mean của `y`.

### Gợi ý 2

$$\mathrm{var}(Y - \theta X) = \mathrm{var}(Y)(1 - \rho^2)$$ khi $$\theta$$ là hệ số tối ưu. Cỡ mẫu tỉ lệ
thuận với variance, nên `n_after_cuped` chỉ là `n * (1 - rho**2)`. Cẩn thận sai số dấu phẩy động
khi làm tròn lên: trừ một lượng rất nhỏ (`1e-9`) trước `math.ceil`.
