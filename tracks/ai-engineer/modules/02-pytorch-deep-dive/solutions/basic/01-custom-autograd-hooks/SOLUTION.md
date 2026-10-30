# Lời giải: custom autograd.Function và hook

## Cách làm

**`SiLUFunction`.** Forward tính $$s = \sigma(x)$$ một lần, lưu cả `x` và `s` (để backward khỏi tính lại sigmoid), trả
`x * s`. Backward:

$$
\frac{d}{dx}\,x\sigma(x) = \sigma(x) + x\,\sigma(x)\bigl(1 - \sigma(x)\bigr) = \sigma(x)\bigl(1 + x(1 - \sigma(x))\bigr)
$$

nhân với `grad_out`. Lưu `s` tốn thêm một tensor cỡ input; đó là đánh đổi bộ nhớ lấy tính toán, ngược với
checkpointing ở bài Intermediate 02. `gradcheck` ở float64 xác nhận đạo hàm (float32 quá thô cho sai phân hữu hạn).

**`RoundSTE`.** Forward `torch.round(x)`, backward trả nguyên `grad_out`. Đạo hàm thật của làm tròn bằng 0 ở mọi nơi
trừ các điểm nhảy, nên không có STE thì mọi tham số đứng trước phép làm tròn nhận gradient 0. Quantization-aware
training (module 10) dùng đúng mẹo này: forward thấy giá trị đã lượng tử hoá, backward coi như hàm đồng nhất.

**`GradReverse`.** Forward `x.view_as(x)`: trả một tensor mới chia storage (trả thẳng `x` cũng chạy, nhưng
PyTorch khuyên không trả nguyên input từ `Function` vì dễ rối với các phép sửa tại chỗ). `lambd` lưu vào `ctx`.
Backward trả `(-ctx.lambd * grad_out, None)`: hai input nên hai giá trị, `None` cho `lambd`. Đây là layer của
domain-adversarial training (Ganin & Lempitsky 2015): feature extractor bị đẩy theo hướng làm bộ phân loại miền
**tệ đi**, trong khi bộ phân loại miền vẫn học bình thường.

**`record_activations`.** Duyệt `named_modules()`, gắn `register_forward_hook` cho module đúng kiểu. Hook đọc
`output.detach()` (không giữ graph), tính ba số, `.item()` thành float, ghi đè `stats[name]`. Tên đi vào hook qua
tham số mặc định. Trả handle để người gọi `remove()`: hook quên gỡ là rò rỉ bộ nhớ và làm chậm mọi forward sau.

**`track_grad_norms`.** `p.register_post_accumulate_grad_hook(hook)`: hook nhận chính tham số, chạy **sau** khi
gradient của lần backward này đã cộng vào `p.grad`, nên norm ghi lại là norm của gradient sẽ được optimizer dùng.

## Kiểm bằng số

- `silu` so `F.silu` trên 101 điểm trong $$[-8, 8]$$: khớp ở `assert_close` mặc định của float64, cả giá trị và gradient.
- Test cố ý gọi backward hai lần không `zero_grad`: với post-accumulate hook, norm lần hai đúng bằng 2 lần lần
  một. Với `register_hook` trên tensor (sai), lần hai ghi lại norm của riêng gradient mới, bằng lần một.

## Bẫy thường gặp

- Backward thiếu số hạng ($$\sigma(x)$$ thay vì công thức đủ): `gradcheck` báo sai ngay.
- `GradReverse.backward` chỉ trả một giá trị: `RuntimeError: function GradReverseBackward returned an incorrect
  number of gradients (expected 2, got 1)`.
- Hook tạo trong vòng lặp mà không gắn `name=name`: mọi hook ghi vào tên của module cuối (late binding của closure Python).
- Lấy std của **input** thay vì output của module, hoặc `std(unbiased=False)`: test so với `output.std()` mặc định.
- Giữ `output` (không `detach`) trong dict: giữ cả graph của batch đó, bộ nhớ tăng theo mỗi forward.
