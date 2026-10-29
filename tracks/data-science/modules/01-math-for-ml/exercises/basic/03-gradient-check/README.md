---
title: Gradient bằng tay và gradient check bằng sai phân hữu hạn
level: basic
services: []
files:
  - path: starter/gradcheck.py
    note: 4 hàm TODO
  - path: tests/test_gradcheck.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/01-math-for-ml/exercises/basic/03-gradient-check -q
---

## Mục tiêu

Tự đạo hàm hai loss quan trọng nhất (MSE và logistic / binary cross-entropy) bằng chain rule, và
viết công cụ **gradient check** để bắt lỗi đạo hàm, kỹ năng mà mọi người tự viết model hay layer
mới đều cần.

## Đề bài

Trong `starter/gradcheck.py`:

1. `numerical_gradient(f, x, eps=1e-5)`: gradient bằng **sai phân trung tâm**
   $$\frac{f(x + \varepsilon e_i) - f(x - \varepsilon e_i)}{2\varepsilon}$$ cho từng toạ độ. Không sửa `x` của người gọi.
2. `relative_error(a, b)`: $$\frac{\lVert a - b\rVert}{\lVert a\rVert + \lVert b\rVert}$$, trả 0 khi cả hai bằng 0.
3. `mse_loss_grad(w, X, y)`: loss $$\frac{1}{n}\lVert Xw - y\rVert^2$$ và gradient.
4. `logistic_loss_grad(w, X, y)`: binary cross-entropy trung bình của $$p = \sigma(Xw)$$ và gradient.
   Phải ổn định số khi logit lên tới ±1000.

## Tiêu chí đạt

- Gradient số đúng trên hàm đã biết đạo hàm; là sai phân **trung tâm** (test phân biệt được với sai phân tiến).
- Gradient giải tích của MSE và logistic khớp gradient số với sai số tương đối dưới 1e-7.
- Logistic loss khớp `sklearn.metrics.log_loss`, không ra `nan` / `inf` với logit ±1000.
- Một gradient sai (quên hệ số 2) bị phát hiện: sai số tương đối trên 0.1.

## Gợi ý

### Gợi ý 1

Sai phân tiến có sai số bậc $$\varepsilon$$, sai phân trung tâm có sai số bậc $$\varepsilon^2$$. Nhưng $$\varepsilon$$
quá nhỏ (1e-12) thì sai số làm tròn của float64 chiếm ưu thế. `1e-5` tới `1e-6` là vùng an toàn.

### Gợi ý 2

Viết loss theo logit $$z$$: $$-[y\log\sigma(z) + (1-y)\log(1-\sigma(z))] = \log(1 + e^{z}) - yz$$, và
`np.logaddexp(0, z)` tính $$\log(1 + e^{z})$$ không tràn số. Chain rule: $$\frac{\partial L}{\partial z} = \sigma(z) - y$$,
rồi $$\frac{\partial z}{\partial w} = x$$, nên gradient trung bình là $$\frac{1}{n}X^\top(\sigma(Xw) - y)$$.
