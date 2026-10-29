---
title: Tự viết normal equation cho phí ship Olist
level: basic
services: []
files:
  - path: starter/normal_equation.py
    note: 4 hàm TODO
  - path: tests/test_normal_equation.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run pytest tracks/data-science/modules/01-math-for-ml/exercises/basic/02-normal-equation -q
---

## Mục tiêu

Tự cài linear regression bằng normal equation, đối chiếu với `numpy` và `scikit-learn`, rồi chạy
trên Olist thật: phí ship (`freight_value`) theo khối lượng và thể tích sản phẩm.

## Đề bài

Trong `starter/normal_equation.py`:

1. `add_intercept(X)`: thêm cột toàn 1 vào bên trái, không sửa `X` gốc.
2. `fit_normal_equation(X, y)`: hệ số cực tiểu $$\lVert y - Xw\rVert^2$$ bằng cách giải
   $$X^\top X\, w = X^\top y$$ với `np.linalg.solve`. Cấm `inv`, `pinv` (test chặn hai hàm này).
3. `predict(X, w)`.
4. `r2_score(y, y_pred)`: $$R^2 = 1 - \mathrm{SS}_{\text{res}} / \mathrm{SS}_{\text{tot}}$$.

Test thật trên Olist (tự skip nếu chưa tải): ghép `order_items` với `products` và `orders`, bỏ item
thiếu kích thước, feature `weight_kg` và `volume_l` (dài × cao × rộng / 1000), fit trên đơn mua
trước 2018-01-01 (51 216 item), đánh giá trên đơn mua từ 2018-04-01 tới hết 2018-08-31 (37 318 item).

## Tiêu chí đạt

- Hệ số khớp `np.linalg.lstsq` và `LinearRegression` tới sai số tương đối 1e-8.
- Không gọi `np.linalg.inv` / `pinv`.
- Residual vuông góc với mọi cột và có trung bình 0.
- `r2_score` khớp `sklearn.metrics.r2_score`; dự đoán bằng trung bình cho R² = 0.
- Trên Olist thật: freight ≈ 13.2485 + 1.4592 · kg + 0.1790 · lít, R² trên test ≈ 0.342.

## Gợi ý

### Gợi ý 1

Vì sao không `inv`? Tính nghịch đảo tốn hơn và kém chính xác hơn giải trực tiếp hệ phương trình;
`solve` dùng phân rã LU một lần. Đọc mục 6 của lý thuyết về condition number.

### Gợi ý 2

`SS_tot = Σ (y − ȳ)²`, `SS_res = Σ (y − ŷ)²`. R² trên tập test có thể âm nếu model tệ hơn dự đoán
bằng trung bình của chính tập test.
