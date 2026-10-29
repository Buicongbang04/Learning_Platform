---
title: Tự viết gradient boosting
level: basic
services: []
files:
  - path: starter/gb.py
    note: 3 hàm TODO
  - path: tests/test_gb.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/12-advanced-ml/exercises/basic/01-gradient-boosting-scratch -q
---

## Mục tiêu

Hiểu gradient boosting đến mức tự viết được trong 30 dòng: mỗi cây học **negative gradient** của
loss, `learning_rate` co bước đi, và với loss không khả vi đẹp (absolute) thì giá trị lá được chọn
lại bằng line search. Sau bài này, các tham số của LightGBM/XGBoost không còn là hộp đen.

## Đề bài

Trong `starter/gb.py`, cây con luôn là `DecisionTreeRegressor(max_depth=max_depth, random_state=0)`.

1. `fit_gb(X, y, n_estimators=100, learning_rate=0.1, max_depth=3, loss="squared") -> dict`
   với các khoá `init`, `trees`, `learning_rate`, `loss`.
   - `loss="squared"` (loss $$\tfrac12 (y - F)^2$$): $$F_0$$ là trung bình của `y`; mỗi vòng fit cây
     lên phần dư $$y - F$$.
   - `loss="absolute"` (loss $$|y - F|$$): $$F_0$$ là median của `y`; negative gradient là
     $$\operatorname{sign}(y - F)$$, nên cây học trên dấu; sau đó **đặt lại giá trị mỗi lá** bằng
     median của phần dư $$y - F$$ của các điểm trong lá (dùng `tree.apply(X)` để biết điểm nào vào lá
     nào, và ghi vào `tree.tree_.value[leaf, 0, 0]`).
   - `loss` khác → `ValueError`.
2. `predict_gb(model, X, n_trees=None)`: $$F_0 + \nu \sum_{m \le n} h_m(X)$$ với $$\nu$$ là
   `learning_rate`; `n_trees=0` cho hằng số $$F_0$$.
3. `staged_loss(model, X, y)`: mảng dài $$M + 1$$, loss sau 0, 1, …, M cây (MSE cho squared, MAE
   cho absolute).

Sau khi xong, thử trong REPL: so `staged_loss` trên train và trên một tập holdout sinh thêm. Bao
nhiêu cây thì holdout bắt đầu xấu đi với `learning_rate=0.5` so với `0.05`?

## Tiêu chí đạt

- `n_trees=0` trả mean (squared) hoặc median (absolute).
- Với squared loss, dự đoán trên tập train trùng `sklearn.ensemble.GradientBoostingRegressor`
  (cùng tham số) tới `1e-8`, kể cả dự đoán từng giai đoạn (`staged_predict`).
- Loss train không bao giờ tăng qua các vòng (squared); learning rate nhỏ cần nhiều cây hơn.
- Absolute loss: giá trị lá là median; khi `y` có 8% outlier cực lớn, MAE trên dữ liệu sạch nhỏ hơn
  70% MAE của squared loss (thử trên 3 seed).

## Gợi ý

### Gợi ý 1

Giữ một mảng `F` (dự đoán hiện tại trên tập train) và cập nhật nó sau mỗi cây; đừng gọi lại toàn bộ
mô hình mỗi vòng. `np.sign(0) = 0` là được.

### Gợi ý 2

Vì sao phải sửa lá với absolute loss: cây học trên `sign` nên giá trị lá nằm trong $$[-1, 1]$$, không
có đơn vị của `y`. Median phần dư trong lá là giá trị $$\gamma$$ làm nhỏ nhất
$$\sum_{i \in \text{leaf}} |y_i - F_i - \gamma|$$. Đây đúng là bước "line search theo từng vùng" trong
bài báo gốc của Friedman (2001), và cũng là ý tưởng mà XGBoost tổng quát hoá bằng bước Newton.
