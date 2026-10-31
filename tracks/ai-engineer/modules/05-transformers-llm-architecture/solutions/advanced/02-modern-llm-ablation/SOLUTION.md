# Hướng làm: từ GPT-2 tới Llama, ablation và KV cache

Bài không có code lời giải cho thí nghiệm. Hai lớp được chấm ghép các mảnh của bài Basic 02; giá trị của bài nằm ở thiết kế
ablation có kiểm soát và ở việc tách tín hiệu khỏi nhiễu. Dưới đây là các quyết định, kết quả của bản tham chiếu và rubric.

## Hai lớp được chấm

- `ModernBlock`: `x = x + attn(norm1(x), cache)`, `x = x + mlp(norm2(x))`, trả thêm cache mới. Norm theo cờ (`RMSNorm` hoặc
  `nn.LayerNorm`), MLP theo cờ (`SwiGLU(d, ffn_hidden)` hoặc `fc`/`w2` không bias quanh GELU). `pos="learned"`: đặt
  `attn.cos.fill_(1)`, `attn.sin.fill_(0)` (quay góc 0) và thêm `pos_emb` ở `ModernGPT`.
- `ModernGPT.forward(idx, targets, caches)`: `past = caches[0][0].shape[2]` nếu có cache, ngược lại 0; `pos_emb` lấy vị trí
  `past .. past + T - 1`; mỗi tầng nhận `caches[i]` và trả cache mới; trả `(logits, loss, new_caches)`.
- `generate`: có cache thì prefill `idx` một lần, mỗi bước đưa đúng một token mới cùng cache; không cache thì forward lại
  `idx[:, -block_size:]`. Logits của bước kế lấy từ forward vừa chạy (đừng chạy hai lần).
- Khởi tạo như GPT-2 (ma trận $$\mathcal{N}(0, 0.02)$$, `wo` và `w2` thu nhỏ $$1/\sqrt{2L}$$), lm_head dùng chung `tok_emb`.

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Quy mô | 4 tầng, `n_embd` 256, 4 head, context 128, vocab 8 000; 3 000 bước batch 32; dữ liệu, tokenizer, đánh giá của bài Intermediate 01 | đúng ngân sách của LSTM module 04 và GPT mini bài Intermediate 01, mỗi lần chạy 2-3 phút |
| Bản đầy đủ | RMSNorm, RoPE base 10 000, SwiGLU 704, GQA 2 kv head, không bias, tie embedding | công thức Llama thu nhỏ; SwiGLU 704 ≈ $$\frac83 d$$ làm tròn bội 64 để tham số MLP gần bằng GELU $$4d$$ |
| Ablation | đổi **một** thứ mỗi lần từ bản đầy đủ; mọi siêu tham số khác giữ nguyên | đọc được đóng góp riêng của từng thứ |
| Độ nhiễu | mọi cấu hình chạy seed 0 và seed 1 (seed đổi khởi tạo và thứ tự batch) | chênh lệch nhỏ hơn độ lệch giữa hai seed của cùng cấu hình thì không kết luận |
| Đo KV cache | `ModernGPT` riêng với `block_size` 1 024, trọng số ngẫu nhiên (không ảnh hưởng thời gian); prompt 32 token, greedy 64/256/768 token, kiểm hai cách ra cùng token (ở 64 token trên CPU và GPU, ở 768 token trên CPU); CPU 4 luồng và GPU | tách lợi ích thuật toán khỏi chi phí khởi chạy kernel |

## Kết quả tham chiếu

PC RTX 3060 12GB, env `setup/gpu`, bf16 autocast, ngày 2026-11-01. bpc trên 664 568 ký tự validation, cửa sổ trượt stride 64.

