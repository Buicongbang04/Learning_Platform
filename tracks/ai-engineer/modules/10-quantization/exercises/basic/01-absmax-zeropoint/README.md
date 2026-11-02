---
title: int8 absmax và zero-point, per-tensor và per-channel
level: basic
services: []
files:
  - path: starter/quant.py
    note: 5 hàm TODO
  - path: tests/test_quant.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/10-quantization/exercises/basic/01-absmax-zeropoint -q
---

## Mục tiêu

Tự viết hai phép lượng tử hoá nền tảng của mục 2 phần lý thuyết, absmax (đối xứng) và zero-point (bất đối xứng), ở cả
mức per-tensor và per-channel, rồi đo sai số bằng SQNR. Mọi kỹ thuật phía sau (int4 theo nhóm, GPTQ, AWQ, k-quant của
llama.cpp) đều dựng trên hai công thức này, chỉ khác cách chọn scale.

## Đề bài

**Phần cứng:** CPU · ~45 phút

Trong `starter/quant.py`, chỉ dùng phép toán tensor của PyTorch (không dùng `torch.quantize_per_tensor` hay `torch.ao`):

1. `absmax_quantize(x, bits=8, axis=None) -> (q, scale)` và `absmax_dequantize(q, scale)`. Mã đối xứng
   $$q \in [-q_{max}, q_{max}]$$ với $$q_{max} = 2^{b-1} - 1$$, kiểu `torch.int8`.
2. `zeropoint_quantize(x, bits=8, axis=None) -> (q, scale, zero_point)` và `zeropoint_dequantize(q, scale, zero_point)`.
   Mã $$q \in [0, 2^b - 1]$$ kiểu `torch.uint8`; khoảng $$[lo, hi]$$ được nới để luôn chứa 0; `zero_point` là số nguyên.
3. `sqnr_db(x, x_hat)`: tỉ số tín hiệu trên nhiễu lượng tử tính bằng dB.

Quy ước `axis`, làm tròn và kênh toàn 0 ghi trong docstring đầu tệp. Docstring từng hàm cho công thức chính xác.

## Tiêu chí đạt

- Mã và scale đúng trên ví dụ tính tay, kể cả các giá trị nằm đúng giữa hai mã (làm tròn nửa về số chẵn như `torch.round`).
- `axis` chọn đúng trục được giữ lại, scale broadcast được với `x` (kể cả `axis=-1` và tensor 3 chiều).
- Kênh toàn 0 không sinh `nan`/`inf`.
- Zero-point: khoảng lượng tử chứa 0, số 0 giải lượng tử ra đúng 0, mã ở biên được kẹp chứ không quay vòng `uint8`;
  mã khớp `torch.quantize_per_tensor` và `torch.quantize_per_channel` khi dùng cùng scale và zero-point.
- SQNR đúng công thức; mỗi bit thêm khoảng 6 dB trên dữ liệu phân phối đều; zero-point thắng absmax trên dữ liệu toàn
  dương, per-channel thắng per-tensor khi các hàng có độ lớn chênh nhau.

## Gợi ý

### Gợi ý 1

Viết một hàm phụ lấy max (hoặc min) theo mọi trục **trừ** trục `axis`, với `keepdim=True`: một hàm đó phục vụ cả absmax lẫn
zero-point, và scale tự broadcast được khi chia `x / scale`. Với `axis=None` thì max của cả tensor.

### Gợi ý 2

Thứ tự trong zero-point: tính scale từ khoảng đã nới chứa 0, làm tròn zero-point thành số nguyên (để số 0 được biểu diễn
chính xác, quan trọng với padding và activation sau ReLU), cộng zero-point, rồi mới kẹp và đổi kiểu. Đổi sang `uint8` trước
khi kẹp thì 256 thành 0. Khi giải lượng tử, đưa `q` về kiểu có dấu trước khi trừ.
