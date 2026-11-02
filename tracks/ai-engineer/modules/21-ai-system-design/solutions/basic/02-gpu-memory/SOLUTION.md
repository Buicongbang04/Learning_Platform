# Lời giải: bộ nhớ GPU khi serve LLM

## Cách làm

- `shape_from_hf_config`: `num_key_value_heads` (thiếu thì bằng `num_attention_heads`), `head_dim` tường minh nếu có,
  không thì `hidden_size // num_attention_heads`.
- `weight_bytes` $$= N b / 8$$; `kv_bytes_per_token` $$= 2 L\, n_{kv}\, d_{head}\, \text{kv\_bits} / 8$$; `kv_cache_bytes`
  nhân thêm số token và số chuỗi.
- Hai hàm cuối: `free = vram - reserve - weights`, `free <= 0` trả 0, còn lại chia rồi làm tròn xuống.

## Đọc các con số

Từ config thật (Hugging Face, kiểm 2026-10-30):

| Model | $$L$$ | KV head / attention head | KV mỗi token (bf16) | Nếu là MHA | KV một chuỗi 32k | Trọng số bf16 / 4.5 bit |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen2.5-3B | 36 | 2 / 16 | 36 KiB | 288 KiB | 1.12 GiB | 5.75 / 1.62 GiB |
| Qwen2.5-7B | 28 | 4 / 28 | 56 KiB | 392 KiB | 1.75 GiB | 14.19 / 3.99 GiB |
| Qwen2.5-72B | 80 | 8 / 64 | 320 KiB | 2.5 MiB | 10.00 GiB | 135.43 / 38.09 GiB |

Số chuỗi Qwen2.5-7B chạy cùng lúc (chừa 1.5 GiB trên 12 GiB, 2 GiB trên 24 GiB):

| Context mỗi chuỗi | 12 GiB, 4.5 bit | 24 GiB, 4.5 bit | 24 GiB, bf16 |
| --- | --- | --- | --- |
| 2 048 | 59 | 164 | 71 |
| 4 096 | 29 | 82 | 35 |
| 8 192 | 14 | 41 | 17 |
| 32 768 | 3 | 10 | 4 |

Ba bài học:

1. **GQA giảm KV cache 7–8 lần.** Qwen2.5-7B với MHA sẽ cần 392 KiB mỗi token: trên 12 GiB chỉ còn 2 chuỗi 8k thay
   vì 14. Đây là lý do mọi model mở gần đây dùng GQA (module 05).
2. **Context dài ăn chỗ của concurrency**, tuyến tính: chuỗi 32k chiếm chỗ của 16 chuỗi 2k. Hứa "hỗ trợ 32k context"
   cho mọi người dùng là hứa số GPU gấp nhiều lần. vLLM cấp KV theo block khi token thật sự sinh ra (PagedAttention),
   nên số chuỗi thực tế phụ thuộc độ dài **thật**, không phải độ dài tối đa; con số ở đây là trường hợp xấu nhất.
3. **Quantize trọng số giải phóng chỗ cho KV**: trên 24 GiB, 4.5 bit cho 41 chuỗi 8k, bf16 cho 17. Quantize KV
   cache xuống int8 nhân đôi số chuỗi lần nữa, đổi lại một chút chất lượng (module 10).

Tệp GGUF `qwen2.5:3b` (Q4_K_M) của Ollama nặng 1 929 912 432 byte cho 3.086 tỉ tham số, tức trung bình 5.0 bit mỗi
tham số chứ không phải 4: Q4_K_M giữ một số tensor ở độ chính xác cao hơn và còn lưu scale cho từng nhóm.

## Bẫy thường gặp

- Dùng `num_attention_heads` cho KV (bỏ qua GQA): KV lớn gấp 7 lần ở Qwen2.5-7B, ước lượng thừa GPU.
- Quên số 2 (chỉ tính K) hoặc quên nhân số layer.
- Suy `head_dim` từ `hidden_size` khi config có `head_dim` riêng (Mistral-Nemo: 160 thay vì 128).
- Không trừ phần dự phòng: CUDA context, activation lúc prefill, buffer của framework thường chiếm 1–2 GiB. vLLM
  mặc định chỉ dùng 92% VRAM (`--gpu-memory-utilization 0.92`, docs engine args kiểm 2026-10-30).
- Làm tròn lên số chuỗi, hoặc trả số âm khi trọng số không vừa.
