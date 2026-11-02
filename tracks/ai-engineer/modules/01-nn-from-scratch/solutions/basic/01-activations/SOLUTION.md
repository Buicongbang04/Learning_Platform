# Lời giải: activation, đạo hàm và softmax ổn định số

## Cách làm

Mỗi activation tính từng phần tử nên chỉ là một biểu thức numpy. Đạo hàm của sigmoid và tanh viết qua
chính giá trị hàm, nên tính hàm rồi dùng lại:

| Hàm | Đạo hàm theo x |
| --- | --- |
| $$\sigma(x)$$ | $$\sigma(x)(1 - \sigma(x))$$ |
| $$\tanh x$$ | $$1 - \tanh^2 x$$ |
| $$\max(0, x)$$ | 1 nếu $$x > 0$$, ngược lại 0 (kể cả tại 0) |
| GELU tanh | $$\tfrac12(1 + t) + \tfrac12 x (1 - t^2)\,u'$$ |

Với GELU, đặt $$u = \sqrt{2/\pi}\,(x + 0.044715x^3)$$ và $$t = \tanh u$$, thì $$\mathrm{GELU}(x) = \tfrac12 x(1 + t)$$.
Quy tắc tích cho hai số hạng: $$\tfrac12(1 + t)$$ từ đạo hàm của $$\tfrac12 x$$, và $$\tfrac12 x \cdot (1 - t^2)\,u'$$ từ
đạo hàm của $$\tanh u$$ (chain rule), với $$u' = \sqrt{2/\pi}\,(1 + 3 \cdot 0.044715x^2)$$. Đây là đạo hàm của **bản
xấp xỉ**, khớp `F.gelu(approximate="tanh")` của PyTorch; bản chính xác $$x\Phi(x)$$ có đạo hàm
$$\Phi(x) + x\varphi(x)$$. Trên [-8, 8] hai bản lệch nhau tới 5e-4 ở giá trị hàm và 9e-4 ở đạo hàm, lớn
hơn nhiều so với `atol=1e-6` của test, nên trộn hai bản là bị bắt ngay.

## Ổn định số

**Sigmoid.** `1 / (1 + np.exp(-x))` với $$x = -1000$$ tính $$e^{1000}$$, tràn thành `inf` (kết quả cuối vẫn
ra 0 nhưng numpy đã phát cảnh báo overflow, và `np.errstate(over="raise")` biến nó thành lỗi). Lời giải
chỉ tính $$e = e^{-|x|} \in (0, 1]$$, không bao giờ tràn:

- $$x \ge 0$$: $$\sigma(x) = \frac{1}{1 + e}$$.
- $$x < 0$$: nhân tử và mẫu với $$e^{x}$$, $$\sigma(x) = \frac{e^{x}}{1 + e^{x}} = \frac{e}{1 + e}$$.

`np.where` an toàn ở đây vì cả hai nhánh chỉ dùng `e` đã an toàn. Nếu viết `np.where(x >= 0, 1/(1+np.exp(-x)),
np.exp(x)/(1+np.exp(x)))` thì vẫn tràn: `np.where` tính **cả hai** biểu thức trên toàn mảng rồi mới chọn.
Underflow ($$e^{-1000}$$ về 0) thì vô hại, vì vậy test chỉ bật `over="raise"`.

**Softmax.** Trừ max theo đúng trục với `keepdims=True` (mục 2 lý thuyết): số mũ lớn nhất của mỗi
dòng là $$e^0 = 1$$, mẫu số luôn $$\ge 1$$, không có `inf/inf` hay `0/0`. Trừ max của **cả mảng** vẫn đúng
về toán nhưng dòng `[-1000, -999]` đứng cạnh dòng `[1000, 1001]` sẽ thành $$e^{-2000}$$, underflow hết về 0,
ra `0/0 = nan`; test `test_softmax_max_is_taken_per_row` bắt lỗi này.

## Liên hệ với PyTorch

| Bản tự viết | PyTorch |
| --- | --- |
| `sigmoid` tách theo dấu | `torch.sigmoid` (kernel cũng xử lý ổn định) |
| `gelu` xấp xỉ tanh | `F.gelu(x, approximate="tanh")`; mặc định `approximate="none"` dùng `erf` |
| `softmax(z, axis)` | `torch.softmax(z, dim)`; cần log thì dùng `log_softmax`, đừng `log(softmax)` |
| `relu_grad(0) = 0` | autograd của `torch.relu` cũng cho 0 tại 0 |

## Bẫy thường gặp

- Viết `*_grad` theo output thay vì input (ví dụ `sigmoid_grad(s)` nhận sẵn $$\sigma$$): đề yêu cầu theo `x`.
- Quên `keepdims=True` khi trừ max theo trục cuối: `z.max(axis=-1)` của mảng `(6, 10)` có shape `(6,)`,
  trừ vào `(6, 10)` thì lỗi broadcasting; tệ hơn, với mảng vuông `(n, n)` nó chạy êm nhưng trừ max của
  dòng `j` vào **cột** `j`. `keepdims=True` giữ shape `(6, 1)` nên broadcast đúng chiều với mọi `axis`.
