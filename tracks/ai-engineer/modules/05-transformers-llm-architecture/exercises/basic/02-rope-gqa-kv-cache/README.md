---
title: RoPE, RMSNorm, SwiGLU, grouped-query attention và KV cache
level: basic
services: []
files:
  - path: starter/modern.py
    note: 8 hàm/lớp TODO
  - path: tests/test_modern.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/05-transformers-llm-architecture/exercises/basic/02-rope-gqa-kv-cache -q
---

## Mục tiêu

Tự viết các mảnh làm Llama, Qwen, Mistral khác GPT-2: RMSNorm, rotary position embedding (RoPE), SwiGLU, grouped-query
attention (GQA) và KV cache cho sinh từng token. Làm xong bạn chứng minh được bằng test rằng RoPE chỉ phụ thuộc khoảng
cách giữa hai token, rằng decode có cache cho đúng kết quả của forward đầy đủ, và tính được KV cache của một model thật
chiếm bao nhiêu GB.

## Đề bài

**Phần cứng:** CPU · ~120 phút

Đọc mục 3 và 4 phần lý thuyết. Trong `starter/modern.py`, điền các chỗ `# TODO` theo docstring:

1. `RMSNorm.forward`: chia cho căn trung bình bình phương, nhân `weight`; không trừ trung bình, không bias.
2. `rope_cache(head_dim, max_len, base)`: bảng `cos`, `sin` shape `(max_len, head_dim)` với góc $$m\theta_i$$,
   $$\theta_i = \text{base}^{-2i/d}$$; cột $$i$$ và $$i + d/2$$ cùng góc. `rotate_half`, `apply_rope(x, cos, sin, start_pos)`
   quay cặp $$(x_i, x_{i+d/2})$$ một góc ứng với vị trí tuyệt đối `start_pos + t`.
3. `repeat_kv(x, n_rep)`: nhân bản kv head cho GQA theo đúng thứ tự (head truy vấn $$h$$ dùng kv head $$\lfloor h / n_{rep} \rfloor$$).
4. `SwiGLU.forward`.
5. `GQAttention`: buffer `cos`, `sin`; `forward(x, kv_cache)` chiếu q, k, v, quay RoPE theo vị trí tuyệt đối, nối với cache
   cũ, lưu cache **trước** khi `repeat_kv`, mask nhân quả **dịch theo số token đã có trong cache**, trả `(out, new_cache)`.
6. `kv_cache_bytes(n_layer, n_kv_head, head_dim, seq_len, batch, bytes_per_elem)`.

## Tiêu chí đạt

- `RMSNorm` đúng công thức, chỉ có `weight`.
- `rope_cache` đúng góc ở cả hai nửa; `apply_rope` quay cặp $$(i, i + d/2)$$ đúng chiều, đúng `start_pos`, giữ nguyên độ
  dài vector, và $$\langle R_m q, R_n k \rangle$$ chỉ phụ thuộc $$m - n$$.
- `repeat_kv` đúng thứ tự nhóm; `SwiGLU` đúng thứ tự `silu(w1 x) * w3 x`.
- `GQAttention` khớp một bản tham chiếu dùng `F.scaled_dot_product_attention`; `wk`, `wv` chỉ có `n_kv_head` head;
  nhân quả; cache lưu `n_kv_head` head.
- Decode từng token với cache (và prefill theo hai khúc) cho cùng output với forward cả chuỗi (`atol=1e-5`).
- `kv_cache_bytes(32, 8, 128, 8192)` bằng đúng 1 GiB (Llama 3 8B, bf16, một chuỗi 8 192 token).

## Gợi ý

### Gợi ý 1

RoPE chỉ là nhân từng phần tử: với cặp $$(a, b)$$ quay góc $$\varphi$$ ra $$(a\cos\varphi - b\sin\varphi,\ b\cos\varphi + a\sin\varphi)$$.
Nếu `cos`, `sin` có cùng góc ở cột $$i$$ và $$i + d/2$$ thì cả phép quay viết được thành một biểu thức với `rotate_half`.
Có hai quy ước ghép cặp trong thực tế (cặp liền kề $$(2i, 2i+1)$$ của paper gốc và cặp nửa đầu, nửa sau của Llama trên
Hugging Face); bài này dùng quy ước thứ hai, test phân biệt được hai cách.

### Gợi ý 2

Khi có cache với $$P$$ token cũ và $$T$$ token mới, score có shape `(B, H, T, P + T)`: token mới $$t$$ nhìn được cột
$$0 .. P + t$$. `torch.tril` có tham số `diagonal`. Vị trí dùng cho RoPE của token mới là $$P + t$$, và $$P$$ đọc được từ
shape của cache. `expand` rồi `reshape` cho đúng thứ tự `repeat_interleave`; `repeat` (lặp cả khối) thì sai thứ tự.
