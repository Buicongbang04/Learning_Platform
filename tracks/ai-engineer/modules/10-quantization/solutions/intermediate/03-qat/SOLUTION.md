# Lời giải: Quantization-aware training cho GPT mini

## Cách làm

**`fake_quant_ste`.** Tính scale absmax theo nhóm trên `w.detach()` (scale không nhận gradient), quantize rồi dequantize thành
`q`, và trả `w + (q - w).detach()`. Giá trị forward bằng `q`; với autograd, biểu thức chỉ còn `w` (phần trong `detach()` là hằng),
nên $$\partial \hat w/\partial w = 1$$: STE đồng nhất. Vì scale là absmax của chính nhóm, không phần tử nào bị kẹp, nên clipped STE
và STE đồng nhất trùng nhau ở đây.

**`QATLinear`.** Gán thẳng `self.weight = linear.weight` và `self.bias = linear.bias`: cùng đối tượng `nn.Parameter`, nên optimizer
cập nhật đúng bản float32 "chủ"; forward là `F.linear(x, fake_quant_ste(self.weight, bits, group_size), self.bias)`.

**`prepare_qat` / `convert_qat`.** `deepcopy` rồi thay module con: duyệt `list(model.modules())`, với mỗi `parent` duyệt
`list(parent.named_children())`, `setattr(parent, name, new)`. `prepare` chỉ bọc `type(c) is nn.Linear` có trọng số không thuộc một
`nn.Embedding` (giữ `lm_head` dùng chung ở float32, như mặc định của bài Intermediate 01). `convert` tạo `nn.Linear` mới với trọng số
`fake_quant_ste(...)` (giá trị đã nằm trên lưới) và bias cũ, đặt cùng device.

## Kết quả tham chiếu

int2 đối xứng nhóm 32 (ternary: mỗi trọng số là $$\{-s, 0, s\}$$ của nhóm), AdamW lr $$3\cdot10^{-4}$$ warmup 20 bước rồi cosine,
batch 16 × 256 token từ 1 000 bài train của module 04/05, weight decay 0, clip 1.0. Đánh giá trên đủ 100 bài validation.


| | PC: bpc (Δ so với gốc) | Laptop: bpc (Δ so với gốc) |
| --- | --- | --- |
| float32 gốc | 1.3472 | 1.5395 |
| PTQ int2 nhóm 32 | 2.4785 (+1.1314) | 2.3626 (+0.8231) |
| QAT 300 bước, rồi convert | 1.5686 (+0.2214) | 1.7257 (+0.1862) |
| fine-tune float32 300 bước | 1.3732 (+0.0260) | 1.5540 (+0.0145) |
| fine-tune float32 rồi PTQ | 2.5066 (+1.1594) | 2.3961 (+0.8566) |
| Thời gian QAT / đối chứng (GPU dùng chung) | 47 s / 47 s | 22 s / 23 s |

(Nguồn: notebook lời giải chạy bằng kernel GPU, `logs/nb_qat_gpu_*.log`; script tham chiếu cho cùng số với seed 0 và gần như
cùng số với seed 1: QAT 1.5691 / 1.7268, đối chứng 2.5138 / 2.3929, `logs/qat_gpu.log`.)

__CPU__

Đọc bảng:

- QAT lấy lại khoảng 80% khoảng cách giữa PTQ và float32 (PC: từ +1.13 về +0.22; laptop: từ +0.82 về +0.19). Ở 2 bit đối xứng mỗi
  trọng số chỉ còn $$\{-s, 0, s\}$$ của nhóm; model vẫn dùng được nhờ học lại cách phân bố trọng số trên lưới ternary.
- **Đối chứng tệ hơn cả PTQ trên checkpoint gốc.** Fine-tune float32 trên 1 000 bài (ít hơn nhiều so với dữ liệu train gốc của
  checkpoint PC) làm model trôi khỏi phân phối gốc (bpc float32 xấu đi 0.026) mà không làm nó dễ lượng tử hơn. Vậy toàn bộ cải thiện
  của QAT đến từ việc "thấy" lượng tử trong forward, không phải từ việc được train thêm.
- Loss train ở 10 bước đầu: QAT khoảng 5.4-5.5 nat, float32 khoảng 3.0 (PC) và 3.7 (laptop): model ternary bắt đầu tệ hơn 1.7-2.5
  nat; sau 300 bước còn cách khoảng 0.4-0.6 nat (`logs/qat_gpu.log`).
- So với PTQ tốt hơn: GPTQ int2 nhóm 32 **zero-point** (bài Intermediate 02, script tham chiếu) cho 1.5506 (PC) và 1.6871
  (laptop), ngang hoặc hơn QAT đối xứng 300 bước, không cần train. QAT không phải lựa chọn mặc định: thử PTQ tốt (zero-point, GPTQ)
  trước; QAT đáng khi đã ở mức bit/định dạng cố định mà PTQ vẫn không đạt, và khi có dữ liệu cùng phân phối với dữ liệu train gốc.
- Checkpoint dự phòng (train 600 bước trên chính 1 000 bài này): QAT cho 2.3356, **tốt hơn** float32 gốc 2.3438, vì fine-tune
  thêm trên dữ liệu train của chính nó vẫn còn lợi (fine-tune float32 cho 2.3263). Không có đối chứng thì dễ đọc nhầm thành "QAT làm
  model tốt hơn".

## Bẫy thường gặp

- Viết fake quantization bằng `torch.round` trần: gradient bằng 0, loss đứng yên, không có lỗi nào.
- Sao chép trọng số vào `QATLinear` thay vì dùng chung `Parameter`: optimizer tạo trước khi bọc sẽ cập nhật bản cũ.
- Bọc luôn `lm_head` dùng chung embedding: embedding đầu vào cũng bị lượng tử 2 bit, model tệ hơn nhiều.
- Đổi nhiều thứ cùng lúc giữa QAT và đối chứng (learning rate, weight decay, số bước): bài giữ mọi thứ giống nhau, weight decay 0
  cho cả hai, để chỉ còn một khác biệt là fake quantization.
- Đánh giá model QAT ở chế độ train (vẫn fake-quant, không sao) nhưng **xuất** quên `convert_qat`: tệp lưu trọng số float32 chưa
  lượng tử.

