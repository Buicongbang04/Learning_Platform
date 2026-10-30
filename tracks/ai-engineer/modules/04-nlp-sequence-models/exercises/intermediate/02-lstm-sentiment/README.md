---
title: BiLSTM phân loại cảm xúc UIT-VSFC
level: intermediate
services: []
files:
  - path: starter/sentiment.ipynb
    note: 8 hàm/lớp TODO
  - path: tests/test_sentiment.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py uit-vsfc
  - uv run jupyter lab tracks/ai-engineer/modules/04-nlp-sequence-models/exercises/intermediate/02-lstm-sentiment/starter/sentiment.ipynb
  - uv run pytest tracks/ai-engineer/modules/04-nlp-sequence-models/exercises/intermediate/02-lstm-sentiment -q
---

## Mục tiêu

Dựng trọn pipeline phân loại văn bản tiếng Việt bằng LSTM: vocab, padding, packing, BiLSTM, train có chọn epoch theo
validation, metric đúng cho dữ liệu lệch lớp, và so với baseline rẻ. Làm xong bạn biết những lỗi "im lặng" của RNN với
batch có padding, và đọc được vì sao accuracy 90% chưa nói lên gì trên UIT-VSFC.

## Đề bài

**Phần cứng:** CPU · ~120 phút

Thời gian trên là thời gian làm bài. Chạy cả notebook lời giải: vài phút trên CPU 4 luồng khi máy rảnh; lần đo của lời
giải mất 12 phút (mỗi LSTM 5-6 phút) vì CPU đang bị việc khác chiếm.

Mở `starter/sentiment.ipynb` và làm theo đặc tả trên từng cell:

1. `load_split`, `tokenize`, `build_vocab`, `encode_batch`: đọc parquet, NFC + chữ thường + tách khoảng trắng, vocab có
   `<pad>` = 0 và `<unk>` = 1, batch pad tới câu dài nhất **trong batch**.
2. `LSTMClassifier`: embedding (`padding_idx=0`) → dropout → `nn.LSTM` (có thể hai chiều) chạy trên
   `pack_padded_sequence` → nối hidden state cuối của các chiều → dropout → `Linear`.
3. `macro_f1` (tự viết, không sklearn), `predict` (chế độ eval), `train_classifier` (Adam, clip 1.0, chọn epoch theo val
   macro-F1, nạp lại **bản sao** trọng số tốt nhất).

Rồi chạy các cell `explore`: hai baseline (đoán lớp nhiều nhất, TF-IDF + logistic regression), LSTM một chiều và BiLSTM
(embedding 128, hidden 128, Adam 2e-3, batch 64, 6 epoch, seed 0), bảng kết quả trên test, confusion matrix và các câu
neutral bị đoán sai. Sau đó làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- Vocab, `encode_batch` đúng ví dụ (thứ tự tần suất, hoà theo chữ cái, câu rỗng thành `<unk>`, độ dài batch).
- Logits của một câu **không đổi** khi ghép chung batch với câu dài hơn (packing đúng); chiều ngược đọc tới token đầu.
- `macro_f1` khớp `sklearn` (kể cả lớp không bao giờ được đoán); `predict` không phụ thuộc dropout hay kích thước batch.
- `train_classifier`: history đúng định dạng; học được bài "token khoá" (val macro-F1 ≥ 0.9); trên dữ liệu 50% nhãn
  nhiễu (val tụt sau epoch 2) model trả về mang trọng số của epoch tốt nhất; train loss là trung bình theo mẫu; cùng
  seed cho cùng history, khác seed thì khác.
- UIT-VSFC thật: đúng số câu và phân bố nhãn, vocab 1 535; BiLSTM 64 chiều train 2 epoch trên 4 000 câu đạt val
  accuracy ≥ 0.8 trong dưới 30 giây.
- Cell `explore` in ra bảng giống mục 5 lý thuyết (BiLSTM test macro-F1 0.7549; máy khác có thể lệch ở chữ số thứ hai).

## Gợi ý

### Gợi ý 1

`pack_padded_sequence(x, lengths.cpu(), batch_first=True, enforce_sorted=False)` rồi đưa thẳng vào `nn.LSTM`; với
`(_, (h, _)) = self.lstm(packed)`, `h` có shape `(num_directions, N, hidden)` và đã là state ở **độ dài thật** của từng câu
(chiều ngược: state sau khi đọc về token đầu). `torch.cat(list(h), dim=-1)` nối hai chiều. Lấy `output[:, -1]` của chuỗi
không pack là lỗi kinh điển: với câu ngắn, đó là state sau khi đọc một đống `<pad>`.

### Gợi ý 2

`model.state_dict()` trả **tham chiếu** tới tensor đang train: lưu nó làm "bản tốt nhất" thì nó vẫn đổi theo các epoch
sau. Dùng `copy.deepcopy(model.state_dict())`. Cộng `loss.item() * len(batch)` rồi chia cho số mẫu. Xáo bằng
`torch.randperm(N, generator=g)` với `g` seed riêng, và gọi `torch.manual_seed(seed)` đầu hàm để dropout tái lập được.
