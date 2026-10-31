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
| Train | Adam 2e-3 cosine, clip 0.5, BPTT 128, batch 32, 3 000 bước, chuyền state có `detach` | cùng số bước cho mọi tokenizer, ghi rõ số ký tự đã đọc |
| Đánh giá | cả chuỗi validation liên tục, batch 1, đoạn 512, chuyền state, tổng NLL | không bỏ đầu mỗi đoạn, không lệch do cắt batch |

## Kết quả tham chiếu

RTX 3050 Laptop 4GB dùng chung với tiến trình khác, seed 0. Train 6 432 422 ký tự, validation 664 568 ký tự.

| Tokenizer | Ký tự/token | Tham số | Ký tự đã đọc khi train | Val PPL theo token | Bit/token | bpc | Thời gian |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Byte (256) | 0.78 | 3.88 triệu | 9.7 triệu | 3.58 | 1.84 | 2.344 | 8.4 phút |
| BPE 2 000 | 2.90 | 5.22 triệu | 35.0 triệu | 55.8 | 5.80 | 2.003 | 8.9 phút |
| BPE 8 000 | 3.48 | 9.83 triệu | 43.3 triệu | 118.7 | 6.89 | 1.980 | 13.6 phút |

Mẫu sinh (temperature 0.8, mở đầu "Hà Nội là"):

- Byte: "Hà Nội là các cuộc chứa lực phải quay. Trong tháng 4 năm 2014: Halakuro cũng có thể làm chứng không không thể là..."
- BPE 8 000: "Hà Nội là một loại thực vật sản xuất khô ăn, sử dụng các mối đe dọa. Trong khi đó, các nhân vật chính là thể hiện sức
  khỏe hơn so với các cống hiến."

Đọc kết quả:

- Perplexity theo token xếp hạng ngược hẳn bpc. Đây là kết luận chính của bài: chỉ so model khác tokenizer bằng đơn vị độc
  lập tokenizer (bpc, bits per byte), và các bảng xếp hạng LLM công bố perplexity phải nói rõ tokenizer.
- Ngân sách không công bằng: cùng 3 000 bước, model byte đọc ít hơn 4.5 lần số ký tự. Báo cáo tốt chạy thêm cấu hình cùng
  số ký tự (byte 13 500 bước) hoặc nói rõ giới hạn này; khác biệt bpc giữa BPE 2 000 và 8 000 (0.02) nhỏ, cần nhiều seed mới
  kết luận.
- Văn bản sinh đúng chính tả, đúng ngữ pháp cục bộ, vô nghĩa ở mức câu: LSTM nhỏ học được hình thái và cú pháp ngắn, không
  giữ được chủ đề. GPT mini ở module 05 train trên cùng dữ liệu, đo bằng cùng bpc.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 15 | 4 hàm pass mọi test |
| Thí nghiệm có kiểm soát | 25 | ≥ 3 tokenizer, cùng kiến trúc, cùng ngân sách được nêu rõ (bước hoặc ký tự), validation tách khỏi train, seed |
| Đánh giá đúng | 20 | tổng NLL trên cả chuỗi validation, perplexity theo token và bpc, số ký tự đếm trên văn bản gốc |
| Diễn giải | 25 | giải thích bằng số vì sao perplexity theo token không so được; nói về ngân sách ký tự; không kết luận từ chênh lệch nhỏ một seed |
| Chất lượng portfolio | 15 | tóm tắt có số, bảng đầy đủ, mẫu sinh có nhận xét, giới hạn và nối sang module 05 |

Đạt từ 70 điểm. Báo cáo kết luận "model byte tốt nhất vì perplexity thấp nhất" không quá 40 điểm.
