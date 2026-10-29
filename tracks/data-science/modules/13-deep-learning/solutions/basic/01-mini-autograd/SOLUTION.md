# Lời giải: autograd vô hướng

## Cách làm

Mỗi phép toán làm hai việc: tính giá trị (forward) và để lại một closure `_backward` biết **đạo
hàm cục bộ** của phép đó. Closure đọc `out.grad` (gradient của loss theo đầu ra, đã được tính khi
tới lượt nút này) và nhân với đạo hàm cục bộ: đó chính là chain rule
$$\frac{\partial L}{\partial a} = \frac{\partial L}{\partial \text{out}}\cdot\frac{\partial \text{out}}{\partial a}$$.

| Phép | Đạo hàm cục bộ |
| --- | --- |
| $$a \cdot b$$ | theo a là $$b$$, theo b là $$a$$ |
| $$a^k$$ | $$k a^{k-1}$$ |
| $$e^a$$ | $$e^a$$ (dùng lại `out.data`) |
| $$\log a$$ | $$1/a$$ |
| $$\tanh a$$ | $$1 - \tanh^2 a$$ |
| ReLU | 1 nếu $$a > 0$$, ngược lại 0 |

`backward()` cần thứ tự sao cho **mọi nút con đã đẩy xong gradient trước khi nút cha đẩy tiếp**.
Thứ tự topo (cha trước con) đảo ngược đáp ứng điều đó. Bản đệ quy kinh điển (micrograd) gọn hơn
nhưng vỡ ở graph sâu hơn khoảng 1 000 tầng; một RNN unroll 1 000 bước hay một vòng lặp dài trong
code người dùng tạo graph sâu như vậy là bình thường. Lời giải dùng DFS với stack tường minh và cờ
"đã xử lý cha".

`fit_line` dựng lại graph mỗi bước (giống PyTorch: graph là động, tạo mới mỗi lần forward), chỉ hai
lá `w`, `b` sống qua các bước. Vì gradient cộng dồn, phải đặt `grad = 0` trước mỗi `backward`:
đúng vai trò của `optimizer.zero_grad()`.

## Liên hệ với PyTorch

| Bản tự viết | PyTorch |
| --- | --- |
| `Value._parents`, `_backward` | `tensor.grad_fn`, `grad_fn.next_functions` |
| `+=` vào `.grad` | `.grad` cộng dồn qua các lần `backward()` |
| `w.grad = 0` | `optimizer.zero_grad()` |
| dựng graph mới mỗi bước | define-by-run (dynamic graph) |

Khác biệt lớn nhất: PyTorch làm việc với tensor, nên đạo hàm cục bộ là tích Jacobian-vector (không
dựng cả Jacobian), và giải phóng graph sau `backward()` để tiết kiệm bộ nhớ (muốn gọi lại phải
`retain_graph=True`).

## Bẫy thường gặp

- Dùng `=` thay vì `+=` trong `_backward`: `a*a + a` cho 3 thay vì 7.
- Đặt `self.grad = 1.0` nhưng quên rằng gọi `backward()` hai lần sẽ cộng dồn lên các lá.
- Topo sort đệ quy: đúng trên ví dụ nhỏ, `RecursionError` trên graph sâu.
- `relu` tính gradient theo `out.data > 0` hay `self.data > 0` đều đúng; tại đúng 0 thì quy ước
  gradient bằng 0 (PyTorch cũng vậy).
