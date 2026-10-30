---
title: nn.Module từ bên trong, RMSNorm, GroupNorm và block residual
level: basic
services: []
files:
  - path: starter/modules.py
    note: 4 lớp, 3 hàm TODO
  - path: tests/test_modules.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/02-pytorch-deep-dive/exercises/basic/02-modules-norm-residual -q
---

## Mục tiêu

Viết các `nn.Module` mà một LLM hiện đại dùng (RMSNorm, block residual pre-norm, weight tying), tự cài GroupNorm
để thấy LayerNorm và InstanceNorm chỉ là hai trường hợp riêng, và nắm cách PyTorch đăng ký tham số: cái gì vào
`parameters()`, `state_dict()`, optimizer, và cái gì lọt ra ngoài.

## Đề bài

**Phần cứng:** CPU · ~75 phút

Sửa `starter/modules.py` (mục 2 và 6 lý thuyết):

1. `RMSNorm(dim, eps=1e-6)`: $$y = x / \sqrt{\mathrm{mean}(x^2) + \epsilon} \cdot w$$ trên chiều cuối, `weight` khởi tạo 1.
   Tính ở độ chính xác ít nhất float32 rồi trả đúng dtype của input. Khớp `torch.nn.RMSNorm`.
2. `group_norm(x, num_groups, weight, bias, eps)` cho input `(N, C, *)`, không gọi `F.group_norm`.
3. `Block(dim, zero_init=True)`: block MLP residual pre-norm $$x + \mathrm{fc_2}(\mathrm{GELU}(\mathrm{fc_1}(\mathrm{RMSNorm}(x))))$$,
   hidden $$4 \cdot \mathrm{dim}$$; `zero_init` đặt `fc2` bằng 0 để block là phép đồng nhất lúc khởi tạo.
4. `TinyLM(vocab_size, dim, n_layers)`: `embed` → `n_layers` block → `norm` → `head`, `head` dùng chung trọng số
   với `embed`. Các block phải được PyTorch "thấy".
5. `weight_decay_groups(model, wd)`: hai param group, weight decay cho tham số ≥ 2 chiều, không cho bias và norm.
6. `parameter_report(model)`: số tham số, số tham số train được, số phần tử buffer, tổng byte.

## Tiêu chí đạt

- `RMSNorm` khớp `torch.nn.RMSNorm` (cùng `state_dict`), bất biến khi nhân input với hằng dương, giữ dtype bf16,
  qua `gradcheck` ở float64.
- `group_norm` khớp `F.group_norm` với 1, 2, 4, 8 nhóm; 1 nhóm bằng `F.layer_norm` trên `(C, H, W)`, C nhóm bằng
  `F.instance_norm`; chạy được với input `(N, C, L)`; không phụ thuộc mẫu khác trong batch; C không chia hết thì `ValueError`.
- `Block` đúng tên thuộc tính và shape, là phép đồng nhất lúc khởi tạo nhưng `fc2` vẫn nhận gradient.
- `TinyLM` có đủ khoá trong `state_dict`, `head.weight is embed.weight`, số tham số đúng (dùng chung tính một lần),
  logits lúc khởi tạo bằng `norm(embed(idx)) @ embed.weight.T`; `.double()` chuyển mọi tham số.
- `weight_decay_groups` phủ đúng một lần mọi tham số `requires_grad`, kể cả tham số dùng chung; `parameter_report`
  đếm đúng tham số, buffer (`num_batches_tracked` là int64) và byte.

## Gợi ý

### Gợi ý 1

Gán một `nn.Module` hay `nn.Parameter` làm thuộc tính trong `__init__` là đăng ký nó. List Python thì không:
dùng `nn.ModuleList`. Weight tying chỉ là gán cùng một `Parameter` cho hai chỗ: `self.head.weight = self.embed.weight`
(shape `(vocab, dim)` khớp vì `Linear` lưu `(out, in)`). `model.parameters()` tự bỏ trùng; `state_dict()` thì không.

### Gợi ý 2

GroupNorm: gom các phần tử của mỗi (mẫu, nhóm) lại thành một dòng, chuẩn hoá theo dòng, đưa về shape cũ, rồi affine
theo kênh (để ý cách broadcast `weight` shape `(C,)` vào input `(N, C, *)`). RMSNorm: giống LayerNorm nhưng chỉ chia cho căn
của trung bình bình phương; nâng độ chính xác trước phép giảm, hạ về dtype gốc ở cuối.
