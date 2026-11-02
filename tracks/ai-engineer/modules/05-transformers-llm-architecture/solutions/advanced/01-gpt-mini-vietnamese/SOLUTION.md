# Hướng làm: GPT mini tiếng Việt từ số 0

Bài không có code lời giải cho pipeline: thiết lập là của bạn. Ba hàm được chấm ngắn; giá trị của bài nằm ở một lần pretrain
có kiểm soát, đánh giá trung thực và một checkpoint dùng lại được. Dưới đây là các quyết định cần cân nhắc, kết quả của bản tham
chiếu và rubric.

## Ba hàm được chấm

- `save_checkpoint`: `torch.save({"format": "gpt-mini-v1", "config": dataclasses.asdict(config), "state_dict": {k: v.cpu() ...},
  "tokenizer": tokenizer.to_str(), "step": step, "metrics": dict(metrics)}, path)`. Mọi thứ trong dict là tensor, số, chuỗi, dict
  và list, nên đọc lại được bằng `weights_only=True` (không chạy pickle tuỳ ý: checkpoint tải từ nơi khác là code của người khác).
  Lưu tokenizer **trong** checkpoint: model không có tokenizer đúng thì vô dụng, và đó là lỗi hay gặp nhất khi chia sẻ model.
- `load_checkpoint`: `torch.load(path, map_location="cpu", weights_only=True)`, kiểm `format`, dựng
  `GPT(GPTConfig(**config))`, `load_state_dict` (tying giữ nguyên vì `lm_head.weight` và `tok_emb.weight` là cùng một tensor của
  model mới, state dict chỉ chép giá trị vào), `.to(device).eval()`.
- `distinct_n`: `len(set(ngrams)) / len(ngrams)`, chia cho số n-gram chứ không chia số token.

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Validation | đúng 100 bài của module 04 (`RandomState(0)`, shard 2, bài ≥ 2 000 ký tự), 664 568 ký tự | bpc so được với LSTM và với bài Intermediate 01 |
| Train | mọi bài ≥ 2 000 ký tự còn lại của hai shard: 14 473 bài, 95.5 triệu ký tự, 28.3 triệu token | gấp 15 lần dữ liệu của bài Intermediate 01; không bài validation nào lọt vào train |
| Tokenizer | BPE byte-level 8 000 train trên 1 000 bài train của module 04 (3.48 ký tự mỗi token trên validation) | giữ nguyên tokenizer để chỉ đổi dữ liệu và model; train tokenizer trên dữ liệu lớn hơn sẽ nén tốt hơn một chút |
| Model | `GPT` bài Basic 01: PC 6 tầng × 384, 6 head, context 256 (13.8 triệu tham số, 10.6 triệu ngoài embedding); laptop 4 tầng × 256, context 256 (5.27 triệu) | vừa VRAM, đủ nhỏ để train trong vài phút tới vài chục phút |
| Train | AdamW (0.9, 0.95), weight decay 0.1 cho ma trận, lr 1e-3, warmup 400 (laptop 300), cosine về 1e-4, clip 1.0, bf16 autocast; PC batch 64 × 256, 8 000 bước, `torch.compile`; laptop batch 32 × 256, 6 000 bước | công thức của nanoGPT thu nhỏ |
| Đánh giá | `evaluate_nll` cửa sổ trượt, stride bằng nửa context, mỗi 1 000 bước | đúng thước đo của bài Intermediate 01 và module 10 |

## Kết quả tham chiếu

PC RTX 3060 12GB, env `setup/gpu`, seed 0, ngày 2026-11-01, GPU dùng chung với một tiến trình khác.

| Model | Tham số | Dữ liệu train | Token đã thấy | Thời gian | VRAM đỉnh | Val PPL theo token | bpc |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LSTM 2 tầng 512 (module 04) | 9.83 triệu | 1 000 bài | 12.3 triệu (BPE) | 1.9 phút | dưới 0.8 GB | 117.0 | 1.975 |
| GPT mini bài Intermediate 01 (GPU) | 5.24 triệu | 1 000 bài | 12.3 triệu | 3.2 phút | dưới 1 GB | 98.2 | 1.901 |
| Cấu hình laptop | 5.27 triệu | 14 473 bài | 49.2 triệu (1.7 epoch) | 5.3 phút | 1.55 GB | 41.0 | 1.540 |
| Cấu hình PC | 13.8 triệu | 14 473 bài | 131.1 triệu (4.6 epoch) | 17.6 phút | 3.01 GB | 25.8 | 1.347 |

