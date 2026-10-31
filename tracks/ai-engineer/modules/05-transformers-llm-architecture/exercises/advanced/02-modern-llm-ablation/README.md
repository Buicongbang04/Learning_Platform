---
title: Từ GPT-2 tới Llama, ablation từng thành phần và KV cache
level: advanced
services: []
files:
  - path: starter/ablation.ipynb
    note: 2 lớp chấm, thí nghiệm tự thiết kế
  - path: starter/REPORT.md
    note: Báo cáo
  - path: tests/test_ablation.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py wikipedia-vi
  - uv sync --project setup/gpu
  - uv run jupyter lab tracks/ai-engineer/modules/05-transformers-llm-architecture/exercises/advanced/02-modern-llm-ablation/starter/ablation.ipynb
  - uv run pytest tracks/ai-engineer/modules/05-transformers-llm-architecture/exercises/advanced/02-modern-llm-ablation -q
---

## Mục tiêu

Ghép RMSNorm, RoPE, SwiGLU, GQA và KV cache của bài Basic 02 thành một `ModernGPT` bật tắt được từng thành phần, rồi làm một
nghiên cứu ablation có kiểm soát như một kỹ sư nghiên cứu: mỗi thay đổi từ GPT-2 sang Llama đóng góp bao nhiêu bpc ở quy mô nhỏ,
và chênh lệch nào **lớn hơn độ nhiễu** giữa hai seed. Phần thứ hai đo KV cache: nhanh hơn bao nhiêu khi sinh, tốn bao nhiêu bộ
nhớ ở model thật.

## Đề bài

**Phần cứng:** GPU 4GB · ~420 phút

Thời gian trên là thời gian làm bài. Thời gian máy của bản tham chiếu, đo trên PC RTX 3060 12GB (GPU dùng chung): mỗi cấu hình
3 000 bước batch 32 × 128 mất 2.4-2.9 phút, dưới 0.8 GB VRAM (vừa GPU laptop 4GB, chậm hơn vài lần); 7 cấu hình × 2 seed
khoảng 40 phút. **Không có GPU:** model `n_embd` 128, 1 000 bước mỗi cấu hình (khoảng 5 phút mỗi cấu hình trên CPU 4 luồng),
chênh lệch nhỏ hơn và nhiễu hơn, nên càng cần hai seed.

1. Trong `starter/ablation.ipynb`, viết `ModernConfig` và `ModernGPT` theo đặc tả trong notebook (cờ `pos`, `norm`, `mlp`,
   `n_kv_head`; `forward` nhận và trả KV cache; `generate` có và không cache).
2. Dữ liệu, tokenizer, đánh giá như bài Intermediate 01. Baseline là `GPT` bài Basic 01 (GPT-2). Bản đầy đủ là `ModernGPT` mặc
   định (4 tầng, `n_embd` 256, 4 head, 2 kv head, SwiGLU 704). Ablation: đổi một thứ mỗi lần (`pos="learned"`, `norm="layer"`,
   `mlp="gelu"`, `n_kv_head` 4 và 1), cùng số bước, batch, learning rate. Chạy mọi cấu hình với ít nhất hai seed.
3. KV cache: dựng riêng một `ModernGPT` với `block_size` ≥ 1 024 (trọng số ngẫu nhiên cũng được, thời gian không phụ thuộc
   trọng số) rồi đo thời gian sinh 64, 256, 768 token sau prompt 32 token, có và không cache, kiểm cùng token, trên CPU và GPU
   nếu có. Model đã train có `block_size` 128: có cache thì vượt bảng cos/sin của RoPE, không cache thì `generate` cắt còn 128
   token cuối nên chi phí thành tuyến tính, cả hai đều không đo được điều cần đo. Thêm bảng bộ nhớ cache của vài model thật bằng
   `kv_cache_bytes` (bài Basic 02).
4. Viết `starter/REPORT.md`, rồi làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `ModernConfig` đúng trường và mặc định; số tham số đổi đúng theo từng cờ; weight tying; nhân quả với mọi tổ hợp cờ.
- Decode từng token với cache khớp forward cả chuỗi (kể cả `pos="learned"`); `generate` có cache prefill một lần rồi đưa một
  token mỗi bước, cho cùng kết quả với không cache (greedy và sampling cùng seed).
- `REPORT.md` không còn TODO, ít nhất 500 từ, có bảng ablation, dùng bpc, nói về seed.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Số token đã có trong cache đọc được từ shape của cache tầng đầu. Vị trí đó dùng cho `pos_emb` ở `ModernGPT` và cho RoPE bên trong
`GQAttention` (bài Basic 02 đã lo). Muốn tắt RoPE mà không sửa `GQAttention`: phép quay góc 0 là phép đồng nhất.

### Gợi ý 2

Chênh lệch bpc giữa hai seed của **cùng** cấu hình là thước đo độ nhiễu; một thay đổi kiến trúc nhỏ hơn mức đó thì chưa kết luận
được ở ngân sách này. Đo thời gian sinh trên GPU nhớ `torch.cuda.synchronize()` trước khi bấm giờ và chạy một lần khởi động.