| Cấu hình | Tham số | bpc seed 0 | bpc seed 1 | Trung bình | So với bản đầy đủ |
| --- | --- | --- | --- | --- | --- |
| GPT-2 (lớp `GPT` bài Basic 01) | 5 240 320 | 1.9072 | 1.9020 | 1.9046 | +0.029 |
| **Đầy đủ** (RMSNorm, RoPE, SwiGLU, GQA 4/2) | 4 999 424 | 1.8786 | 1.8733 | 1.8759 | 0 |
| position embedding học được thay RoPE | 5 032 192 | 1.9175 | 1.9143 | 1.9159 | +0.040 |
| LayerNorm thay RMSNorm | 5 001 728 | 1.8825 | 1.8769 | 1.8797 | +0.004 |
| GELU $$4d$$ thay SwiGLU | 4 933 888 | 1.8720 | 1.8661 | 1.8690 | −0.007 |
| MHA (4 kv head) | 5 261 568 | 1.8689 | 1.8689 | 1.8689 | −0.007 |
| MQA (1 kv head) | 4 868 352 | 1.8777 | 1.8759 | 1.8768 | +0.001 |

Hai seed của cùng cấu hình lệch nhau tới 0.006 bpc. Mỗi lần chạy 2.4-2.9 phút, dưới 0.8 GB VRAM.

Đọc kết quả:

- **Thật**: bản Llama tốt hơn GPT-2 0.029 bpc ở cả hai seed, và gần như toàn bộ đến từ **RoPE** (bỏ RoPE thì kém hơn cả GPT-2).
  Ở context 128, mã hoá vị trí tương đối giúp nhiều hơn mọi thứ khác.
- **Trong nhiễu**: RMSNorm so với LayerNorm (0.004), MQA so với GQA (0.001). Ở quy mô này chúng không đổi chất lượng; lợi ích của
  chúng là tốc độ và bộ nhớ (RMSNorm rẻ hơn, MQA cache nhỏ hơn 2 lần so với GQA 2).
- **Ngược kỳ vọng**: GELU nhỉnh hơn SwiGLU 0.007 ở cả hai seed, lớn hơn nhiễu một chút. Lợi ích của SwiGLU được báo cáo ở quy mô
  lớn hơn nhiều (Shazeer 2020, perplexity sau 65 000 bước model T5 base); một lần chạy 3 000 bước model 5 triệu tham số không
  bác bỏ được nó, chỉ cho thấy nó không phải nguồn lợi ở đây. MHA tốt hơn GQA 0.007 nhưng có thêm 262 144 tham số (wk, wv đầy đủ):
  GQA đổi một chút chất lượng lấy cache nhỏ hơn 2 lần.
- KV cache (`ModernGPT` block 1 024 trọng số ngẫu nhiên, prompt 32 token, greedy, hai cách ra cùng token; PC, float32): CPU 4 luồng
  sinh 64 / 256 / 768 token mất 0.21 / 0.76 / 2.41 s có cache so với 0.41 / 2.71 / 18.84 s không cache (tuyến tính so với gần bậc
  hai, chậm hơn 7.8 lần ở 768 token). RTX 3060: 0.43 / 1.66 / 5.07 s so với 0.47 / 1.73 / 5.32 s, gần như không khác, và chậm hơn
  CPU có cache: với model 5 triệu tham số, thời gian chủ yếu là dispatch phía host và launch kernel CUDA (GPU dùng chung lúc đo làm phồng thêm), không phải phép tính; CUDA Graphs (`torch.compile(mode="reduce-overhead")`) hoặc batching là cách khắc phục. Báo cáo tốt nói được điều
  này thay vì kết luận "cache không có tác dụng".

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 15 | 2 lớp pass mọi test |
| Thí nghiệm có kiểm soát | 25 | baseline GPT-2 và bản đầy đủ, ≥ 4 ablation đổi một thứ mỗi lần, cùng ngân sách, số tham số mỗi dòng |
| Độ nhiễu | 20 | ≥ 2 seed cho mọi cấu hình (hoặc cho baseline, bản đầy đủ và ít nhất 2 ablation), kết luận chỉ cho chênh lệch vượt nhiễu |
| KV cache | 20 | đo có và không cache, kiểm cùng token, giải thích kết quả theo phần cứng; bảng bộ nhớ cache cho model thật |
| Diễn giải | 20 | nói thành phần nào đáng giá ở quy mô này, thành phần nào để tiết kiệm bộ nhớ/tốc độ, giới hạn của quy mô nhỏ |

Đạt từ 70 điểm. Báo cáo kết luận từ chênh lệch một seed dưới mức nhiễu (ví dụ "LayerNorm tệ hơn RMSNorm") không quá 50 điểm.
