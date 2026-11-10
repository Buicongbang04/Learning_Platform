---
title: Hook, cache và phân rã residual stream
level: basic
services: []
files:
  - path: starter/hooks.py
    note: 3 hàm TODO
  - path: tests/test_hooks.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/08-interpretability/exercises/basic/01-hooks-residual-stream -q
---

## Mục tiêu

Viết công cụ mà mọi bài còn lại của module dùng: chạy GPT mini của module 05 một lần và ghi lại mọi activation cần cho
interpretability (residual stream trước và sau từng sublayer, ma trận attention, output từng head), rồi tách residual stream
cuối thành tổng các đóng góp. Làm xong bạn biết chính xác mỗi tensor nằm ở đâu trong model, trước hay sau LayerNorm, và vì
sao "residual stream là tổng" là nền của logit lens, direct logit attribution và activation patching.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Lớp `GPT` là lời giải bài Basic 01 của [module 05](../../../../05-transformers-llm-architecture/exercises/basic/01-gpt-mini/README.md)
(đọc docstring đầu tệp `gpt.py`: tên module con cố định, attention đọc được qua `blocks[i].attn.attn_dropout`, `lm_head` dùng
chung trọng số với `tok_emb`). Đọc mục 1 phần lý thuyết (residual stream, `register_forward_hook` và
`register_forward_pre_hook`). Trong `starter/hooks.py`, chỉ dùng PyTorch, không thư viện interpretability:

1. `run_with_cache(model, idx) -> (logits, cache)`: gắn hook, chạy forward một lần ở chế độ eval không gradient, gỡ hook.
   `cache` có đủ 7 khoá cho mỗi Block `l`: `resid_pre.l`, `attn_out.l`, `resid_mid.l`, `mlp_out.l`, `resid_post.l`,
   `pattern.l` (B, n_head, T, T) và `z.l` (B, T, n_head, head_dim). Định nghĩa từng khoá ở docstring đầu tệp.
2. `head_contributions(model, cache, layer)`: đóng góp của từng head vào residual stream, shape (B, T, n_head, C).
3. `residual_components(model, cache, idx)`: tách `resid_post` của Block cuối thành `tok_emb`, `pos_emb` và output của từng
   sublayer.

## Tiêu chí đạt

- Đủ khoá, đúng shape; `resid_pre.0` đúng bằng `tok_emb + pos_emb`.
- Sổ sách residual đúng: `resid_mid = resid_pre + attn_out`, `resid_post = resid_mid + mlp_out`, `resid_pre.(l+1) = resid_post.l`,
  và `lm_head(ln_f(resid_post` cuối`))` bằng logits.
- `attn_out`, `mlp_out` là output của sublayer tính từ input **đã** chuẩn hoá; `pattern` là softmax có mask nhân quả.
- Chạy ở chế độ eval (kể cả khi model đang train có dropout), không giữ graph, trả lại chế độ cũ, gỡ hết hook kể cả khi forward
  báo lỗi.
- Tổng `head_contributions` theo head cộng bias của `proj` bằng `attn_out`; đóng góp của head h bằng đúng phần `attn_out` mất đi
  khi xoá output của head đó.
- Tổng các thành phần của `residual_components` bằng residual stream cuối.

## Gợi ý

### Gợi ý 1

Forward pre-hook nhận `(module, args)` và thấy **input** của module; forward hook nhận `(module, args, output)`. Input của
Block là stream trước `ln1`; input của `ln2` là stream sau khi cộng attention; input của `attn.proj` là output các head nối lại.
Mỗi `register_*` trả về một handle có `.remove()`.

### Gợi ý 2

`proj` tính $$y = zW_O^\top + b$$ với $$z$$ là các head nối liền (head h là cột `h*head_dim .. (h+1)*head_dim`). Tách
`proj.weight` (shape `(C, C)`) theo trục **input** thành `n_head` khối rồi nhân từng khối với output của head tương ứng.
`torch.einsum` giúp viết gọn.