Đường bpc của cấu hình PC theo bước: 1.754 (1 000), 1.544 (2 000), 1.472 (3 000), 1.424 (4 000), 1.395 (5 000), 1.369 (6 000),
1.354 (7 000), 1.347 (8 000). Tốc độ trung bình khoảng 124 000 token/giây, tương đương khoảng 10 TFLOP/s theo $$6ND$$ (tính cả
lớp output); đầu run khoảng 168 000 token/giây (14 TFLOP/s), về cuối chậm lại vì GPU dùng chung. Loss train cuối khoảng 2.9-3.0 nat so với validation 3.25: khoảng cách 0.3 nat sau 4.6 epoch, có dấu hiệu bắt đầu
học thuộc; thêm dữ liệu (hai shard còn lại của Wikipedia tiếng Việt) có lợi hơn thêm bước.

Nạp lại checkpoint `gpt-mini-v1` cho đúng bpc 1.3473. Mẫu sinh từ "Hà Nội là" (100 token, generator seed 0):

- Greedy: "Hà Nội là một trong những địa danh nổi tiếng nhất của Việt Nam. / Lịch sử / Thời kỳ đầu / Thời kỳ đầu / ..." (distinct-2
  0.20: rơi vào vòng lặp tiêu đề mục).
- Temperature 0.8, top-k 40: "Hà Nội là một trong những xã thuần của huyện Bình Định. / Xã Tân Bình có diện tích 32,53 km², dân số
  năm 2018 là 14.628 người, mật độ dân số đạt 83 người/km². / Hành chính / Xã Tân Bình được chia thành 9 ấp: Cây Cẩm, Cây Mai, Cây
  Mai, ..." (distinct-2 0.64). Model đã học **khuôn** của bài sơ khai về xã (Wikipedia tiếng Việt có hàng chục nghìn bài do bot
  tạo): con số đúng định dạng nhưng bịa, sai sự thật ("Hà Nội là xã của huyện Bình Định").
- Temperature 1.0 và 1.2: distinct-2 0.99, âm tiết lạ, tên riêng ghép bậy ("Disiohe el Barbera").

Đọc kết quả:

- Dữ liệu nhiều hơn 15 lần đưa cùng một model 5 triệu tham số từ 1.90 xuống 1.54 bpc; model to hơn 2.6 lần và nhiều token hơn
  2.7 lần xuống tiếp 1.35. Với LM nhỏ, dữ liệu và compute là giới hạn, không phải kiến trúc (mục 7 lý thuyết).
- Perplexity theo token 25.8 không so được với số công bố của model khác tokenizer; bpc so được với LSTM của module 04.
- Văn bản trôi chảy cục bộ, sai sự thật và lặp: đó là một base model, chưa có instruction tuning (module 14), và greedy luôn lặp.

## Checkpoint cho module 08 và 10

Bản tham chiếu lưu theo định dạng `gpt-mini-v1` (đặc tả trong notebook của bài): cấu hình PC `GPTConfig(vocab_size=8000,
block_size=256, n_layer=6, n_head=6, n_embd=384, dropout=0.0)`, bước 8 000, bpc 1.3473, khoảng 55 MB float32; cấu hình laptop
`GPTConfig(vocab_size=8000, block_size=256, n_layer=4, n_head=4, n_embd=256, dropout=0.0)`, bước 6 000, bpc 1.5397. Checkpoint
không nằm trong repo; module 08 và 10 nạp checkpoint do chính người học train, hoặc tự train lại cấu hình laptop (5 phút trên GPU).

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 15 | 3 hàm pass mọi test |
| Dữ liệu và tách validation | 15 | validation đúng của module 04 (hoặc tách riêng có lý do), chứng minh không rò rỉ, ghi số bài, ký tự, token, số epoch |
| Train có kiểm soát | 20 | cấu hình ghi đủ (tham số, batch, lr, warmup, bước, token, dtype, VRAM, thời gian), đường loss train và validation, seed |
| Đánh giá đúng | 20 | bpc bằng cửa sổ trượt trên cả validation, so với LSTM và bài Intermediate 01 kèm ngân sách; nạp lại checkpoint cho cùng số |
| Diễn giải | 15 | giải thích bằng số đóng góp của dữ liệu và kích thước model; nhận ra overfitting hoặc không; không so perplexity khác tokenizer |
| Portfolio | 15 | mẫu sinh có distinct-n và nhận xét lỗi (lặp, bịa), giới hạn, checkpoint dùng lại được (định dạng, đường dẫn) |

Đạt từ 70 điểm. Báo cáo không có bpc trên validation hoặc đánh giá trên dữ liệu train không quá 40 điểm.
