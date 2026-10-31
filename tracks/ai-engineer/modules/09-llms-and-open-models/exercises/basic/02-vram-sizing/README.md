---
title: Ước lượng VRAM của LLM từ config.json
level: basic
services: []
files:
  - path: starter/sizing.py
    note: 6 hàm TODO
  - path: tests/test_sizing.py
    note: Không sửa
  - path: tests/fixtures/
    note: config.json thật của 5 model
run:
  - uv run pytest tracks/ai-engineer/modules/09-llms-and-open-models/exercises/basic/02-vram-sizing -q
---

## Mục tiêu

Trả lời trong vài giây câu hỏi đầu tiên khi chọn model mở: "chạy được trên máy này không, với context bao
nhiêu?". Bạn đếm tham số **chính xác tới từng số** từ `config.json`, tính bộ nhớ trọng số theo kiểu dữ liệu, KV
cache theo context và batch, rồi tìm context lớn nhất vừa một ngân sách VRAM.

## Đề bài

**Phần cứng:** CPU · ~40 phút

`tests/fixtures/` có `config.json` thật tải từ Hugging Face của Qwen2.5 0.5B/3B/7B Instruct, Phi-3 mini 4k
Instruct và Mistral 7B Instruct v0.3. Trong `starter/sizing.py` (docstring đầu tệp mô tả kiến trúc), viết:

1. `head_dim(config)` và `count_params(config)`: đếm từng ma trận và bias của một decoder kiểu Llama/Qwen2 (GQA,
   SwiGLU, RMSNorm, embedding có thể dùng chung với `lm_head`).
2. `weight_bytes(config, dtype)` dùng bảng `BYTES_PER_PARAM` có sẵn.
3. `kv_cache_bytes(config, seq_len, batch, kv_dtype)`: công thức ở mục 7 phần lý thuyết.
4. `estimate_memory(config, dtype, seq_len, batch, kv_dtype, overhead)`: trọng số, KV cache, phần dư
   (`overhead` × tổng hai phần trên), tổng.
5. `max_context(config, dtype, budget_bytes, ...)`: context lớn nhất vừa ngân sách, không vượt
   `max_position_embeddings`, trả 0 khi trọng số đã không vừa.

## Tiêu chí đạt

- `count_params` khớp **chính xác** số tham số thật của cả 5 model (494 032 768 cho Qwen2.5-0.5B; 3 085 938 688 và
  7 615 616 512 cho Qwen2.5 3B, 7B như GGUF của Ollama báo) và cấu hình tí hon tính tay.
- `weight_bytes` bf16 của Qwen2.5-0.5B khớp kích thước `model.safetensors` (988 097 824 byte) trừ phần header.
- KV cache: Qwen2.5-0.5B ở 32 768 token là đúng 384 MiB; Phi-3 mini (MHA, 32 KV head) ở 4 096 token là 1.5 GiB;
  Mistral 7B ở 32 768 token là 4 GiB.
- `max_context` trả số lớn nhất còn vừa (số kế tiếp đã vượt), đúng biên 0 và trần context.

## Gợi ý

### Gợi ý 1

Viết riêng từng khối của một tầng: q (có bias nếu có), k và v (cùng cỡ, $$h_{kv} \cdot d_{head}$$ cột), o (không
bias), MLP 3 ma trận, 2 norm. Nhân với số tầng, cộng embedding (một hay hai lần tuỳ `tie_word_embeddings`) và norm
cuối. Sai một thành phần là lệch khỏi số thật: thiếu bias của Qwen2 lệch 27 648 tham số với bản 0.5B, quên
`tie_word_embeddings` lệch 136 triệu.

### Gợi ý 2

KV cache lưu **K và V** (hệ số 2) cho **mỗi tầng**, mỗi **KV head** (không phải mỗi query head: đó là lợi ích của
GQA), mỗi vị trí, mỗi chuỗi trong batch. `estimate_memory` tuyến tính theo `seq_len`, nên `max_context` giải được
bằng một phép chia: phần ngân sách còn lại sau trọng số (đã nhân `1 + overhead`) chia cho chi phí một token (cũng
nhân `1 + overhead`), lấy phần nguyên.
