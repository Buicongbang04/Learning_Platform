# Lời giải: nn.Module từ bên trong, RMSNorm, GroupNorm và block residual

## Cách làm

**`RMSNorm`.** Không trừ mean, chỉ chia cho căn bậc hai của trung bình bình phương, rồi nhân `weight`. So với
LayerNorm bỏ được một phép giảm (mean) và tham số bias; LLaMA, Qwen, Mistral dùng nó. Tính trong
`promote_types(x.dtype, float32)`: input bf16 thì tổng bình phương tính ở fp32 (bf16 chỉ có 8 bit mantissa,
cộng 4096 số bình phương ở bf16 mất chính xác đáng kể), input float64 giữ float64 để `gradcheck` đúng.

**`group_norm`.** `x.reshape(N, G, -1)` gom mỗi (mẫu, nhóm) thành một dòng; mean và phương sai **lệch** theo dòng;
chuẩn hoá; reshape về shape gốc; affine theo kênh. Ba trường hợp đặc biệt rơi ra tự nhiên:

| `num_groups` | Chuẩn hoá trên | Tên |
| --- | --- | --- |
| 1 | mọi (C, H, W) của một mẫu | LayerNorm kiểu CNN |
| C | mỗi kênh của một mẫu | InstanceNorm |
| 1 < G < C | mỗi nhóm C/G kênh của một mẫu | GroupNorm (Wu & He 2018, mặc định 32 nhóm) |

Không thống kê nào đi qua chiều batch, nên kết quả của một mẫu không phụ thuộc mẫu khác (test so `x[:1]` với cả
batch): khác BatchNorm, và là lý do GroupNorm dùng được với batch nhỏ, với gradient accumulation (bài Intermediate 02).

**`Block`.** Pre-norm: chuẩn hoá ở **đầu nhánh**, đường tắt cộng thẳng $$x$$ chưa chuẩn hoá. Khi `fc2` bằng 0, nhánh
trả 0 nên block là đồng nhất, gradient theo $$x$$ đi thẳng qua đường tắt ($$2x$$ cho loss $$\sum y^2$$). `fc2` vẫn có
gradient khác 0 vì gradient theo trọng số là (input của `fc2`)ᵀ × (gradient theo output), mà input của `fc2` khác 0.
Đây là "zero-init residual" (Goyal et al. 2017 cho γ của BN cuối block; GPT-2 thu nhỏ projection theo
$$1/\sqrt{2L}$$ cùng ý).

**`TinyLM`.** `nn.ModuleList` cho các block; `self.head.weight = self.embed.weight`. `parameters()` bỏ trùng nên
đếm `embed` một lần: $$50 \cdot 8 + 3 \cdot (8 + 288 + 264) + 8 = 2\,088$$ tham số trong test, còn `state_dict()` có
cả `embed.weight` lẫn `head.weight` (cùng storage), nên tổng phần tử trong `state_dict` lớn hơn.

**`weight_decay_groups`.** Duyệt `model.parameters()` (đã bỏ trùng), lọc `requires_grad`, chia theo `p.dim() >= 2`.
Quy tắc "≥ 2 chiều" (nanoGPT dùng) bắt được weight của Linear, Conv, Embedding; bỏ bias và weight của norm. Lọc theo
tên (`"weight" in name`) là sai: weight của RMSNorm/LayerNorm cũng tên `weight`.

**`parameter_report`.** `numel()` và `element_size()` cho tham số và `model.buffers()`. Buffer của BatchNorm2d(4):
`running_mean` (4), `running_var` (4), `num_batches_tracked` (1 phần tử int64 = 8 byte).

## Bẫy thường gặp

- `self.blocks = [Block(...) ...]`: không lỗi, model vẫn chạy, nhưng tham số của block không có trong
  `parameters()` (optimizer không cập nhật), không có trong `state_dict()` (checkpoint thiếu), không đi theo `.to()`.
  Test đếm tham số và khoá `state_dict` bắt ngay. Bài Advanced 02 có đúng bug này trong một vòng train thật.
- Gán `self.head.weight = nn.Parameter(self.embed.weight.clone())`: hai tham số riêng, không còn tying.
- Phương sai không lệch (`unbiased=True`) trong GroupNorm: lệch so với PyTorch ở mọi nhóm.
- Post-norm (`norm(x + f(x))`) thay vì pre-norm: không còn là đồng nhất lúc khởi tạo, và gradient qua đường tắt bị
  chuẩn hoá ở mỗi block. Mục 6 lý thuyết nói vì sao Transformer sâu chuyển sang pre-norm.
