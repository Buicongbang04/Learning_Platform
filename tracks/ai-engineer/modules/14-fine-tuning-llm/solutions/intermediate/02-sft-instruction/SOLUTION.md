# Lời giải: vòng SFT tự viết với LoRA cho Qwen2.5-0.5B

## Cách làm

- **`token_budget_batches`**: `sorted(range(n), key=lengths.__getitem__)` (sort ổn định), gom tham lam khi
  `max(độ dài) × (số mẫu + 1)` vẫn không vượt ngân sách, rồi hoán vị **thứ tự batch** bằng `default_rng(seed)`. Không trộn
  thứ tự thì model thấy mọi mẫu ngắn trước, mọi mẫu dài sau: loss vẽ ra đi theo độ dài, và learning rate cao nhất (đầu
  cosine) chỉ rơi vào một kiểu mẫu.
- **`heldout_nll`**: `model.eval()`, `torch.no_grad()`, logits dịch một vị trí ở fp32, `cross_entropy(..., reduction="sum")`
  trên vị trí có label, cộng dồn tổng và số token, chia một lần ở cuối. Trung bình các loss batch sai khi các batch có số token
  khác nhau (luôn đúng với batch theo ngân sách token).
- **`normalize_answer`** bỏ dấu câu và `_`, **`is_short_answer`** chọn câu mà đáp án ngắn có mặt trong câu hỏi,
  **`exact_match`** so sau chuẩn hoá. Đây là một thước đo hẹp: đáp án đúng nhưng viết khác (thêm "Đáp án là") bị tính sai,
  và vài câu "đáp án nằm trong câu hỏi" không thật sự là trắc nghiệm (một mẫu có đáp án chỉ là chữ "Và"). Nó vẫn có ích
  vì kiểm được bằng code và giống nhau giữa các lần chạy.
- **Vòng train**: `gradient_checkpointing_enable()` cùng `enable_input_require_grads()` (bắt buộc khi mọi tham số gốc đóng
  băng, nếu không checkpointing không có gì để tính gradient qua), `get_peft_model` với `target_modules="all-linear"`,
  AdamW chỉ trên tham số LoRA, warmup 3% rồi cosine, clip gradient 1.0, 1 epoch.

## Kết quả (PC của track, RTX 3060 12GB, kernel `ai-gpu`, khoảng 12 phút cả notebook)

Dữ liệu: 4 000 mẫu train (1 139 057 token, trong đó 483 297 token có label, 42%), 300 mẫu validation cho loss (36 568 token
có label), 200 câu trắc nghiệm đáp án ngắn (trong 287 câu như vậy của 3 689 câu validation). Ngân sách 1 024 token mỗi batch:
1 297 bước, 600 giây, VRAM đỉnh 2.83 GiB. Tỉ lệ token thật: **0.999** với batch theo ngân sách token, **0.635** với batch
cố định 8 mẫu theo thứ tự gốc.

| Model | Val loss | Val perplexity | Trắc nghiệm EM | Có chứa đáp án | Độ dài trả lời TB (ký tự) |
| --- | --- | --- | --- | --- | --- |
| 0.5B gốc | 1.796 | 6.02 | 0.175 | 0.300 | 54.4 |
| 0.5B + SFT LoRA (4 000 mẫu, 1 epoch) | 1.478 | 4.38 | 0.255 | 0.450 | 38.5 |
| 3B gốc, không fine-tune | 1.578 | 4.85 | 0.025 | 0.480 | 104.7 |

"Có chứa đáp án": đáp án đúng (đã chuẩn hoá) nằm đâu đó trong câu trả lời; thước đo lỏng, ưu ái câu trả lời dài (một câu dài
có thể nhắc nhiều lựa chọn). Dòng 3B đo bằng một script riêng với đúng cùng 300 + 200 câu và cùng hàm của notebook (cell
trong notebook tự bỏ qua vì lúc chạy GPU đang có tiến trình khác giữ khoảng 3.4 GB; 3B bf16 cần 6.56 GiB, 123 giây). Chạy
lại cả notebook hai lần: loss và perplexity của SFT trùng tới chữ số thứ 3, EM 0.260 và 0.255.

Đọc bảng:

- **Loss và perplexity giảm rõ** (6.02 xuống 4.38) và còn thấp hơn cả model 3B (4.85): model 0.5B sau SFT khớp phân phối của
  OpenOrca-Viet hơn, tức viết giống kiểu câu trả lời trong dữ liệu hơn. Perplexity thấp hơn model lớn hơn không có nghĩa là
  "giỏi hơn": nó đo mức giống văn phong dữ liệu.
- **Exact-match kể một câu chuyện, "có chứa đáp án" kể câu chuyện khác.** Theo EM, 0.5B sau SFT (0.255) hơn hẳn 3B (0.025),
  vì 3B luôn giải thích dài dòng (105 ký tự trung bình) theo system prompt của OpenOrca. Theo "có chứa đáp án", 3B không
  fine-tune (0.48) ngang 0.5B sau SFT (0.45); 200 câu cho khoảng tin cậy cỡ ±0.07 nên không phân biệt được hai con số này.
- Vậy SFT ở đây dạy **kỹ năng làm các task kiểu FLAN trong đúng phân phối này cộng với định dạng**: EM tăng từ 0.175 lên
  0.255 và độ dài giảm (định dạng), nhưng tỉ lệ "có chứa đáp án" cũng tăng từ 0.30 lên 0.45, tức model làm đúng task hơn chứ
  không chỉ trả lời gọn hơn. Đó không phải kiến thức tổng quát mới: thước đo chỉ gồm câu trắc nghiệm của cùng nguồn với dữ
  liệu train, và model 0.5B sau SFT chỉ lên **ngang** mức "có chứa đáp án" của model 3B chưa fine-tune, không vượt. Muốn model
  biết nhiều hơn thì chọn model nền lớn hơn; muốn đúng khuôn thì prompt (few-shot, dặn "chỉ trả lời lựa chọn") hoặc SFT đều
  làm được, và SFT có lợi khi phải dùng model nhỏ.

## Bẫy thường gặp

- Trung bình loss theo batch; hoặc đo validation ở chế độ `train` (dropout của LoRA bật).
- Quên `enable_input_require_grads` khi bật gradient checkpointing với model đóng băng: lỗi "element 0 of tensors does not
  require grad" hoặc LoRA không học.
- Ngân sách token quá lớn cho GPU 4GB: logits fp32 của 4 096 token × 151 936 từ vựng đã khoảng 2.5 GB.
- So perplexity giữa hai model có tokenizer khác nhau: perplexity theo token chỉ so được khi tokenizer giống nhau (Qwen2.5
  0.5B và 3B dùng chung tokenizer).
