# Lời giải: mô phỏng fp8 và STE

## fp8: làm tròn theo binade

Một số fp8 dương normal là $$2^{e}(1 + k/2^{m})$$ với $$k \in [0, 2^m)$$, nên trong mỗi binade $$[2^e, 2^{e+1})$$ các số cách đều
nhau một bước $$2^{e-m}$$. Thuật toán:

1. $$e = \lfloor \log_2 \lvert x\rvert \rfloor$$, chặn dưới ở $$e_{min} = 1 - \text{bias}$$ (dưới đó là vùng subnormal: bước giữ
   nguyên $$2^{e_{min} - m}$$ tới tận 0).
2. bước $$= 2^{e - m}$$, làm tròn $$\lvert x\rvert$$ tới bội gần nhất của bước bằng `torch.round` (hoà về bội chẵn, tức mantissa
   chẵn). Làm tròn có thể đẩy lên $$2^{e+1}$$: vẫn là một số biểu diễn được nên không cần xử lý riêng.
3. kẹp ở số lớn nhất (bão hoà), gắn lại dấu. Với $$x = 0$$ dùng $$\log_2 1$$ để không ra `-inf`.

| | E4M3 | E5M2 |
| --- | --- | --- |
| bias, $$e_{min}$$ | 7, $$-6$$ | 15, $$-14$$ |
| lớn nhất | 448 | 57 344 |
| bước subnormal nhỏ nhất | $$2^{-9}$$ | $$2^{-16}$$ |
| sai số tương đối tối đa (normal) | $$2^{-4}$$ | $$2^{-3}$$ |
| số dương hữu hạn khác 0 | 126 | 123 |
| dùng cho | trọng số, activation (forward) | gradient (cần dải rộng) |

E4M3 kiểu "fn" (finite, no inf) chỉ dành một mã cho NaN nên lên được 448; E5M2 giữ inf/NaN như IEEE. Bản tự viết khớp từng bit với
ép kiểu `torch.float8_e4m3fn`/`torch.float8_e5m2` của PyTorch trên 260 nghìn giá trị (PyTorch bão hoà E4M3 khi ép kiểu trên CPU,
còn E5M2 thì tràn ra inf; bài này bão hoà cả hai, như Transformer Engine làm khi train).

Phần cứng: tensor core fp8 có từ Ada (RTX 40xx, sm_89) và Hopper (H100); RTX 3060 (Ampere, sm_86) không có, nên mọi phép fp8
ở đây là mô phỏng: đúng số học, không nhanh hơn.

## Fake quantization và STE

Forward: $$\hat w = s\cdot\mathrm{clamp}(\mathrm{round}(w/s), -q_{max}, q_{max})$$. Đạo hàm của `round` bằng 0 ở mọi nơi (và
không xác định ở điểm nhảy), nên nếu để autograd tự lo, gradient theo $$w$$ bằng 0 và không tham số nào thay đổi. STE
(Bengio và cộng sự, 2013) coi `round` như hàm đồng nhất khi lan truyền ngược:

$$
\frac{\partial \hat w}{\partial w} \approx \mathbb{1}\left[\,\lvert w/s\rvert \le q_{max}\right]
$$

Phần chỉ báo là **clipped STE**: chỗ bị kẹp thì đầu ra không đổi khi $$w$$ đổi, nên gradient 0 là đúng thật. Cài bằng
`torch.autograd.Function`: `forward` lưu mặt nạ bằng `ctx.save_for_backward`, `backward` trả `grad * mask` cho `x` và `None` cho
`scale`, `bits`. Một cách viết gọn khác hay gặp trong code QAT là `w + (q - w).detach()` (đồng nhất hoàn toàn, không cắt).

`absmax_scale_per_channel` tách scale khỏi graph (`detach`): scale theo absmax là hàm không trơn của $$w$$ (chỉ phụ thuộc phần
tử lớn nhất), để gradient đi qua nó vừa vô nghĩa vừa làm phần tử lớn nhất nhận gradient lạ. Các phương pháp học scale (LSQ,
PACT) có công thức gradient riêng cho scale.

## Kiểm bằng gì

- So từng bit với dtype fp8 của PyTorch trên dải $$2^{-20}..2^{17}$$ và lưới đều quanh 0; đếm số giá trị phân biệt sau làm tròn
  (127 cho E4M3, 124 cho E5M2, tính cả 0) bắt được lỗi subnormal mà so ngẫu nhiên dễ bỏ sót.
- Gradient của `fake_quant` kiểm bằng trọng số khác nhau cho từng phần tử, để biết chính xác phần tử nào bị cắt.
- Hồi quy tuyến tính 4 bit: với STE loss giảm hơn 10 lần sau 100 bước; dùng `torch.round` trần, loss đứng yên.
