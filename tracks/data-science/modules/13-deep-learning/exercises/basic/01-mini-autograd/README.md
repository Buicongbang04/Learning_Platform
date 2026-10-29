---
title: Tự viết autograd vô hướng
level: basic
services: []
files:
  - path: starter/autograd.py
    note: 6 phép toán, backward() và fit_line()
  - path: tests/test_autograd.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/13-deep-learning/exercises/basic/01-mini-autograd -q
---

## Mục tiêu

Hiểu `loss.backward()` của PyTorch làm gì bằng cách tự viết một bản thu nhỏ: mỗi phép toán ghi lại
nút cha và đạo hàm cục bộ, rồi backward đi ngược graph theo thứ tự topo và cộng dồn gradient. Sau
bài này, các lỗi như "quên `zero_grad`" hay "gradient bị cộng dồn" không còn là bí ẩn.

## Đề bài

Trong `starter/autograd.py`, lớp `Value` đã có sẵn phép cộng làm mẫu và các phép suy ra (`-`, `/`,
phép với số Python ở bên trái). Bạn viết:

1. `__mul__`, `__pow__` (số mũ là số cố định), `exp`, `log`, `tanh`, `relu`. Mỗi phép tạo một
   `Value` mới với `_parents` và gán `_backward` cộng dồn (`+=`) gradient vào các nút cha theo chain
   rule (mục 4 của module 01).
2. `backward()`: sắp các nút theo thứ tự topo **không dùng đệ quy** (graph trong test sâu 5 000
   tầng, vượt giới hạn đệ quy mặc định 1 000 của Python), đặt gradient của nút gốc bằng 1, rồi gọi
   `_backward()` theo thứ tự ngược.
3. `fit_line(xs, ys, lr, steps)`: fit $$y \approx wx + b$$ bằng gradient descent trên MSE trung bình,
   gradient lấy từ `Value`. Bắt đầu từ `w = b = 0`, nhớ đặt lại `grad = 0` mỗi bước.

Không import `torch` hay `numpy` trong `autograd.py` (test dùng torch để đối chiếu).

## Tiêu chí đạt

- Gradient của `a*b + a`, `a*a + a` (nút dùng lại nhiều lần) đúng.
- `relu`, `tanh`, `exp`, `log` khớp torch (float64) tới sai số tương đối 1e-9; `relu` có gradient
  0 khi đầu vào âm.
- 8 biểu thức ngẫu nhiên (cộng, nhân, trừ, chia, `tanh`, bình phương lồng 4 tầng) khớp gradient của
  torch.
- Graph sâu 5 000 phép nhân không gây `RecursionError`.
- `fit_line` tìm lại `w = 2`, `b = -1` (sai số 1e-3) trên dữ liệu không nhiễu, và một bước GD
  khớp công thức gradient của MSE.

## Gợi ý

### Gợi ý 1

Phép nhân: với `out = a * b` thì `a.grad += b.data * out.grad` và `b.grad += a.data * out.grad`.
`exp` dùng lại `out.data` vì đạo hàm của $$e^x$$ là chính nó. Dùng `+=` chứ không `=`: một nút có
thể là cha của nhiều nút (`a*a + a`), gradient từ mọi nhánh phải cộng lại.

### Gợi ý 2

Topo sort không đệ quy: stack chứa cặp `(nút, đã_xử_lý_cha)`. Lấy ra một nút lần đầu thì đẩy lại
nó với cờ `True` rồi đẩy các cha (cờ `False`); lấy ra với cờ `True` thì thêm vào danh sách thứ tự.
Đánh dấu đã thăm bằng `id(node)`.
