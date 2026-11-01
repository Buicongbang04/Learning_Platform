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

PC của track (RTX 3060 12GB, kernel `ai-gpu`), GPU dùng chung: Ollama của một module khác giữ khoảng 2.4 GB và một tiến
trình khác khoảng 1 GB suốt lúc đo, nên thời gian chỉ để tham khảo. LoRA r = 16, `lora_alpha` 32, mọi lớp tuyến tính, lr 2e-4
cosine, 1 epoch, batch hiệu dụng 16, cùng 2 000 câu train.

| Cấu hình | Ghim: F1 cảm xúc | Ghim: F1 chủ đề | Test: F1 cảm xúc | Test: F1 chủ đề | JSON strict (test) | Train | Đánh giá (150 + 3 166 câu) | VRAM đỉnh |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 7B NF4, chỉ prompt | 0.783 | 0.657 | 0.672 | 0.697 | 1.000 | | 455 giây | 6.32 GiB (sinh, batch 32) |
| 7B QLoRA, 2 000 câu | 0.806 | 0.745 | 0.827 | 0.794 | 1.000 | 125 bước, 919 giây | 573 giây | 5.93 GiB train, 6.62 GiB sinh |
| 0.5B LoRA bf16, cùng 2 000 câu | 0.640 | 0.751 | 0.732 | 0.754 | 1.000 | 125 bước, 105 giây | 86 giây | 1.64 GiB train |
| 0.5B LoRA bf16, 8 000 câu (Intermediate 03) | 0.805 | 0.777 | 0.814 | 0.805 | 1.000 | 500 bước, 300 giây | 49 giây | 1.71 GiB train |
| `qwen2.5:3b` chỉ prompt (module 11) | 0.804 (zero-shot), 0.852 (JSON Schema) | | | | | | | |

Bộ nhớ: nạp 7B ở NF4 + double quant chiếm **5.17 GiB** (`memory_allocated`), khớp đúng ước lượng `weight_memory_gib(config,
4.127)` = 5.17 GiB; trong đó 2.03 GiB là embedding và `lm_head` bf16 không bị lượng tử hoá. Ước lượng bf16 là 14.19 GiB, không
vừa GPU 12GB. Bản ước lượng cho 3B: 5.75 GiB bf16, 1.91 GiB NF4; cho 0.5B: 0.92 và 0.43 GiB.

Một lần chạy thử với `prepare_model_for_kbit_training` hết bộ nhớ ngay ở bước chuẩn bị (cố cấp phát thêm 2.03 GiB: hàm này
đổi embedding và `lm_head` sang fp32). Bật gradient checkpointing và `enable_input_require_grads()` bằng tay thì train vừa
5.93 GiB; TRL tự đưa tham số LoRA về bf16 khi model đã lượng tử hoá.

Đọc bảng:

- **QLoRA 7B đáng giá khi dữ liệu ít**: cùng 2 000 câu, 7B vượt 0.5B rõ ở F1 cảm xúc (0.827 so với 0.732 trên test, 0.806 so
  với 0.640 trên ghim). Nó đạt mức của 0.5B train trên **gấp 4 lần** dữ liệu. Ở F1 chủ đề thì hai model ngang nhau.
- **Fine-tune vẫn đáng ngay cả với 7B**: so với chính nó chỉ dùng prompt, F1 cảm xúc trên test tăng 0.67 lên 0.83, chủ đề 0.70
  lên 0.79. Trên 150 câu ghim, mức tăng cảm xúc (0.78 lên 0.81) nằm trong nhiễu.
- **Cái giá**: train chậm hơn 0.5B gần 9 lần (919 so với 105 giây cho cùng 125 bước), đánh giá chậm hơn khoảng 7 lần, VRAM
  cỡ 6 GiB so với dưới 2 GiB. Phục vụ 7B NF4 cần chỗ cho 5.2 GiB trọng số cộng KV cache (sinh batch 32 lúc đánh giá: 6.62 GiB);
  0.5B chạy được cả trên CPU (notebook Intermediate 03 chạy hết trên CPU). Với bài này, có 8 000 câu nhãn thì 0.5B là lựa chọn hợp lý hơn; chỉ có vài trăm tới hai nghìn câu thì 7B QLoRA đáng.
- Chưa đo: độ trễ phục vụ theo request, quantize sau khi merge (merge vào bản bf16 rồi GGUF/AWQ), và nhiều seed.

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
