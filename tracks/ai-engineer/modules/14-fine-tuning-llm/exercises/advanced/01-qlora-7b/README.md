---
title: QLoRA Qwen2.5-7B trên GPU 12GB, so với model nhỏ và với prompt
level: advanced
services: []
files:
  - path: starter/qlora.ipynb
    note: 5 hàm TODO, 4 hàm dán từ Intermediate 03
  - path: starter/REPORT.md
    note: Báo cáo
  - path: tests/test_qlora.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py uit-vsfc
  - uv run jupyter lab tracks/ai-engineer/modules/14-fine-tuning-llm/exercises/advanced/01-qlora-7b/starter/qlora.ipynb
  - uv run pytest tracks/ai-engineer/modules/14-fine-tuning-llm/exercises/advanced/01-qlora-7b -q
---

## Mục tiêu

Fine-tune một model 7B trên GPU tiêu dùng bằng QLoRA, và trả lời bằng số câu hỏi mà mọi trưởng nhóm sẽ hỏi: model lớn
fine-tune có đáng gấp nhiều lần VRAM, thời gian và chi phí phục vụ so với model nhỏ fine-tune, hay so với chính model lớn
chỉ dùng prompt? Bài toán là bài trích xuất phản hồi UIT-VSFC ra JSON của Intermediate 03.

## Đề bài

**Phần cứng:** GPU 12GB (PC) · ~180 phút

Chạy notebook bằng kernel `ai-gpu` (xem `setup/gpu/README.md`). Thời gian trên là thời gian làm bài. Thời gian máy của
bản tham chiếu trên PC của track (RTX 3060 12GB, GPU dùng chung với tiến trình khác lúc đo): nạp 7B ở 4 bit vài giây khi đã
có trong cache, đánh giá trước fine-tune khoảng 8 phút, QLoRA 1 epoch trên 2 000 câu khoảng 15 phút, đánh giá sau khoảng
10 phút, VRAM đỉnh dưới 7 GiB. Lần đầu tải Qwen2.5-7B-Instruct khoảng 15 GB.

**Laptop 4GB**: chạy cùng notebook với `MODEL = "Qwen/Qwen2.5-3B-Instruct"`, `BATCH = 2`, `GRAD_ACCUM = 8` (trọng số NF4
ước lượng dưới 2 GiB; cấu hình này chưa được đo trên laptop), hoặc với 0.5B; báo cáo ghi rõ model đã dùng. Đọc mục 3, 4 lý
thuyết và mục 3, 7 module 10. Làm bài Intermediate 03 trước.

1. Trong `starter/qlora.ipynb`, viết `lora_param_count`, `weight_memory_gib`, `bnb_4bit_config`, `qlora_sft_kwargs`,
   `load_4bit` theo đặc tả trong notebook, và **dán** bốn hàm của bài Intermediate 03.
2. Chạy cell ước lượng cho 0.5B, 3B, 7B **trước** khi train; ghi lại dự đoán VRAM của bạn.
3. Chạy các cell `explore`: nạp 4 bit, đo trước fine-tune, QLoRA 1 epoch trên 2 000 câu, đo sau. Ghi VRAM đỉnh (cấp phát
   và reserved), thời gian từng pha.
4. Chạy thêm đối chứng: 0.5B LoRA bf16 trên **cùng** 2 000 câu (dùng lại code của Intermediate 03 với `SFT_N = 2000`).
5. Viết `starter/REPORT.md` theo khung có sẵn, rồi làm phần trắc nghiệm của bài trong app.

**Một `REPORT.md` tốt**:

- Ước lượng trước, đo sau, giải thích chỗ lệch (activation, logits fp32 với từ vựng 152 nghìn, bộ nhớ CUDA reserved).
- So **công bằng**: cùng dữ liệu train, cùng tập đánh giá, cùng prompt, cùng cách đọc output (strict). Nói rõ "7B chỉ
  prompt" của bạn là bản NF4 (không phải bf16).
- Đọc bảng như một kỹ sư: chênh lệch F1 nào lớn hơn nhiễu (150 câu ghim: mỗi câu cỡ 0.7 điểm phần trăm), chênh lệch nào không;
  thời gian và VRAM đổi lấy bao nhiêu điểm F1.
- Khuyến nghị có điều kiện: khi nào 7B QLoRA đáng (nhãn ít, tác vụ cần hiểu ngữ cảnh dài, nhiều nhãn hiếm), khi nào 0.5B
  là đủ, và cái giá phục vụ (VRAM, token/giây) mà bảng chưa đo.

## Tiêu chí đạt

- `lora_param_count` khớp số PEFT đếm cho Qwen2.5-0.5B và 7B (mọi lớp và chỉ `q_proj`, `v_proj`), tôn trọng `head_dim`.
- `weight_memory_gib` ở 16 bit cho đúng tổng tham số × 2 byte của cả hai model (dùng chung embedding hay không).
- `bnb_4bit_config` là NF4, double quant, compute bf16; `qlora_sft_kwargs` có optimizer phân trang 8 bit, gradient
  checkpointing, bf16 và các tham số khác theo đặc tả.
- Bốn hàm dán từ Intermediate 03 qua kiểm tra nhanh.
- `REPORT.md` không còn TODO, ít nhất 400 từ, có bảng.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Đếm từ shape: với GQA, `k_proj` và `v_proj` ra `num_key_value_heads × head_dim`, không phải `hidden_size`. Qwen2 có bias
ở q, k, v; norm có một vector `hidden_size` cho mỗi lần dùng. Kiểm hàm của bạn bằng tổng `numel` của Qwen2.5-0.5B
(494 032 768) trước khi tin nó cho 7B.

### Gợi ý 2

Notebook bật gradient checkpointing và `enable_input_require_grads()` bằng tay. Hàm tiện ích
`prepare_model_for_kbit_training` của PEFT cũng làm việc đó và hơn thế: đọc mã nguồn của nó xem nó làm gì với các tham số
**không** lượng tử hoá, rồi đo VRAM ngay sau khi gọi nó trên model 7B trước khi quyết định dùng. Đo VRAM bằng `torch.cuda.max_memory_allocated` sau
`reset_peak_memory_stats` ở đầu mỗi pha, và so với con số `nvidia-smi` báo cùng lúc.
