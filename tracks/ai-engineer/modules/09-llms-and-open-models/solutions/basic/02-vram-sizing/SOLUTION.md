# Lời giải: ước lượng VRAM từ config.json

## Cách làm

**`count_params`** cộng từng khối của một tầng, với $$d$$ = `hidden_size`, $$h$$, $$h_{kv}$$ số head và KV head,
$$d_h$$ = `head_dim`, $$d_{ff}$$ = `intermediate_size`:

$$
\underbrace{d\,h d_h + b\,h d_h}_{q} + \underbrace{2\,(d\,h_{kv} d_h + b\,h_{kv} d_h)}_{k,\ v} + \underbrace{h d_h\, d}_{o} + \underbrace{3\,d\,d_{ff}}_{\text{SwiGLU}} + \underbrace{2d}_{\text{2 RMSNorm}}
$$

với $$b = 1$$ khi có bias q, k, v. Nhân với $$L$$ tầng, cộng embedding $$V d$$ (nhân 2 nếu `lm_head` không dùng
chung) và norm cuối $$d$$. Cờ bias: `config.get("attention_bias")`, `None` thì suy ra từ `model_type == "qwen2"`
(config Qwen2 không có khoá này nhưng code `Qwen2Attention` luôn bật bias ở q, k, v).

**`kv_cache_bytes`** là $$2 \cdot L \cdot h_{kv} \cdot d_h \cdot n_{ctx} \cdot B \cdot \text{byte}$$.

**`max_context`** giải bất phương trình tuyến tính
$$(W + n \cdot c)(1 + o) \le M$$ thành $$n = \lfloor (M - W(1+o)) / (c(1+o)) \rfloor$$, với $$c$$ là byte KV cache
của một token, rồi kẹp bởi `max_position_embeddings`.

## Con số đáng nhớ

| Model | Tham số | Trọng số bf16 | Q4_K_M (~5 bit) | KV cache fp16 / 4 096 token |
| --- | --- | --- | --- | --- |
| Qwen2.5-0.5B | 494 032 768 | 0.92 GiB | 0.29 GiB | 48 MiB |
| Qwen2.5-3B | 3 085 938 688 | 5.75 GiB | 1.80 GiB | 144 MiB |
| Qwen2.5-7B | 7 615 616 512 | 14.2 GiB | 4.43 GiB | 224 MiB |
| Phi-3 mini 4k (MHA) | 3 821 079 552 | 7.12 GiB | 2.22 GiB | 1.5 GiB |
| Mistral 7B v0.3 | 7 248 023 552 | 13.5 GiB | 4.22 GiB | 512 MiB |

- **GQA là chuyện tiền bạc**: Phi-3 mini có 32 KV head (MHA), Qwen2.5-3B chỉ 2. Cùng cỡ ~3-4B nhưng KV cache của
  Phi-3 ở 4 096 token lớn gấp hơn 10 lần (1.5 GiB so với 144 MiB) và gần bằng chính trọng số Q4 của nó.
- **Qwen2.5-7B Q4 không vừa GPU 4 GB**: chỉ riêng trọng số đã 4.43 GiB. Ollama vẫn chạy được bằng cách để một số
  tầng trên CPU, nhưng tốc độ sinh giảm mạnh (đo ở mục 6 lý thuyết).
- **Ước lượng so với đo thật**: công thức cho Qwen2.5-3B Q4_K_M, 4 096 token, overhead 0.2 là 2.32 GiB; `/api/ps`
  của Ollama báo model nạp chiếm 2.65 GB (2.46 GiB). Phần lệch là buffer tính toán (compute graph) của llama.cpp,
  không tỉ lệ với trọng số. Hệ số 0.2 là quy tắc ngón tay cái, đủ để quyết định "vừa hay không", không đủ để xếp
  sát 100% VRAM.
- Một tham số thì trọng số bf16 bằng 2 byte, nên `weight_bytes` của bản 0.5B (988 065 536) chỉ kém tệp
  `model.safetensors` 32 288 byte: đó là header JSON mô tả tên, shape, dtype của từng tensor.
