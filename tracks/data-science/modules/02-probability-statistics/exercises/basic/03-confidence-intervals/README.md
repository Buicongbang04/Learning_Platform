---
title: Khoảng tin cậy cho trung bình và tỉ lệ, kiểm tra bằng mô phỏng
level: basic
services: []
files:
  - path: starter/ci.py
    note: 4 hàm TODO
  - path: tests/test_ci.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/02-probability-statistics/exercises/basic/03-confidence-intervals -q
---

## Mục tiêu

Dựng khoảng tin cậy (CI) và **kiểm tra** nó bằng mô phỏng: một CI 95% đúng nghĩa phải chứa giá trị
thật khoảng 95% số lần. Bạn sẽ thấy CI Wald quen thuộc hỏng nặng thế nào với tỉ lệ nhỏ và mẫu nhỏ,
đúng tình huống "category ít đơn" của Olist.

## Đề bài

Trong `starter/ci.py`:

1. `mean_ci(x, alpha=0.05)`: CI t cho trung bình.
2. `wald_ci(k, n, alpha=0.05)`: CI Wald cho tỉ lệ, cắt hai đầu về [0, 1].
3. `wilson_ci(k, n, alpha=0.05)`: CI Wilson (công thức dưới).
4. `coverage(ci_fn, p, n, n_sims=10000, seed=0, alpha=0.05)`: mô phỏng `k ~ Binomial(n, p)`
   `n_sims` lần, trả tỉ lệ CI chứa p.

Với `p̂ = k/n` và `z = z_{1−α/2}`:

$$
\text{Wald: } \hat p \pm z\sqrt{\frac{\hat p(1-\hat p)}{n}},
\qquad
\text{Wilson: } \frac{\hat p + \frac{z^2}{2n}}{1 + \frac{z^2}{n}} \pm \frac{z}{1 + \frac{z^2}{n}}\sqrt{\frac{\hat p(1-\hat p)}{n} + \frac{z^2}{4n^2}}
$$

Test dùng cả số thật của Olist: category `fashion_male_clothing` có 24 review xấu trên 105 đơn,
category `fashion_childrens_clothes` 0 trên 7, toàn sàn 12 272 trên 95 824.

## Tiêu chí đạt

- `mean_ci`, `wald_ci`, `wilson_ci` khớp `scipy` / `statsmodels` tới 1e-9.
- Với 0/7: Wald thoái hoá thành [0, 0]; Wilson cho cận trên trên 30%.
- Độ phủ với p = 2%, n = 50: Wald khoảng 63%, Wilson khoảng 92%. Với p = 12.8%, n = 400 cả hai gần 95%.
- Cùng seed cho cùng kết quả.

## Gợi ý

### Gợi ý 1

`t.ppf(1 − alpha/2, n − 1)` và `norm.ppf(1 − alpha/2)`. Độ lệch chuẩn mẫu dùng `ddof=1`.

### Gợi ý 2

`coverage` không cần gọi `ci_fn` 20 nghìn lần: k chỉ nhận n + 1 giá trị. `np.unique(ks,
return_counts=True)` rồi tính CI một lần cho mỗi giá trị k.
