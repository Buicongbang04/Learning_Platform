---
title: int4 theo nhóm và đóng gói hai giá trị vào một byte
level: basic
services: []
files:
  - path: starter/int4.py
    note: 5 hàm TODO
  - path: tests/test_int4.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/10-quantization/exercises/basic/02-int4-groupwise-packing -q
---

## Mục tiêu

Đi từ per-channel sang **group-wise**, mức chia scale mà gần như mọi định dạng 4 bit dùng (GPTQ, AWQ, `Q4_0` của llama.cpp,
NF4 của bitsandbytes), rồi tự đóng gói mã 4 bit vào byte và tính đúng số bit thực sự tốn cho mỗi trọng số. Làm xong bạn đọc
được "4.5 bit/weight" trên model card nghĩa là gì và vì sao tệp int4 không nhỏ đúng 8 lần so với fp32.

## Đề bài

**Phần cứng:** CPU · ~45 phút

Trong `starter/int4.py` (quy ước nhóm, mã không dấu và thứ tự bit ghi ở docstring đầu tệp):

1. `quantize_groupwise(w, bits=4, group_size=128, symmetric=True) -> (codes, scales, zeros)` cho trọng số shape
   `(out_features, in_features)`; mỗi nhóm là `group_size` cột liền nhau trên một hàng. Hai chế độ: đối xứng (absmax, zero
   là hằng) và bất đối xứng (zero-point riêng cho từng nhóm).
2. `dequantize_groupwise(codes, scales, zeros, group_size)`.
3. `pack_int4(codes)` và `unpack_int4(packed)`: hai mã 4 bit trong một `uint8`.
4. `bits_per_weight(bits, group_size, scale_bits=16, zero_bits=0)`.

Không dùng vòng lặp Python qua từng phần tử: mọi thứ làm được bằng `reshape` và phép toán trên cả tensor.

## Tiêu chí đạt

- Mã, scale, zero đúng trên ví dụ tính tay cho cả hai chế độ; nhóm là cột liền nhau của **một** hàng (một ngoại lai chỉ
  làm hỏng scale của nhóm chứa nó); `in_features` không chia hết cho `group_size` thì `ValueError`.
- Sai số sau giải lượng tử không vượt nửa bước lượng tử của nhóm; nhóm càng nhỏ, sai số càng nhỏ.
- `pack_int4` đúng thứ tự bit (phần tử chẵn ở 4 bit thấp), `unpack_int4` là phép ngược trên tensor nhiều chiều, từ chối
  độ dài lẻ và mã lớn hơn 15.
- `bits_per_weight` đúng với cả scale và zero.

## Gợi ý

### Gợi ý 1

`w.reshape(out_features, in_features // group_size, group_size)` biến mỗi nhóm thành một hàng của trục cuối; max/min theo
`dim=-1` cho scale từng nhóm, và phép chia broadcast được khi thêm một trục `[..., None]`. Kiểm bằng tay: phần tử
`w[r, c]` phải nằm ở nhóm `c // group_size` của hàng `r`.

### Gợi ý 2

Slicing bước 2 (`[..., 0::2]`, `[..., 1::2]`) lấy phần tử chẵn và lẻ của trục cuối. Dịch bit `<< 4` trên `uint8` không tràn
khi mã nhỏ hơn 16. Để tách ngược, `& 0x0F` lấy 4 bit thấp và `>> 4` lấy 4 bit cao; xếp lại xen kẽ bằng `torch.stack(...,
dim=-1)` rồi `reshape`, không phải `torch.cat`.
