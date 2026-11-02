---
title: Layer Linear, ReLU, SoftmaxCrossEntropy có forward/backward
level: basic
services: []
files:
  - path: starter/layers.py
    note: 3 lớp, 7 phương thức TODO
  - path: tests/test_layers.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/01-nn-from-scratch/exercises/basic/03-layers-backprop -q
---

## Mục tiêu

Đóng gói backprop của mục 4 phần lý thuyết thành ba lớp `Linear`, `ReLU`, `SoftmaxCrossEntropy`, mỗi
lớp tự lo `forward` và `backward` của mình, ghép nối tiếp được như `nn.Module`. Đây là bộ khung mà
Intermediate 01 dùng để train MLP trên MNIST thật.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Trong `starter/layers.py`, quy ước giống phần lý thuyết: batch theo dòng, `x` shape `(N, in)`,
`W` shape `(in, out)`, $$\text{out} = xW + b$$. Viết:

1. `Linear(in_features, out_features, rng)`:
   - `__init__`: `self.W` khởi tạo **He** (phân phối chuẩn, trung bình 0, phương sai $$2/n_{in}$$), `self.b`
     bằng 0. Mọi số ngẫu nhiên lấy từ `rng` (một `np.random.Generator`), để cùng seed ra cùng trọng số.
   - `forward(x)`: trả $$xW + b$$, lưu lại những gì `backward` cần.
   - `backward(grad)`: `grad` là $$\partial L/\partial\,\text{out}$$ shape `(N, out)`. **Gán** `self.dW`, `self.db`
     (không cộng dồn qua các lần gọi), trả $$\partial L/\partial x$$ shape `(N, in)`.
2. `ReLU()`: `forward(x)` và `backward(grad)`; đạo hàm tại đúng 0 bằng 0.
3. `SoftmaxCrossEntropy()`:
   - `forward(logits, y)`: `logits` shape `(N, C)`, `y` là mảng nhãn nguyên shape `(N,)`. Trả cross-entropy
     **trung bình trên batch**, kiểu `float` Python, ổn định số với logits cỡ 1000.
   - `backward()`: không nhận tham số, trả $$\partial L/\partial\,\text{logits}$$ shape `(N, C)`.

Ghép lại, một bước forward/backward của MLP 2 tầng là:

```python
loss = ce.forward(l2.forward(relu.forward(l1.forward(X))), y)
l1.backward(relu.backward(l2.backward(ce.backward())))
```

Chỉ dùng numpy trong `layers.py`. Test kiểm từng layer bằng gradient check (float64) và đối chiếu cả
chuỗi với PyTorch cùng trọng số.

## Tiêu chí đạt

- `Linear(1000, 500, rng)`: `W` shape `(1000, 500)`, std lệch $$\sqrt{2/1000}$$ dưới 2%, `b` toàn 0; cùng
  seed cho cùng `W`.
- Gradient check từng layer (`dx`, `dW`, `db` của `Linear`; `dx` của `ReLU`; `dlogits` của
  `SoftmaxCrossEntropy`) đạt `rel < 1e-6`; `ReLU.backward` cho gradient 0 tại đúng `x = 0`.
- Gọi `forward`/`backward` hai lần liền cho `dW` như nhau (gán, không cộng dồn).
- Cả chuỗi `Linear → ReLU → Linear → SoftmaxCrossEntropy`: gradient của `W1, b1, W2, b2` và của `X` đạt
  `rel < 1e-6` so với sai phân.
- Loss và `dW1, db1, dW2, db2` khớp `torch.nn.functional.cross_entropy` + autograd cùng trọng số với `atol=1e-8`.
- Logits cỡ 1000: loss và gradient hữu hạn (không inf/nan, không cảnh báo tràn số), mỗi dòng gradient
  có tổng 0, `forward([[1000, 0]], [1]) == 1000`.

## Gợi ý

### Gợi ý 1

Viết `Linear.backward` theo mẹo "gradient có cùng shape với thứ nó là gradient" ở mục 4: mỗi gradient
chỉ có một cách nhân hai mảng sẵn có ra đúng shape. Bias được broadcast cho N dòng nên gradient của nó
là tổng theo một trục. Cross-entropy: mục 3 suy ra gradient theo logits gọn đến mức không cần dựng
Jacobian của softmax.

### Gợi ý 2

`SoftmaxCrossEntropy.forward` nên tính **log-softmax** trực tiếp (trừ max theo từng dòng, rồi
log-sum-exp), không tính softmax rồi mới `np.log`: xác suất underflow về 0 thì `log(0) = -inf`. Lưu
xác suất và `y` để `backward` dùng. Lấy log-xác suất của đúng lớp mỗi dòng bằng fancy indexing
`log_p[np.arange(N), y]`. Trong `backward`, nhớ loss là trung bình nên gradient chia thêm N; quên chia
thì gradient check báo sai số tương đối $$\frac{N-1}{N+1}$$.
