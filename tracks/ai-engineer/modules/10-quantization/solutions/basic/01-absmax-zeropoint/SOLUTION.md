# Lời giải: int8 absmax và zero-point

## Cách làm

Cả hai phép lượng tử hoá là một phép biến đổi affine rồi làm tròn và kẹp:

$$
q = \mathrm{clamp}\left(\mathrm{round}\left(\frac{x}{s}\right) + z,\ q_{min},\ q_{max}\right), \qquad \hat x = s\,(q - z)
$$

| | absmax (đối xứng) | zero-point (bất đối xứng) |
| --- | --- | --- |
| Dải mã | $$[-(2^{b-1}-1),\ 2^{b-1}-1]$$, `int8` | $$[0,\ 2^b-1]$$, `uint8` |
| Scale | $$s = \max\lvert x\rvert / (2^{b-1}-1)$$ | $$s = (hi - lo)/(2^b - 1)$$, $$lo = \min(x_{min}, 0)$$, $$hi = \max(x_{max}, 0)$$ |
| Zero-point | $$z = 0$$ | $$z = \mathrm{round}(-lo/s)$$ kẹp vào dải mã |
| Hợp với | trọng số (phân phối quanh 0) | activation sau ReLU/GELU, dữ liệu lệch một phía |

Một hàm phụ `_amax(t, axis)` lấy max theo mọi trục trừ `axis` với `keepdim=True`; nhờ vậy scale per-channel tự broadcast khi
chia `x / scale`, và cùng một đoạn code phục vụ per-tensor (`axis=None`) lẫn per-channel. `_amin` là `-_amax(-t)`.

Các chi tiết dễ sai:

- **Khoảng chứa 0.** Nới $$[lo, hi]$$ để chứa 0 rồi làm tròn $$z$$ thành số nguyên thì số 0 được biểu diễn chính xác. Điều này
  quan trọng thật: padding, activation sau ReLU, và các trọng số bằng 0 phải giải lượng tử ra đúng 0, nếu không sai số bị cộng
  dồn có hệ thống. Với dữ liệu toàn dương $$[2, 10]$$, scale là $$10/255$$ chứ không phải $$8/255$$.
- **Kẹp trước khi đổi kiểu.** Với $$x = [-1.5, 0, 253.5]$$: $$s = 1$$, $$z = \mathrm{round}(1.5) = 2$$, phần tử cuối
  $$\mathrm{round}(253.5) + 2 = 256$$. Đổi sang `uint8` trước khi kẹp thì 256 thành 0: giá trị lớn nhất biến thành nhỏ nhất.
- **Làm tròn nửa về số chẵn.** `torch.round(-12.5) = -12`, `torch.round(2.5) = 2`. Đây cũng là cách PyTorch, numpy và phần
  cứng làm (không thiên lệch khi cộng dồn nhiều phép làm tròn); `floor(x + 0.5)` cho kết quả khác ở các điểm hoà.
- **Kênh toàn 0** cho scale 0 và phép chia ra `nan`; thay scale bằng 1 (mã nào cũng là 0, giải lượng tử vẫn ra 0).
- **Giải lượng tử zero-point** phải đưa `q` về kiểu có dấu trước khi trừ $$z$$: trừ trên `uint8` quay vòng.

## Kiểm bằng gì

- Ví dụ tính tay chọn scale là luỹ thừa của 2 ($$0.25$$) để mọi phép chia chính xác trong float32, kiểm được cả các điểm hoà.
- Mã zero-point khớp `torch.quantize_per_tensor` và `torch.quantize_per_channel` (API quantized tensor cũ của PyTorch, nay đã
  bị đánh dấu deprecated, thay bằng `torchao`) khi đưa cùng scale và zero-point: tham chiếu độc lập cho phép làm tròn và kẹp.
- Quy luật 6 dB mỗi bit: với dữ liệu phân phối đều trên $$[-1, 1]$$, nhiễu lượng tử xấp xỉ phân phối đều trên một bước $$s$$,
  phương sai $$s^2/12$$; mỗi bit thêm chia đôi $$s$$, nhiễu giảm 4 lần, tức $$10\log_{10}4 \approx 6.02$$ dB. Hiệu SQNR giữa 8 và 4
  bit trên dữ liệu đó nằm trong $$[22, 26]$$ dB.
- Hai phép so sánh định tính: zero-point thắng absmax trên dữ liệu toàn dương (absmax bỏ phí nửa dải mã âm), per-channel thắng
  per-tensor khi các hàng chênh nhau 100 lần về độ lớn (hàng nhỏ bị làm tròn hết về vài mã quanh 0 nếu dùng chung scale).

## Liên hệ thực tế

| Bản tự viết | Thư viện |
| --- | --- |
| `absmax_quantize(w, 8, axis=0)` | int8 weight-only per-channel (`torchao`, TensorRT-LLM W8A16) |
| `zeropoint_quantize(x, 8)` | activation int8 bất đối xứng của PyTorch eager quantization, ONNX Runtime |
| `sqnr_db` | thước đo nhanh để chọn bit và mức chia trước khi đo trên model thật |
