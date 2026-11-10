# Lời giải: int4 theo nhóm và đóng gói

## Cách làm

**Nhóm bằng `reshape`.** `w.reshape(out, in // g, g)` đưa mỗi nhóm `g` cột liền nhau của một hàng thành một dòng của trục cuối
(phần tử `w[r, c]` nằm ở nhóm `c // g` của hàng `r`). Max/min theo `dim=-1` cho scale của từng nhóm, `[..., None]` để
broadcast, rồi `reshape` trả về shape gốc. Không vòng lặp Python nào.

**Một biểu diễn cho cả hai chế độ.** Mã luôn không dấu $$0..2^b-1$$ và giải lượng tử luôn là $$(q - z)\,s$$:

- đối xứng: $$q_{max} = 2^{b-1} - 1 = 7$$, mã $$\mathrm{round}(w/s) \in [-7, 7]$$ cộng $$z = 8$$, nên mã $$0$$ không bao giờ được
  dùng (15 mức); đổi lại không phải lưu zero.
- bất đối xứng: zero-point riêng cho từng nhóm, dùng đủ 16 mức, tốn thêm một zero mỗi nhóm.

Đây cũng là cách nhiều định dạng thật lưu: `Q4_0` của llama.cpp lưu mã không dấu và trừ 8 khi giải lượng tử, `Q4_1` có thêm một
giá trị min cho mỗi khối 32.

**Đóng gói.** `c[..., 0::2] | (c[..., 1::2] << 4)`: phần tử chẵn ở 4 bit thấp. Tách ngược bằng `& 0x0F` và `>> 4`, rồi
`torch.stack([low, high], dim=-1).reshape(...)` để xếp xen kẽ lại; `torch.cat` đặt mọi phần tử chẵn trước mọi phần tử lẻ và
test round-trip bắt được ngay. Thứ tự bit là một **quy ước** của định
dạng: GPTQ/AutoGPTQ gói 8 giá trị vào một `int32`, `Q4_0` của llama.cpp đặt nửa đầu khối ở 4 bit thấp và nửa sau ở 4 bit cao.
Đọc nhầm quy ước thì model vẫn chạy nhưng ra rác.

**Bit mỗi trọng số.** Mỗi nhóm lưu thêm một scale fp16 (16 bit) và, nếu bất đối xứng, một zero:

$$
\text{bpw} = b + \frac{16 + b_{zero}}{g}
$$

| Cấu hình | bpw |
| --- | --- |
| int4, nhóm 128, đối xứng | 4.125 |
| int4, nhóm 32, đối xứng | 4.5 |
| int4, nhóm 32, zero 4 bit | 4.625 |
| int8 per-channel, hàng 4 096 | khoảng 8.004 |

Nên "4 bit" trên giấy thường là 4.1 tới 4.6 bit thật, cộng thêm những tensor giữ nguyên độ chính xác (embedding, norm).

## Kiểm bằng gì

- Ví dụ tính tay có điểm hoà ($$-3.5 \to -4$$) và một ngoại lai ở cột 5: chỉ scale của nhóm cột 4-7 hàng 0 đổi, nhóm cột 0-3
  vẫn giải lượng tử chính xác. Mutant chia nhóm xen kẽ (`reshape(out, g, in // g)`) hay theo hàng đều thất bại ở đây.
- Sai số không vượt nửa bước của nhóm (tính chất của làm tròn gần nhất khi không bị kẹp), và giảm dần khi nhóm nhỏ lại.
- Thứ tự bit kiểm bằng giá trị byte cụ thể (`[1, 2] -> 0x21`), không chỉ bằng round-trip: một cặp pack/unpack cùng sai quy ước
  vẫn round-trip đúng.

## Bẫy thường gặp

- Quên nới khoảng chứa 0 ở chế độ bất đối xứng: nhóm toàn dương có scale nhỏ hơn và zero âm bị kẹp về 0.
- `pack` khi mã chưa nằm trong 0..15 (quên cộng zero cho mã đối xứng có dấu): `<< 4` tràn sang bit cao, dữ liệu hỏng âm thầm.
- Tính dung lượng chỉ bằng `numel * bits / 8`, quên scale: với nhóm 32, scale chiếm 11% dung lượng.
