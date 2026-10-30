---
title: Variational quantum classifier với parameter-shift tự viết
level: intermediate
services: []
files:
  - path: starter/vqc.ipynb
    note: 4 hàm TODO
  - path: tests/test_vqc.py
    note: Không sửa
run:
  - uv run jupyter lab tracks/ai-engineer/modules/22-quantum-ml/exercises/intermediate/01-variational-classifier/starter/vqc.ipynb
  - uv run pytest tracks/ai-engineer/modules/22-quantum-ml/exercises/intermediate/01-variational-classifier -q
---

## Mục tiêu

Train một mô hình lượng tử từ đầu tới cuối như trên phần cứng thật: gradient bằng parameter-shift rule bạn tự viết, mạch
2 qubit có data re-uploading dựng bằng PennyLane, gradient descent trên `make_moons`. Rồi làm điều mà phần lớn bài viết về
QML bỏ qua: so với bốn baseline cổ điển trên 5 lần chia dữ liệu, và đếm chi phí mỗi bước train trên phần cứng.

## Đề bài

**Phần cứng:** CPU · ~90 phút

Thời gian trên là thời gian làm bài. Chạy cả notebook lời giải khoảng 1 phút (train 4 mạch bằng parameter-shift khoảng 40
giây; 5 lần chia dùng backprop của simulator, khoảng 15 giây); máy bận có thể chậm gấp đôi.

Mở `starter/vqc.ipynb`. Dữ liệu sinh bằng scikit-learn, không cần tải.

1. `parameter_shift_jacobian(f, params, shift=np.pi/2)`: Jacobian của `f` theo `params` bằng
   $$\frac{f(\theta + s e_i) - f(\theta - s e_i)}{2\sin s}$$, shape `params.shape + np.shape(f(params))`, mỗi tham số gọi `f` đúng hai lần, không sửa
   `params` (mục 5 lý thuyết).
2. `make_vqc(n_layers)`: trả `model(params, X)` cho mạch 2 qubit mô tả trong notebook (mỗi layer: `RY(x_w)`, `RY(θ)`, `RZ(θ)` trên
   từng wire, rồi CNOT 0 → 1; output $$\langle Z_0\rangle$$), dùng parameter broadcasting để một lần chạy QNode cho cả batch, và gắn
   QNode gốc vào `model.circuit`.
3. `loss_and_grad(model, params, X, y_pm)`: MSE với nhãn $$\pm 1$$ và gradient qua Jacobian của bạn.
4. `train_vqc(model, X, y_pm, n_layers, steps=100, lr=0.3, seed=0)`: gradient descent full batch từ khởi tạo
   $$U(-\pi, \pi)$$ ghi trong notebook; trả `(params, history)`.

Rồi chạy các cell `explore`: parameter-shift so với sai phân hữu hạn (có và không có shots), bảng $$L = 1..4$$, light cone, so
gradient với backprop của PennyLane, và bảng 5 lần chia với logistic regression, SVM RBF, hai MLP. Sau đó làm phần trắc
nghiệm của bài trong app.

## Tiêu chí đạt

- Parameter-shift đúng chính xác ($$10^{-12}$$) trên hàm lượng giác với $$s = \pi/2, \pi/4, 1$$, với output vô hướng và vector, với tham số
  nhiều chiều, và khớp sai phân hữu hạn trên một QNode PennyLane.
- Gọi `f` đúng $$2P$$ lần ở điểm dịch (cộng tối đa một lần ở điểm gốc), mỗi lần dịch đúng một tham số; không sửa input.
- `make_vqc` khớp mạch tham chiếu viết tay bằng numpy tới $$10^{-10}$$, output là mảng float shape `(B,)`; `model.circuit` là QNode cho cùng kết quả.
- `loss_and_grad` khớp sai phân hữu hạn của loss; `train_vqc` đúng khởi tạo, đúng một bước GD, tất định theo seed, và học được
  moons nhỏ (train accuracy ≥ 0.85).
- Cell `explore` in ra hai bảng ở mục 5 lý thuyết (vd. $$L = 4$$: test acc 0.980 ở lần chia seed 0; 5 lần chia: VQC 0.946 ± 0.022,
  SVM RBF 0.968 ± 0.016; thời gian phụ thuộc máy).

## Gợi ý

### Gợi ý 1

`np.ndindex(params.shape)` duyệt mọi chỉ số với mọi số chiều. Làm việc trên `np.array(params, dtype=float)` (một bản sao) để không
đụng mảng của người gọi. Gán `jac[idx] = ...` với `jac` shape `params.shape + out_shape` tự đặt kết quả đúng chỗ.

### Gợi ý 2

Trong QNode, `qml.RY(X[:, w], wires=w)` với `X[:, w]` là mảng dài $$B$$ khiến PennyLane chạy $$B$$ mạch một lần (broadcasting), và
`qml.expval` trả mảng dài $$B$$. Chain rule: nếu `jac` shape `params.shape + (B,)` thì `jac @ (2 * (out - y) / B)` cộng theo trục batch.
