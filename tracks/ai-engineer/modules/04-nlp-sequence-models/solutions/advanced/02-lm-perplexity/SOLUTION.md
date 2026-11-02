# Hướng làm: language model LSTM tiếng Việt, byte vs BPE

Bài không có code lời giải cho thí nghiệm: thiết lập là của bạn. Bốn hàm được chấm rất ngắn; giá trị của bài nằm ở thí
nghiệm có kiểm soát và cách diễn giải. Dưới đây là các quyết định cần cân nhắc, kết quả tham chiếu và rubric.

## Bốn hàm được chấm

- `batchify`: `torch.tensor(ids[:n*B]).view(B, n)` với `n = len(ids) // B`. `view(n, B).T` (xen kẽ) sai: mỗi dòng không còn là
  văn bản liên tục, chuyền hidden state giữa các đoạn vô nghĩa.
- `get_batch`: `L = min(bptt, n - 1 - i)`; `y` dịch phải một vị trí.
- `nll_to_metrics`: $$\text{ppl} = e^{\text{NLL}/N_{tok}}$$, bit mỗi token $$= \text{NLL}/(N_{tok}\ln 2)$$,
  $$\text{bpc} = \text{NLL}/(N_{char}\ln 2)$$. Quên $$\ln 2$$ là ra nat mỗi ký tự.
- `sample_next`: chia temperature, top-k bằng `torch.topk(...).values[-1]` làm ngưỡng rồi `masked_fill(< ngưỡng, -inf)`,
  `torch.multinomial(softmax, 1, generator=g)`.

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Dữ liệu | 1 000 bài ≥ 2 000 ký tự lấy ngẫu nhiên (seed 0) từ shard `train-00002`, 100 bài khác làm validation; NFC; nối bằng `"\n\n"` | shard 2 khác shard 1 của Intermediate 01; bài dài, tránh bài sơ khai do bot |
| Tokenizer | byte; BPE ByteLevel `tokenizers` 2 000 và 8 000, train trên tập train | cả ba **không mất thông tin** (không `<unk>`), nên bpc so được |
| Model | Embedding 256, LSTM 2 tầng 512, dropout 0.2, không tie embedding | giữ một kiến trúc, chỉ đổi vocab (số tham số đổi theo embedding và lớp output) |
| Train | Adam 2e-3 cosine, clip 0.5, BPTT 128, batch 32, 3 000 bước, chuyền state có `detach` | cùng số bước cho mọi tokenizer, ghi rõ số ký tự đã đọc; thêm một model byte cùng số ký tự |
| Đánh giá | cả chuỗi validation liên tục, batch 1, đoạn 512, chuyền state, tổng NLL | không bỏ đầu mỗi đoạn, không lệch do cắt batch |

## Kết quả tham chiếu

PC RTX 3060 12GB, env `setup/gpu`, seed 0, ngày 2026-10-31. Shard có 5 413 bài ≥ 2 000 ký tự; train 6 432 422 ký tự,
validation 664 568 ký tự (khoảng 18% ký tự nằm ngoài ASCII).

| Tokenizer | Ký tự/token | Tham số | Bước | Ký tự đã đọc khi train | Val PPL theo token | Bit/token | bpc | Thời gian |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Byte (256) | 0.78 | 3.88 triệu | 3 000 | 9.7 triệu | 3.58 | 1.84 | 2.344 | 1.3 phút |
| BPE 2 000 | 2.90 | 5.22 triệu | 3 000 | 35.0 triệu | 55.6 | 5.80 | 2.001 | 1.3 phút |
| BPE 8 000 | 3.48 | 9.83 triệu | 3 000 | 43.3 triệu | 117.0 | 6.87 | 1.975 | 1.9 phút |
| Byte (256), cùng số ký tự | 0.78 | 3.88 triệu | 13 500 | 43.6 triệu | 3.07 | 1.62 | 2.061 | 5.7 phút |

Một lần chạy cùng cấu hình trên laptop RTX 3050 cho bpc 2.344 / 2.003 / 1.980: lệch ở chữ số thứ ba.

Mẫu sinh (mở đầu "Hà Nội là", 60 token BPE hoặc 200 byte):

- Byte, greedy: "Hà Nội là một chiếc tàu khu trục trong thời gian nhạc của các chức từ năm 1940, ..."; byte 13 500 bước, greedy:
  "Hà Nội là Thủ tướng Thủ tướng Thủ tướng ..." (greedy rơi vào vòng lặp).
- BPE 8 000, temperature 0.8, top-k 40: "Hà Nội là người bạn bè của triều đình là do con mình của ông thường là con trai của
  hoàng đế, sau đó ông làm Thái hậu."
- BPE 8 000, temperature 1.2: "... "zựu Đọ truyền hình châmnh xanh" ... Vella Armbill ... Bùi contr Tĩnhzne": nhiệt độ cao
  sinh âm tiết không có thật.
- Với model byte, top-k 40 trên 256 byte gần như không cắt gì: cùng generator, mẫu temperature 0.8 có và không có top-k trùng
  nhau từng byte.

Đọc kết quả:

- Perplexity theo token xếp hạng ngược hẳn bpc. Đây là kết luận chính của bài: chỉ so model khác tokenizer bằng đơn vị độc
  lập tokenizer (bpc, bits per byte), và các bảng xếp hạng LLM công bố perplexity phải nói rõ tokenizer.
- Ngân sách: cùng 3 000 bước, model byte đọc ít hơn 4.5 lần số ký tự. Cho cùng số ký tự thì khoảng cách bpc co từ 0.37 còn
  0.09, BPE vẫn hơn (và model byte tốn gấp 4.5 lần số bước). Khác biệt giữa BPE 2 000 và 8 000 (0.026) nhỏ, nhiều seed mới
  kết luận được.
- Văn bản sinh đúng chính tả phần lớn, đúng ngữ pháp cục bộ, vô nghĩa ở mức câu: LSTM nhỏ học được hình thái và cú pháp ngắn,
  không giữ được chủ đề. Greedy dễ lặp; temperature cao sinh chữ không có thật. GPT mini ở module 05 train trên cùng dữ liệu,
  đo bằng cùng bpc.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 15 | 4 hàm pass mọi test |
| Thí nghiệm có kiểm soát | 25 | ≥ 3 tokenizer, cùng kiến trúc, cùng ngân sách được nêu rõ (bước hoặc ký tự), validation tách khỏi train, seed |
| Đánh giá đúng | 20 | tổng NLL trên cả chuỗi validation, perplexity theo token và bpc, số ký tự đếm trên văn bản gốc |
| Diễn giải | 25 | giải thích bằng số vì sao perplexity theo token không so được; nói về ngân sách ký tự; không kết luận từ chênh lệch nhỏ một seed |
| Chất lượng portfolio | 15 | tóm tắt có số, bảng đầy đủ, mẫu sinh có nhận xét, giới hạn và nối sang module 05 |

Đạt từ 70 điểm. Báo cáo kết luận "model byte tốt nhất vì perplexity thấp nhất" không quá 40 điểm.
