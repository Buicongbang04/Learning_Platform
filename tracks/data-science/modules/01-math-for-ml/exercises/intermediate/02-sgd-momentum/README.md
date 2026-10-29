---
title: Momentum và SGD minibatch trên bài toán xấu điều kiện
level: intermediate
services: []
files:
  - path: starter/optimizers.py
    note: 6 hàm TODO
  - path: tests/test_optimizers.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/01-math-for-ml/exercises/intermediate/02-sgd-momentum -q
---

## Mục tiêu

Tự viết ba optimizer nền tảng của deep learning (gradient descent, heavy-ball momentum, minibatch
SGD có learning rate giảm dần) và đo bằng số: momentum nhanh hơn bao nhiêu trên bài toán có
condition number 100, và vì sao SGD với learning rate cố định không bao giờ "đậu" đúng nghiệm.

## Đề bài

Trong `starter/optimizers.py` (quy ước "path": mảng `(n_iter + 1, d)`, hàng 0 là `w0`):

1. `quadratic_grad(A, b)`: trả hàm gradient của $$f(w) = \tfrac12 w^\top A w - b^\top w$$.
2. `gd(grad, w0, lr, n_iter)` và `momentum(grad, w0, lr, beta, n_iter)` (heavy ball:
   $$v \leftarrow \beta v - \text{lr}\,\nabla f(w)$$, $$w \leftarrow w + v$$, `v` khởi tạo 0).
3. `optimal_momentum_params(mu, L)`: lr và β tối ưu theo lý thuyết cho trị riêng trong $$[\mu, L]$$.
4. `iterations_to_tol(path, w_star, tol)`: bước đầu tiên khoảng cách tới nghiệm còn `tol` lần ban đầu.
5. `sgd_linreg(X, y, lr0, n_epochs, batch_size, seed, decay)`: minibatch SGD cho MSE, xáo dữ liệu
   mỗi epoch, lr giảm theo $$\text{lr}_0/(1 + \text{decay}\cdot t)$$. Đọc docstring để làm đúng quy ước
   (test so khớp tuyệt đối với cách cài tham chiếu ở một số chỗ).

## Tiêu chí đạt

- `gd` khớp nghiệm đóng trên hàm bậc hai chéo; phân kỳ khi lr > 2/L.
- `momentum` với β = 0 trùng `gd`; hai bước đầu khớp tính tay.
- Trên 10 hàm bậc hai bị xoay ngẫu nhiên có κ = 100, momentum với tham số tối ưu cần ít hơn 1/5 số
  bước của gradient descent (lr = 1/L) để tới sai số 1e-6.
- SGD full batch không decay trùng gradient descent; cùng seed cho cùng kết quả.
- Trên 10 seed: SGD lr cố định dừng cách nghiệm least squares hơn 0.2, có decay thì dưới 0.1 và gần
  hơn ít nhất 5 lần.

## Gợi ý

### Gợi ý 1

Với gradient descent trên hàm bậc hai, sai số theo hướng trị riêng $$\lambda$$ nhân với
$$(1 - \text{lr}\,\lambda)$$ mỗi bước. Lr = 1/L thì hướng $$\lambda = \mu$$ chỉ giảm $$1 - 1/\kappa$$ mỗi bước:
khoảng $$\kappa \ln(10^6) \approx 1380$$ bước cho κ = 100. Momentum tối ưu giảm khoảng
$$(\sqrt\kappa - 1)/(\sqrt\kappa + 1)$$ mỗi bước.

### Gợi ý 2

`rng = np.random.default_rng(seed)` tạo **một lần** trước vòng epoch; mỗi epoch
`order = rng.permutation(n)`, batch là `order[start:start + batch_size]`. Biến đếm `t` tăng sau mỗi
lần cập nhật, không reset theo epoch.
