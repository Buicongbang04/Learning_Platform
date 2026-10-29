---
title: Activation, đạo hàm và softmax ổn định số
level: basic
services: []
files:
  - path: starter/activations.py
    note: 9 hàm TODO
  - path: tests/test_activations.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/01-nn-from-scratch/exercises/basic/01-activations -q
---

## Mục tiêu

Tự viết bốn activation hay gặp (sigmoid, tanh, ReLU, GELU), đạo hàm của chúng và softmax, bằng numpy,
sao cho khớp PyTorch và **không bao giờ ra `nan` hay tràn số** với input lớn. Đây là các viên gạch mà
bài 03 và cả module ghép lại thành MLP.

## Đề bài

**Phần cứng:** CPU · ~45 phút

Trong `starter/activations.py`, viết:

1. `sigmoid`, `tanh`, `relu`, `gelu`: nhận `np.ndarray` float64 bất kỳ shape, trả mảng cùng shape.
   `gelu` là **bản xấp xỉ tanh** (công thức ở mục 2 phần lý thuyết), tức `gelu(approximate="tanh")`
   của PyTorch, không phải bản dùng hàm `erf`.
2. `sigmoid_grad`, `tanh_grad`, `relu_grad`, `gelu_grad`: đạo hàm của activation tương ứng **theo input
   `x`** (không phải theo output). `relu_grad(0)` bằng 0, theo quy ước của mọi framework.
3. `softmax(z, axis=-1)`: softmax theo trục `axis`, các trục khác giữ nguyên.

Yêu cầu ổn định số:

- `sigmoid(-1000)` và `sigmoid(1000)` chạy được khi bật `np.errstate(over="raise")` (tràn số là lỗi),
  ra gần 0 và gần 1. Underflow về 0 thì không sao.
- `softmax([1000, 1001, 1002])` không ra `nan`, tổng bằng 1. Một mảng 2 chiều có dòng logits rất lớn
  và dòng rất nhỏ cũng phải đúng ở **mọi dòng**.

Chỉ dùng numpy trong `activations.py` (test dùng torch để đối chiếu).

## Tiêu chí đạt

- `sigmoid`, `tanh`, `relu`, `gelu` khớp `torch.sigmoid`, `torch.tanh`, `torch.relu`,
  `F.gelu(approximate="tanh")` với `atol=1e-6` trên khoảng [-8, 8].
- Bốn hàm đạo hàm khớp sai phân trung tâm (`eps=1e-6`) với `atol=1e-5` và khớp `torch.autograd`.
- `relu_grad(0) == 0`.
- `sigmoid` và `sigmoid_grad` tại ±1000 không gây lỗi trong `np.errstate(over="raise")`, kết quả nằm trong [0, 1].
- `softmax` khớp `torch.softmax` trên cả `axis=-1` và `axis=0`, tổng mỗi dòng bằng 1, không `nan` với
  logits 1000 hay với dòng logits âm rất lớn nằm cạnh dòng dương rất lớn.

## Gợi ý

### Gợi ý 1

Đạo hàm của sigmoid và tanh viết được qua chính giá trị của hàm (xem bảng ở mục 2), nên tính hàm trước
rồi dùng lại. Với GELU, đặt tên cho biểu thức bên trong `tanh` rồi áp chain rule: đạo hàm của tích
$$\tfrac12 x \cdot (1 + \tanh u)$$ gồm hai số hạng. Softmax: mục 2 giải thích vì sao trừ đi một hằng
không đổi kết quả; nghĩ xem trừ hằng nào, và tính hằng đó **theo trục nào**.

### Gợi ý 2

Sigmoid tràn số vì `np.exp(-x)` với `x = -1000` là $$e^{1000}$$. Viết lại sigmoid sao cho số mũ luôn
**không dương**: với x âm, nhân cả tử và mẫu của $$\frac{1}{1+e^{-x}}$$ với $$e^{x}$$. Tính hai nhánh trên hai phần
của mảng (mặt nạ `x >= 0`), đừng dùng `np.where` với cả hai biểu thức vì `np.where` vẫn tính cả hai
nhánh trên toàn mảng. Softmax: `z.max(axis=axis, keepdims=True)`, `keepdims` để broadcasting trừ đúng
chiều.
