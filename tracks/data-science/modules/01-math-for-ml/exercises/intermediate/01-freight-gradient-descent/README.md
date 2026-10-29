---
title: Gradient descent và learning rate schedule cho phí ship Olist
level: intermediate
services: []
files:
  - path: starter/freight_gd.ipynb
    note: 5 hàm TODO + phần nhận xét
  - path: tests/test_freight_gd.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/01-math-for-ml/exercises/intermediate/01-freight-gradient-descent/starter/freight_gd.ipynb
  - uv run pytest tracks/data-science/modules/01-math-for-ml/exercises/intermediate/01-freight-gradient-descent -q
---

## Mục tiêu

Tự viết gradient descent có learning rate schedule, chạy trên dữ liệu Olist thật, và thấy tận mắt
vì sao chuẩn hoá feature (condition number) và ngưỡng learning rate $$2/L$$ quyết định optimizer có
chạy được hay không.

## Đề bài

Mở `starter/freight_gd.ipynb` và điền các hàm:

1. `build_freight_table(items, products, orders)`: mỗi dòng một order item, cột `freight_value`,
   `weight_kg`, `volume_l`, `split` (train / val / test theo thời điểm mua, quy ước chung của track),
   bỏ item thiếu kích thước và đơn mua từ 2018-09-01.
2. `lr_at(t, lr0, schedule, decay, step_size)`: bốn schedule `constant`, `step`, `inverse_time`,
   `exponential` (công thức trong notebook); tên lạ thì `ValueError`.
3. `gradient_descent(X, y, lr0, n_iter, schedule=..., ...) -> (w, losses)` cho MSE, khởi tạo `w = 0`,
   `losses` dài `n_iter + 1`.
4. `standardize_fit(X) -> (mu, sd)` và `to_original_scale(w_std, mu, sd)`: đổi hệ số học trên
   feature chuẩn hoá về đơn vị gốc.
5. Chạy các cell `explore`, viết 4–6 gạch đầu dòng nhận xét ở cell cuối.

## Tiêu chí đạt

- Bảng dữ liệu đúng trên fixture (lọc, đơn vị, ranh giới ngày giữa các split).
- Bốn schedule đúng công thức; `gradient_descent` thật sự dùng schedule.
- Gradient descent hội tụ về nghiệm least squares; dưới ngưỡng `0.95 · 2/L` thì hội tụ, trên
  `1.05 · 2/L` thì phân kỳ, trên 10 seed.
- Đổi hệ số về đơn vị gốc khớp hồi quy trực tiếp trên dữ liệu gốc.
- Trên Olist thật: 51 216 / 24 097 / 37 318 item train / val / test; hệ số ≈ 13.2485, 1.4592, 0.1790
  (khớp normal equation của bài Basic 02); MSE train ≈ 111.864.

## Gợi ý

### Gợi ý 1

Gradient của $$L(w) = \frac{1}{n}\lVert Xw - y\rVert^2$$ là $$\frac{2}{n}X^\top(Xw - y)$$. Hessian là
$$H = \frac{2}{n}X^\top X$$, hằng số. Với lr cố định, gradient descent hội tụ khi và chỉ khi
$$0 < \text{lr} < 2/\lambda_{\max}(H)$$.

### Gợi ý 2

`np.select([t < "2018-01-01", t < "2018-04-01"], ["train", "val"], default="test")` sau khi đã bỏ
đơn từ 2018-09-01. Hệ số trên đơn vị gốc: slope $$w_j/\sigma_j$$, intercept
$$b - \sum_j w_j\mu_j/\sigma_j$$.
