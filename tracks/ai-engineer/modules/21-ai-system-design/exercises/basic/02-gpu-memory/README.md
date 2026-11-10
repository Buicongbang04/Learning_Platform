---
title: Bộ nhớ GPU khi serve LLM - trọng số và KV cache
level: basic
services: []
files:
  - path: starter/memory.py
    note: 6 hàm TODO
  - path: tests/test_memory.py
    note: Không sửa
  - path: tests/fixtures/qwen2.5-7b-instruct.json
    note: config.json thật (rút gọn); cùng thư mục có Qwen2.5 3B/72B và Mistral-Nemo
run:
  - uv run pytest tracks/ai-engineer/modules/21-ai-system-design/exercises/basic/02-gpu-memory -q
---

## Mục tiêu

Trả lời được câu "model này chạy trên GPU kia được không, phục vụ bao nhiêu người cùng lúc" từ `config.json` và một
phép nhân, trước khi thuê GPU. Làm xong bạn biết vì sao KV cache, không phải trọng số, thường là thứ giới hạn số
request đồng thời, và vì sao GQA quan trọng với chi phí serve.

## Đề bài

**Phần cứng:** CPU · ~45 phút

`starter/memory.py` có dataclass `ModelShape(n_params, n_layers, n_kv_heads, head_dim)`. Chỉ dùng thư viện chuẩn.
Định nghĩa theo mục 4 lý thuyết. Viết:

1. `shape_from_hf_config(config, n_params) -> ModelShape`: đọc dict `config.json` kiểu Hugging Face. `n_layers` là
   `num_hidden_layers`. `n_kv_heads` là `num_key_value_heads`; nếu không có khoá này thì model dùng multi-head
   attention đầy đủ, lấy `num_attention_heads`. `head_dim` lấy khoá `head_dim` nếu có (một số model như Mistral-Nemo
   có `head_dim` khác `hidden_size / num_attention_heads`), không thì `hidden_size // num_attention_heads`.
2. `weight_bytes(n_params, bits_per_weight) -> float`: $$N \cdot b / 8$$. `bits_per_weight` có thể lẻ (Q4_K_M khoảng
   4.85). `ValueError` nếu `bits_per_weight <= 0` hoặc `n_params < 0`.
3. `kv_bytes_per_token(shape, kv_bits=16) -> int`: byte KV cache cho một token,
   $$2 \cdot L \cdot n_{kv} \cdot d_{head} \cdot \frac{\text{kv\_bits}}{8}$$ (số 2 là K và V).
4. `kv_cache_bytes(shape, context_tokens, batch=1, kv_bits=16) -> int`: KV cache cho `batch` chuỗi dài
   `context_tokens`. `ValueError` nếu số âm.
5. `max_concurrent_sequences(vram_bytes, shape, weight_bits, context_tokens, kv_bits=16, reserve_bytes=0) -> int`:
   bộ nhớ cho KV là `vram - reserve - trọng số`; trả số chuỗi tối đa (làm tròn xuống) mà mỗi chuỗi giữ đủ KV cho
   `context_tokens` token; 0 nếu trọng số không vừa. `reserve_bytes` là phần dành cho activation, CUDA context, phân
   mảnh. `ValueError` nếu `context_tokens < 1`.
6. `max_context_tokens(vram_bytes, shape, weight_bits, batch=1, kv_bits=16, reserve_bytes=0) -> int`: context dài nhất
   mỗi chuỗi khi chạy `batch` chuỗi cùng lúc; 0 nếu không vừa. `ValueError` nếu `batch < 1`. Hàm chỉ tính giới hạn bộ
   nhớ; context tối đa model hỗ trợ (`max_position_embeddings`) là giới hạn riêng.

`tests/fixtures/` có `config.json` thật (rút gọn) tải từ Hugging Face ngày 2026-10-30. Số tham số trong test lấy từ
`total_size` của `model.safetensors.index.json` (byte bf16) chia 2.

## Tiêu chí đạt

- Đọc đúng ba config Qwen2.5 (GQA), Mistral-Nemo (`head_dim` tường minh) và một config không có `num_key_value_heads`.
- KV cache mỗi token: Qwen2.5-3B 36 864 byte, 7B 57 344, 72B 327 680; KV int8 bằng một nửa.
- Qwen2.5-7B trọng số 4.5 bit trên 12 GiB, chừa 1.5 GiB: 14 chuỗi 8 192 token, hoặc một chuỗi 121 904 token; bf16 không vừa (0).
- Mọi hàm trả đúng kiểu (`int` cho số chuỗi, số token) và ném `ValueError` với đầu vào sai như trên.

## Gợi ý

### Gợi ý 1

`config.get("num_key_value_heads") or config["num_attention_heads"]` xử lý cả trường hợp thiếu khoá. Đừng suy
`head_dim` từ `hidden_size` khi config đã ghi sẵn: test Mistral-Nemo bắt đúng lỗi này (ra 160 thay vì 128).

### Gợi ý 2

Hai hàm cuối cùng một khung: `free = vram - reserve - weight_bytes(...)`; nếu `free <= 0` trả 0; còn lại chia cho
dung lượng một đơn vị (một chuỗi đủ context, hoặc một token nhân `batch`) rồi làm tròn **xuống**: 14.9 chuỗi nghĩa là
chuỗi thứ 15 không có chỗ.
