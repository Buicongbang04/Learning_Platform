---
title: Mô phỏng fp8 và fake quantization có STE
level: basic
services: []
files:
  - path: starter/fp8_ste.py
    note: 3 hàm/lớp TODO
  - path: tests/test_fp8_ste.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/10-quantization/exercises/basic/03-fp8-fake-quant-ste -q
---

## Mục tiêu

Hai mảnh còn thiếu trước khi quantize một model thật: định dạng **dấu phẩy động** 8 bit (E4M3, E5M2) mà GPU Hopper/Ada
dùng để train và serve, và **fake quantization** có straight-through estimator, nền của quantization-aware training (mục 6
phần lý thuyết). RTX 3060 (Ampere) không có tensor core fp8, nên ở đây ta mô phỏng fp8 bằng float32: kết quả số học giống
hệt, chỉ không nhanh hơn.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Trong `starter/fp8_ste.py`:

1. `fp8_round(x, fmt)` với `fmt` là `"e4m3"` hoặc `"e5m2"`: trả số fp8 gần nhất của mỗi phần tử (float32), có subnormal,
   hoà thì về mantissa chẵn, **bão hoà** ở số lớn nhất. Thông số từng định dạng có sẵn trong `FP8_FORMATS`. Không ép kiểu
   sang dtype fp8 của PyTorch (test kiểm mã nguồn), nhưng test dùng chính các dtype đó làm đáp án.
2. `FakeQuantSTE` (một `torch.autograd.Function`) và hàm bọc `fake_quant(x, scale, bits)`: forward là quantize rồi
   dequantize đối xứng với scale cho trước; backward là **clipped STE**.
3. `absmax_scale_per_channel(w, bits)`: scale absmax cho từng hàng, tách khỏi graph.

## Tiêu chí đạt

- `fp8_round` khớp từng bit với ép kiểu của PyTorch trên hàng trăm nghìn giá trị trải từ $$2^{-20}$$ tới $$2^{17}$$, cả hai
  định dạng; đếm đúng số giá trị biểu diễn được; sai số tương đối trong vùng normal không vượt $$2^{-(m+1)}$$.
- Hoà, subnormal và bão hoà đúng trên ví dụ tính tay.
- `fake_quant` cho đúng giá trị forward; gradient theo `x` bằng gradient phía sau ở chỗ không bị kẹp và bằng 0 ở chỗ bị kẹp;
  không có gradient cho scale.
- Một hồi quy tuyến tính có trọng số đi qua `fake_quant` 4 bit vẫn học được (loss giảm hơn 10 lần sau 100 bước SGD).

## Gợi ý

### Gợi ý 1

Một số fp8 dương normal có dạng $$2^{e}(1 + k/2^{m})$$; trong cùng một "binade" $$[2^e, 2^{e+1})$$ các số cách đều nhau một bước
$$2^{e-m}$$. Nên chỉ cần biết số mũ của từng phần tử để biết bước của nó, rồi làm tròn theo bước như quantization số nguyên.
Vùng subnormal là chỗ số mũ bị chặn dưới, bước không nhỏ thêm nữa.

### Gợi ý 2

`torch.autograd.Function`: `forward(ctx, ...)` lưu mặt nạ bằng `ctx.save_for_backward`, `backward(ctx, grad)` trả **một giá trị
cho mỗi input** của `forward` theo đúng thứ tự, `None` cho input không cần gradient. Nếu bạn viết forward bằng `torch.round`
ngay trong graph mà không qua `Function`, gradient bằng 0 ở mọi nơi và trọng số không bao giờ đổi.
