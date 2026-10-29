---
title: LSTM cho chuỗi độ dài thay đổi
level: intermediate
services: []
files:
  - path: starter/sequence.py
    note: 4 TODO (pad, model, clip, train)
  - path: tests/test_sequence.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/13-deep-learning/exercises/intermediate/02-lstm-sequences -q
---

## Mục tiêu

Xử lý đúng hai việc mà mọi model chuỗi thật phải làm: chuỗi dài ngắn khác nhau (padding + packing)
và gradient bùng nổ (clipping). Thấy bằng thí nghiệm vì sao LSTM/GRU nhớ được thông tin xa còn RNN
thường thì không.

## Đề bài

Trong `starter/sequence.py`:

1. `pad_sequences(seqs, pad_value=0) -> (padded, lengths)`: đệm bên phải về độ dài lớn nhất.
2. `SequenceClassifier(vocab_size, embed_dim, hidden_dim, n_classes, cell="lstm", padding_idx=0)`:
   `nn.Embedding` → `nn.RNN` / `nn.GRU` / `nn.LSTM` (chọn qua `cell`, một tầng, một chiều,
   `batch_first=True`) → `nn.Linear` trên hidden state **sau token thật cuối cùng** của mỗi chuỗi.
   Dùng `pack_padded_sequence(..., enforce_sorted=False)` để RNN không chạy qua padding.
3. `clip_gradients(model, max_norm) -> float`: cắt gradient theo chuẩn L2 gộp mọi tham số, trả chuẩn
   **trước** khi cắt.
4. `train_classifier(model, X, lengths, y, epochs, lr, batch_size, clip, seed) -> list[float]`: Adam,
   cross-entropy, clip sau `backward()` trước `step()`, xáo bằng
   `torch.Generator().manual_seed(seed + epoch)`, trả loss trung bình theo mẫu mỗi epoch.

Bài toán thử trong test: chuỗi 10–20 token, nhãn là token **đầu tiên** chẵn hay lẻ. Model đọc trái
sang phải phải giữ một bit thông tin qua 10–20 bước giữa các token nhiễu.

## Tiêu chí đạt

- `pad_sequences` đúng giá trị, dtype `long`, hỗ trợ `pad_value`.
- Ba loại cell đều chạy; module bên trong đúng loại.
- Với LSTM và GRU: thêm cột padding, hoặc ghi token thật vào vị trí padding, không đổi output; mỗi
  chuỗi chạy riêng cho cùng output như khi chạy trong batch.
- `clip_gradients` khớp `nn.utils.clip_grad_norm_`, sau khi cắt chuẩn gradient bằng `max_norm`.
- Cùng seed cho cùng dãy loss.
- LSTM đạt trên 90% accuracy trên tập kiểm tra của bài toán "token đầu tiên" (2 seed).

## Gợi ý

### Gợi ý 1

`pack_padded_sequence` cần `lengths` trên CPU. Với `enforce_sorted=False`, PyTorch tự sắp theo độ
dài rồi trả `h_n` **về đúng thứ tự gốc** của batch, nên `h_n[-1]` dùng thẳng được. LSTM trả
`(output, (h_n, c_n))`, RNN và GRU trả `(output, h_n)`.

### Gợi ý 2

Nếu loss đứng yên ở khoảng 0.69 (đoán mò cho hai lớp), thử learning rate nhỏ hơn: bài toán này có
"bước chuyển pha", model đứng yên một lúc rồi đột ngột học được. Với lr 1e-2 LSTM thường kẹt; với
3e-3 thì học được.
