# Hướng làm: QLoRA Qwen2.5-7B trên GPU 12GB

Bài không có code lời giải đầy đủ: phần chạy phụ thuộc phần cứng của bạn, và `REPORT.md` là đánh giá của bạn. Dưới đây là
các quyết định cần cân nhắc, kết quả của một bản tham chiếu để bạn so, và rubric chấm.

## Hàm được chấm

- `lora_param_count`: mỗi lớp đích $$r(d_{in} + d_{out})$$, với `k_proj`, `v_proj` ra `num_key_value_heads × head_dim` (GQA).
  Qwen2.5-7B, r = 16, 7 lớp: 40 370 176; 0.5B: 8 798 208. Khớp PEFT.
- `weight_memory_gib`: tách tham số lớp tuyến tính trong các tầng (lượng tử hoá) khỏi phần còn lại (embedding, `lm_head`
  nếu không dùng chung, norm, bias). Qwen2.5-7B **không** dùng chung embedding với `lm_head` (`tie_word_embeddings` false):
  hai ma trận 152 064 × 3 584 ở bf16 là khoảng 2 GiB không bao giờ được lượng tử hoá bởi bitsandbytes.
- `bnb_4bit_config`: `load_in_4bit=True`, `bnb_4bit_quant_type="nf4"`, `bnb_4bit_use_double_quant=True`,
  `bnb_4bit_compute_dtype=torch.bfloat16`.
- `qlora_sft_kwargs`: `optim="paged_adamw_8bit"`, `gradient_checkpointing=True`, `bf16=True`, batch hiệu dụng = batch ×
  tích luỹ gradient (bản tham chiếu 4 × 4 = 16, bằng batch của 0.5B ở Intermediate 03).

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Dữ liệu train | 2 000 câu đầu của hoán vị seed 0 (cùng hoán vị với Intermediate 03) | 7B chậm hơn nhiều; đủ để thấy xu hướng, và đối chứng 0.5B dùng đúng 2 000 câu đó |
| Baseline "chỉ prompt" | chính 7B ở NF4 trước khi train | cùng trọng số, chỉ khác adapter; ghi rõ không phải bf16 |
| Batch | 4 × tích luỹ 4 | logits fp32 của 4 câu × 256 token × 152 nghìn từ vựng đã là vài trăm MB |
| Sinh khi đánh giá | greedy, batch 32, `max_new_tokens` 32, đọc strict | cùng cách với Intermediate 03 |

## Kết quả tham chiếu

<<A01_RESULTS>>

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 15 | Mọi test pass |
| Ước lượng và đo bộ nhớ | 20 | Bảng ước lượng (bf16, NF4) cho 0.5B, 3B, 7B; VRAM đo được ở ba pha (nạp, train, sinh); giải thích chỗ lệch giữa ước lượng và đo, giữa `max_memory_allocated` và `nvidia-smi` |
| So sánh công bằng | 20 | Cùng 2 000 câu train, cùng tập đánh giá, cùng prompt và cách đọc; nói rõ baseline là 7B NF4 |
| Số liệu | 20 | Bảng có JSON đúng định dạng, F1 cảm xúc (ghim và test), F1 chủ đề, thời gian train và đánh giá, VRAM; ít nhất 4 cấu hình |
| Diễn giải và khuyến nghị | 25 | Tách chênh lệch thật khỏi nhiễu của 150 câu; đặt thời gian và VRAM cạnh điểm F1 thu được; khuyến nghị có điều kiện và nêu điều chưa đo (độ trễ phục vụ, chi phí, quantize sau merge) |

Đạt từ 70 điểm. Báo cáo so 7B fine-tune với 0.5B fine-tune trên số câu train khác nhau, hoặc chỉ báo VRAM của
`nvidia-smi` mà không tách khỏi bộ nhớ của tiến trình khác, không quá 50 điểm.
