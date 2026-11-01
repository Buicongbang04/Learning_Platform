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
1 297 bước, 613 giây, VRAM đỉnh 2.83 GiB. Tỉ lệ token thật: **0.999** với batch theo ngân sách token, **0.635** với batch
cố định 8 mẫu theo thứ tự gốc.

| Model | Val loss | Val perplexity | Trắc nghiệm EM | Độ dài trả lời TB (ký tự) |
| --- | --- | --- | --- | --- |
| 0.5B gốc | 1.796 | 6.02 | 0.175 | 54.4 |
| 0.5B + SFT LoRA (4 000 mẫu, 1 epoch) | 1.478 | 4.39 | 0.260 | 38.7 |
| 3B gốc, không fine-tune | <<I02_3B_LOSS>> | <<I02_3B_PPL>> | <<I02_3B_EM>> | <<I02_3B_LEN>> |

Dòng 3B đo bằng một script riêng với đúng cùng 300 + 200 câu (cell trong notebook tự bỏ qua vì lúc chạy notebook GPU đang có
tiến trình khác giữ khoảng 7 GB); <<I02_3B_NOTE>>.

Đọc bảng:

- **Loss và perplexity giảm rõ** (6.02 xuống 4.39): model khớp phân phối của OpenOrca-Viet hơn, tức viết giống kiểu câu trả
  lời của GPT-4 dịch sang tiếng Việt hơn. Đó là thay đổi **văn phong** là chủ yếu: câu trả lời trắc nghiệm ngắn đi (54 xuống
  39 ký tự) và hay viết đúng lựa chọn hơn.
- **Exact-match tăng** từ 0.175 lên 0.260; 200 câu cho khoảng tin cậy cỡ ±0.06 nên mức tăng có thật nhưng không lớn. Đọc
  câu trả lời mẫu: model gốc hay viết dài hoặc thêm lời dẫn ("Dựa trên câu hỏi của bạn..."), exact-match tính là sai dù
  ý có thể đúng; một phần mức tăng là do câu trả lời gọn đúng khuôn của dữ liệu.
- <<I02_3B_READ>>

## Bẫy thường gặp

- Trung bình loss theo batch; hoặc đo validation ở chế độ `train` (dropout của LoRA bật).
- Quên `enable_input_require_grads` khi bật gradient checkpointing với model đóng băng: lỗi "element 0 of tensors does not
  require grad" hoặc LoRA không học.
- Ngân sách token quá lớn cho GPU 4GB: logits fp32 của 4 096 token × 151 936 từ vựng đã khoảng 2.5 GB.
- So perplexity giữa hai model có tokenizer khác nhau: perplexity theo token chỉ so được khi tokenizer giống nhau (Qwen2.5
  0.5B và 3B dùng chung tokenizer).
