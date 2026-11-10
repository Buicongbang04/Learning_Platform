---
title: GPT mini tự dựng (LayerNorm, causal self-attention, MLP, Block, sinh văn bản)
level: basic
services: []
files:
  - path: starter/gpt.py
    note: 5 lớp, 9 chỗ TODO
  - path: tests/test_gpt.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/05-transformers-llm-architecture/exercises/basic/01-gpt-mini -q
---

## Mục tiêu

Tự dựng một Transformer decoder-only kiểu GPT-2 từ các phép nhân ma trận: LayerNorm, multi-head causal
self-attention, MLP, Block pre-norm, embedding vị trí, weight tying và vòng sinh văn bản. Lớp `GPT` này là model mà
cả module dùng lại: bài Intermediate 01 train nó trên Wikipedia tiếng Việt, module 08 gắn hook vào nó để mổ xẻ, module
10 quantize nó.

## Đề bài

**Phần cứng:** CPU · ~90 phút

Đọc mục 1 và 2 phần lý thuyết. Trong `starter/gpt.py`, điền các chỗ `# TODO` theo docstring:

1. `LayerNorm.forward`: chuẩn hoá theo trục cuối với phương sai **lệch** (chia $$D$$), $$\epsilon$$ cộng vào phương sai bên
   trong căn, rồi nhân `weight`, cộng `bias`. Không dùng `F.layer_norm`.
2. `CausalSelfAttention`: đăng ký mask nhân quả làm buffer **không** lưu vào `state_dict`; `forward` tách `qkv` thành
   q, k, v, chia head, tính $$\mathrm{softmax}(QK^\top/\sqrt{d_{head}} + M)V$$ với $$M$$ là mask $$-\infty$$ ở tương lai, ghép
   head, qua `proj`. Không dùng `F.scaled_dot_product_attention`.
3. `MLP.forward` và `Block.forward` (pre-norm, hai đường residual).
4. `GPT.__init__` (weight tying `lm_head` với `tok_emb`, khởi tạo theo docstring), `num_params`, `forward` (trả logits và
   loss trung bình bỏ qua target `-1`; chuỗi dài hơn `block_size` thì `ValueError`), `generate` (cắt ngữ cảnh về
   `block_size` token cuối, greedy khi `temperature == 0`, top-k, chỉ dùng `generator` truyền vào).

Giữ nguyên tên các module con (`blocks`, `attn`, `mlp`, `ln1`, `ln2`, `ln_f`, `lm_head`, `qkv`, `proj`, `fc`): module 08
gắn hook theo tên này.

## Tiêu chí đạt

- `LayerNorm` khớp `F.layer_norm` cả khi phương sai rất nhỏ.
- `CausalSelfAttention` khớp `F.scaled_dot_product_attention(is_causal=True)` với cùng trọng số; mask là buffer không
  nằm trong `state_dict`.
- `Block` đúng pre-norm; đổi token ở vị trí 7 không làm đổi logits ở vị trí 0..6; chuỗi toàn một token cho logits khác
  nhau theo vị trí.
- Số tham số đúng công thức, `lm_head.weight is tok_emb.weight`; khởi tạo đúng độ lệch chuẩn (kể cả các lớp `proj`),
  loss ban đầu với target ngẫu nhiên xấp xỉ $$\ln V$$.
- Loss bỏ qua target `-1`; model học thuộc một chuỗi 16 token trong 150 bước.
- `generate`: greedy khớp vòng argmax tính tay, độ dài ngữ cảnh mỗi bước là `3, 4, ..., 8, 8`; top-k = 1 bằng greedy;
  cùng seed cùng kết quả; trả lại chế độ train/eval.
- Hook gắn vào `blocks[i].attn`, `blocks[i].mlp`, `ln_f` nhận output shape `(B, T, n_embd)`.

## Gợi ý

### Gợi ý 1

Viết attention theo shape: sau khi tách head, q, k, v có shape `(B, n_head, T, head_dim)`; score là `(B, n_head, T, T)`.
Một `view` đổi `(B, T, C)` thành `(B, T, n_head, head_dim)`, rồi đổi chỗ trục 1 và 2. Viết thẳng `view(B, n_head, T, ...)`
chạy được nhưng trộn dữ liệu của các token. Mask phải áp **trước** softmax (giống mục 6 module 04), cắt về `T × T` khi
chuỗi ngắn hơn `block_size`.

### Gợi ý 2

Trong `__init__` của `GPT`, gán `self.lm_head.weight = self.tok_emb.weight` rồi mới khởi tạo; `self.apply(fn)` gọi `fn`
trên mọi module con. Đếm tham số bằng `self.parameters()` tự loại trùng tensor dùng chung. `F.cross_entropy` có tham
số `ignore_index`. Ở `generate`, lấy logits của **vị trí cuối**; ngưỡng top-k là giá trị lớn thứ k, giá trị bằng ngưỡng
vẫn giữ.
