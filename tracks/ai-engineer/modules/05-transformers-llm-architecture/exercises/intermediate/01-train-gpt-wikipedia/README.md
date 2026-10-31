---
title: Train GPT mini trên Wikipedia tiếng Việt, so với LSTM bằng bits-per-character
level: intermediate
services: []
files:
  - path: starter/train_gpt.ipynb
    note: 8 hàm TODO
  - path: tests/test_train_gpt.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py wikipedia-vi
  - uv run jupyter lab tracks/ai-engineer/modules/05-transformers-llm-architecture/exercises/intermediate/01-train-gpt-wikipedia/starter/train_gpt.ipynb
  - uv run pytest tracks/ai-engineer/modules/05-transformers-llm-architecture/exercises/intermediate/01-train-gpt-wikipedia -q
---

## Mục tiêu

Viết các mảnh của một vòng pretrain LLM (chia dữ liệu tái lập, lấy batch, warmup + cosine, nhóm weight decay, đánh giá bằng
cửa sổ trượt), rồi train GPT mini của bài Basic 01 trên đúng dữ liệu và tokenizer mà LSTM của module 04 đã dùng. Kết quả là
một con số bits-per-character so được trực tiếp với LSTM, và một hàm đánh giá mà module 10 dùng lại để đo model đã quantize.

## Đề bài

**Phần cứng:** CPU · ~150 phút

Thời gian trên là thời gian làm bài. Thời gian máy của notebook lời giải: trên CPU 4 luồng (PC, máy rảnh) cả notebook 9 phút,
trong đó train model `n_embd` 128 1 500 bước mất 8.3 phút; với kernel `ai-gpu` (GPU 4GB là đủ, dưới 1 GB VRAM) notebook tự
dùng model `n_embd` 256 và 3 000 bước, cùng ngân sách với LSTM module 04. Đọc mục 2 phần lý thuyết và mục 7 module 04
(perplexity, bpc). Mở `starter/train_gpt.ipynb`:

1. `long_articles`, `split_articles`: tái lập đúng 1 000 bài train, 100 bài validation của module 04.
2. `get_batch`, `lr_at` (warmup tuyến tính rồi cosine về `min_lr`), `configure_optimizer` (AdamW, hai nhóm weight decay).
3. `sliding_windows`, `evaluate_nll` (cửa sổ trượt, gom batch), `nll_to_metrics` (giống module 04).

Rồi chạy các cell `explore`: tokenizer BPE 8 000, train, bpc trên validation so với LSTM, loss theo vị trí trong cửa sổ, sinh
văn bản. Sau đó làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `long_articles` lọc theo độ dài trước chuẩn hoá rồi NFC; `split_articles` đúng hoán vị `RandomState`; trên dữ liệu thật ra
  5 413 bài dài, train 6 432 422 ký tự, validation 664 568 ký tự (đúng module 04).
- `get_batch` lấy đúng cửa sổ, `y` dịch một vị trí, vị trí bắt đầu phủ hết khoảng hợp lệ.
- `lr_at` đúng warmup, cosine, giữ `min_lr` sau `total`; `configure_optimizer` chỉ cho ma trận chịu weight decay, tham số dùng
  chung đếm một lần, `betas=(0.9, 0.95)`.
- `sliding_windows` tính mỗi target đúng một lần, mỗi target (trừ cửa sổ đầu) có ít nhất `block_size - stride` token ngữ
  cảnh; `evaluate_nll` khớp bản tham chiếu từng cửa sổ, có gom batch, trả lại chế độ train/eval.
- Cell `explore` in số giống mục 2 lý thuyết (máy khác có thể lệch nhẹ).

## Gợi ý

### Gợi ý 1

Viết `sliding_windows` bằng một biến đếm "đã tính tới target nào": mỗi cửa sổ mới chỉ đóng góp những target mà cửa sổ trước chưa
tính, và chúng luôn nằm ở **cuối** cửa sổ. Thử tay với `n_tokens = 21, block_size = 8, stride = 4` trước khi viết code.

### Gợi ý 2

Cửa sổ cuối thường ngắn hơn `block_size`; gom các cửa sổ theo độ dài (dict độ dài → danh sách) rồi `torch.stack` từng nhóm.
`F.cross_entropy(logits.transpose(1, 2), y, reduction="none")` cho NLL từng vị trí shape `(B, T)`. Trong `configure_optimizer`,
`model.parameters()` đã loại trùng tham số dùng chung; `named_parameters()` cũng vậy.
