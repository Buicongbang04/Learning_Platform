---
title: Tự cài LoRA trên nn.Linear
level: basic
services: []
files:
  - path: starter/lora.py
    note: lớp LoRALinear (5 phương thức) và 3 hàm TODO
  - path: tests/test_lora.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/14-fine-tuning-llm/exercises/basic/01-lora-from-scratch -q
---

## Mục tiêu

Tự viết LoRA từ một `nn.Linear` của PyTorch: nhánh hạng thấp, khởi tạo, hệ số $$\alpha / r$$, đóng băng trọng số gốc,
gộp (merge) vào trọng số và tách ra lại, gắn vào một LLM thật kiểu Qwen2 theo tên lớp. Làm xong bạn đọc được mọi tham số
của `LoraConfig` trong PEFT và biết mỗi cái đổi gì trong phép tính.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Đọc mục 3 phần lý thuyết. Trong `starter/lora.py`, chỉ dùng PyTorch:

1. `LoRALinear(base, r, alpha, dropout=0.0)` bọc một `nn.Linear` có sẵn (`base`, giữ nguyên làm thuộc tính `base`):
   - Hai tham số mới `lora_A` shape `(r, in_features)` và `lora_B` shape `(out_features, r)`, kiểu `float32`, cùng
     device với `base.weight`. `lora_A` khởi tạo `nn.init.kaiming_uniform_(..., a=math.sqrt(5))` (giống PEFT),
     `lora_B` bằng 0. `scaling = alpha / r`. `r` không dương thì `ValueError`.
   - Mọi tham số của `base` (weight, bias) đóng băng (`requires_grad=False`). `merged = False`.
   - `delta_weight()`: ma trận `(out_features, in_features)` mà LoRA cộng vào `base.weight`.
   - `forward(x)`: output của `base` cộng nhánh LoRA (dropout chỉ áp lên **đầu vào của nhánh LoRA**, rồi qua `A`, `B`,
     nhân `scaling`). Đã merge thì chỉ còn `base(x)`. Nhánh LoRA tính ở dtype của `lora_A`, cộng vào ở dtype của output.
   - `merge()`: cộng `delta_weight()` vào `base.weight` tại chỗ, `merged = True`; gọi khi đã merge thì không làm gì.
     `unmerge()`: ngược lại.
2. `inject_lora(model, target_modules, r, alpha, dropout=0.0) -> list[str]`: đóng băng **mọi** tham số của `model`, rồi
   thay mọi `nn.Linear` có phần cuối tên (sau dấu chấm cuối cùng) nằm trong `target_modules` bằng `LoRALinear` bọc chính
   nó. Trả danh sách tên đầy đủ đã thay, sắp xếp tăng dần. Không lớp nào khớp thì `ValueError`.
3. `count_parameters(model) -> (train được, tổng)`.
4. `merge_and_unload(model)`: merge mọi `LoRALinear` rồi thay nó bằng `nn.Linear` gốc bên trong; trả `model`.

## Tiêu chí đạt

- Lúc khởi tạo, output không đổi so với lớp gốc; bước backward đầu tiên chỉ `B` có gradient khác 0.
- Train vài bước thì trọng số gốc không đổi, chỉ `A`, `B` đổi.
- Output khớp công thức với `alpha / r` cho nhiều cặp `(r, alpha)`; dropout chỉ ở nhánh LoRA.
- Merge rồi unmerge: output và trọng số khớp tới `1e-5`; merge hai lần không cộng hai lần.
- Trên một Qwen2 tí hon tạo trong test: số tham số train được đúng công thức, **bằng** số của PEFT `get_peft_model`
  với cùng `r` và cùng lớp đích; train 5 bước giảm loss; `merge_and_unload` cho cùng logits và đúng số tham số gốc.

## Gợi ý

### Gợi ý 1

Viết phép tính dưới dạng ma trận trước: lớp gốc là $$y = x W^\top + b$$ với $$W$$ shape `(out, in)`. Nhánh LoRA phải cho
một ma trận cùng shape với $$W$$ từ hai ma trận nhỏ. Tự hỏi: nếu cả hai ma trận cùng bằng 0 thì gradient của mỗi cái
là gì? Nếu chỉ một cái bằng 0 thì sao?

### Gợi ý 2

Thay một module con theo tên: `model.get_submodule("model.layers.0.self_attn")` trả module cha, `setattr(cha, "q_proj",
lớp_mới)` thay con. Lấy danh sách tên **trước** khi thay (sửa cây module trong lúc duyệt `named_modules()` là lỗi kinh
điển). Merge là phép ghi tại chỗ vào `base.weight`: làm trong `torch.no_grad()` và đổi về dtype của trọng số gốc.
