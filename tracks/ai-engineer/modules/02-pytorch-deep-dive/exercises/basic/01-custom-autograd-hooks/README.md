---
title: Custom autograd.Function và hook
level: basic
services: []
files:
  - path: starter/autograd_ext.py
    note: 3 Function, 2 hàm gọi, 2 hàm gắn hook
  - path: tests/test_autograd_ext.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/02-pytorch-deep-dive/exercises/basic/01-custom-autograd-hooks -q
---

## Mục tiêu

Mở rộng autograd ở hai chỗ mà AI Engineer hay cần: tự định nghĩa forward/backward cho một phép toán
(`torch.autograd.Function`), và gắn hook để nhìn activation, gradient mà không sửa model. Làm xong bạn viết được
straight-through estimator dùng ở quantization (module 10), gradient reversal, và công cụ log của riêng mình.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Sửa `starter/autograd_ext.py` (mục 1 lý thuyết):

1. `SiLUFunction`: forward $$x\,\sigma(x)$$, backward **tự viết** theo đạo hàm
   $$\sigma(x)\bigl(1 + x(1 - \sigma(x))\bigr)$$, lưu thứ backward cần bằng `ctx.save_for_backward`. `silu(x)` gọi
   nó qua `.apply`.
2. `RoundSTE`: forward `torch.round`, backward cho gradient đi qua nguyên vẹn (đạo hàm thật của làm tròn bằng 0
   gần như mọi nơi, nên không train được nếu không "giả vờ").
3. `GradReverse` và `grad_reverse(x, lambd=1.0)`: forward giữ nguyên giá trị, backward nhân gradient với
   $$-\lambda$$. `lambd` là số Python: backward vẫn phải trả một giá trị cho nó.
4. `record_activations(model, types)`: forward hook trên mọi module con có kiểu thuộc `types`, ghi mean, std,
   tỉ lệ bằng 0 của **output**, khoá là tên trong `named_modules()`. Trả kèm danh sách handle để gỡ.
5. `track_grad_norms(model)`: mỗi tham số cần gradient, ghi norm L2 của `.grad` **sau mỗi lần** gradient được
   cộng dồn vào `.grad` (gợi ý: `Tensor.register_post_accumulate_grad_hook`).

## Tiêu chí đạt

- `silu` khớp `F.silu` cả giá trị lẫn gradient, đi qua `SiLUFunction`, và qua `torch.autograd.gradcheck` ở float64.
- `RoundSTE` làm tròn đúng và trả gradient nguyên vẹn; `grad_reverse` giữ giá trị, đảo dấu và nhân $$\lambda$$
  gradient (mặc định $$\lambda = 1$$).
- `record_activations` chỉ gắn vào đúng kiểu module, số liệu đúng theo output, ghi đè mỗi lần forward, ngừng ghi
  sau khi gỡ handle.
- `track_grad_norms` bỏ qua tham số đóng băng, ghi norm sau khi cộng dồn (lần backward thứ hai không `zero_grad`
  cho norm gấp đôi), ngừng ghi sau khi gỡ handle.

## Gợi ý

### Gợi ý 1

Trong `forward` của `Function`, autograd tắt: bạn tính bằng tensor bình thường và tự lo backward. `backward`
nhận gradient theo output và phải trả **một giá trị cho mỗi input** của `forward`, theo đúng thứ tự (`None` cho
input không cần gradient). Lưu số Python bằng `ctx.lambd = ...`, lưu tensor bằng `ctx.save_for_backward`.

### Gợi ý 2

Forward hook có chữ ký `hook(module, inputs, output)`; tạo hook trong vòng lặp thì "đóng băng" tên bằng tham số
mặc định (`def hook(m, i, o, name=name)`), không thì mọi hook ghi vào tên cuối cùng. `register_hook` trên tensor
thấy gradient **trước** khi cộng dồn; `register_post_accumulate_grad_hook` thấy tham số **sau** khi `.grad` đã cộng.
