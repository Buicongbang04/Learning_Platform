---
title: Conv2d bằng numpy với im2col, forward và backward
level: basic
services: []
files:
  - path: starter/conv.py
    note: 4 hàm TODO
  - path: tests/test_conv.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/03-computer-vision/exercises/basic/01-conv2d-im2col -q
---

## Mục tiêu

Tự viết tầng convolution mà mọi CNN dùng, đúng như cách các thư viện CPU làm: trải ảnh thành ma trận bằng
**im2col** để cả tầng conv chỉ còn **một phép nhân ma trận**, rồi viết backward bằng **col2im**. Làm xong bạn
đọc được shape của mọi tensor trong một CNN và biết vì sao conv tốn bộ nhớ hơn vẻ ngoài của nó.

## Đề bài

**Phần cứng:** CPU · ~90 phút

Đọc mục 1 phần lý thuyết trước. Trong `starter/conv.py`, quy ước giống PyTorch: `x` shape `(N, C, H, W)`,
trọng số `W` shape `(F, C, kh, kw)`, `b` shape `(F,)`, output `(N, F, OH, OW)` với
$$OH = \lfloor (H + 2p - k_h)/s \rfloor + 1$$ (hàm `output_size` có sẵn). Padding bằng 0, đều hai phía.

1. `im2col(x, kh, kw, stride, padding)`: trả `cols` shape `(N·OH·OW, C·kh·kw)`. Dòng thứ
   $$n \cdot OH \cdot OW + i \cdot OW + j$$ là cửa sổ mà output `(n, :, i, j)` nhìn thấy, trải phẳng theo thứ tự
   `(c, di, dj)`, tức cùng thứ tự với `W.reshape(F, -1)`.
2. `col2im(cols, x_shape, kh, kw, stride, padding)`: phép "ngược" của im2col theo nghĩa adjoint: rải mỗi dòng
   về đúng cửa sổ của nó, **cộng** các giá trị rơi vào cùng một pixel, rồi cắt bỏ phần padding.
3. `conv2d_forward(x, W, b, stride, padding)`: trả `(out, cache)`. Forward là im2col, một phép nhân với
   `W.reshape(F, -1)`, cộng bias, rồi sắp lại về NCHW.
4. `conv2d_backward(dout, cache)`: nhận $$\partial L/\partial\,\text{out}$$ shape `(N, F, OH, OW)`, trả `(dx, dW, db)`.

Chỉ dùng numpy, không `sliding_window_view` hay `as_strided` (bạn tự cắt lát). Không vòng lặp Python qua
`N`, `OH`, `OW`; vòng lặp qua `kh × kw` vị trí trong kernel thì được.

## Tiêu chí đạt

- `im2col` khớp `torch.nn.functional.unfold` (sau khi đổi trục) tới `1e-12` trên 6 cấu hình: kernel vuông và
  chữ nhật (2×3), kernel 1×1 và 5×5, stride 1/2/3, padding 0/1/2.
- `col2im` là adjoint của `im2col`: $$\langle \mathrm{im2col}(x), c\rangle = \langle x, \mathrm{col2im}(c)\rangle$$; kernel
  2×2 stride 1 trên ảnh 3×3 cho pixel giữa giá trị 4 (nằm trong 4 cửa sổ).
- `conv2d_forward` khớp `F.conv2d` tới `1e-10` trên cả 6 cấu hình.
- `dx, dW, db` khớp autograd của PyTorch tới `1e-10`, và gradient check (sai phân trung tâm) đạt `rel < 1e-7`.
- Forward + backward một tầng conv 3×3 của ResNet CIFAR (64 ảnh 16×32×32, 32 bộ lọc) dưới 10 giây (lời giải
  mẫu khoảng 0.3 giây; vòng lặp qua từng vị trí output mất cỡ 30 giây chỉ riêng forward).

## Gợi ý

### Gợi ý 1

Với mỗi vị trí `(di, dj)` trong kernel, các pixel mà vị trí đó "chạm" tới trên mọi cửa sổ là một lát cắt có
bước nhảy của ảnh đã pad: `xp[:, :, di : di + s*OH : s, dj : dj + s*OW : s]`, shape `(N, C, OH, OW)`. Gom
`kh × kw` lát cắt vào một mảng `(N, C, kh, kw, OH, OW)`, rồi `transpose` cho `(n, oh, ow)` lên trước và
`(c, di, dj)` ra sau trước khi `reshape`.

### Gợi ý 2

Forward là $$\text{out} = \text{cols}\,W_{mat}^\top + b$$ với $$W_{mat}$$ shape `(F, C·kh·kw)`. Đặt $$D$$ là `dout` sắp
lại thành `(N·OH·OW, F)` (cùng thứ tự dòng với `cols`). Như layer Linear ở module 01:
$$dW_{mat} = D^\top\,\text{cols}$$, $$db$$ là tổng của `dout` trên mọi trục trừ trục `F`, còn
$$d\,\text{cols} = D\,W_{mat}$$ rồi `col2im` để ra `dx`. `col2im` dùng đúng lát cắt của gợi ý 1 nhưng với `+=`:
viết `=` thì pixel thuộc nhiều cửa sổ chỉ giữ giá trị của cửa sổ cuối.
