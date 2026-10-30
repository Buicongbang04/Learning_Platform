# Lời giải: BiLSTM phân loại cảm xúc UIT-VSFC

## Cách làm

**Dữ liệu.** UIT-VSFC đã chữ thường và tách dấu câu, nên tokenize chỉ cần NFC + `lower()` + `split()`. Vocab âm tiết
`min_freq=2` chỉ có 1 535 mục (kể cả `<pad>`, `<unk>`): văn bản hẹp miền, âm tiết tiếng Việt có hạn. `encode_batch` pad
tới câu dài nhất **trong batch** (trung vị 11 âm tiết, p99 là 52, dài nhất 159; cắt ở 64).

**Model.** Embedding → dropout → `nn.LSTM` trên chuỗi đã pack → `torch.cat(list(h_n), -1)` → dropout → `Linear`.

| Lựa chọn | Lời giải | Vì sao |
| --- | --- | --- |
| Packing | `pack_padded_sequence(..., enforce_sorted=False)` | state cuối là state ở độ dài thật; không pack thì kết quả phụ thuộc câu dài nhất trong batch |
| Biểu diễn câu | nối `h_n` hai chiều | chiều ngược kết thúc ở token đầu nên thấy cả câu từ phải sang |
| Chọn epoch | val macro-F1, nạp lại `deepcopy(state_dict())` | lớp neutral hiếm, accuracy gần như không đổi giữa các epoch |
| Tái lập | `torch.manual_seed(seed)` + `randperm(generator=g)` | dropout và thứ tự batch cố định theo seed |

**Metric.** F1 từng lớp $$= 2TP / (2TP + FP + FN)$$, lớp không có TP thì 0, rồi lấy trung bình không trọng số.

## Kết quả thật

Embedding 128, hidden 128, dropout 0.3, Adam 2e-3, batch 64, 6 epoch, seed 0, CPU 4 luồng:

| Model | Val macro-F1 theo epoch | Epoch chọn |
| --- | --- | --- |
| LSTM một chiều | 0.615, 0.658, 0.701, 0.741, 0.760, 0.771 | 6 |
| BiLSTM | 0.666, 0.721, 0.740, 0.800, 0.810, 0.787 | 5 |

| Model (test, 3 166 câu) | Accuracy | Macro-F1 | F1 negative | F1 neutral | F1 positive |
| --- | --- | --- | --- | --- | --- |
| Đoán toàn positive | 0.5022 | 0.2229 | 0 | 0 | 0.669 |
| TF-IDF 1-2 gram + LR (C = 10) | 0.8977 | 0.7159 | 0.915 | 0.311 | 0.922 |
| LSTM một chiều | 0.9021 | 0.7246 | 0.920 | 0.327 | 0.927 |
| BiLSTM | 0.9037 | 0.7549 | 0.922 | 0.415 | 0.928 |

Confusion matrix của BiLSTM (dòng là nhãn thật negative, neutral, positive):

```
[[1323   25   61]
 [  49   55   63]
 [  89   18 1483]]
```

Đọc kết quả:

- Ba model thật có accuracy trong khoảng 0.6 điểm; macro-F1 tách chúng ra (0.716, 0.725, 0.755), và gần như toàn bộ
  khác biệt đến từ lớp neutral (0.31 → 0.42).
- BiLSTM vẫn đoán sai 112 / 167 câu neutral. Đọc các câu sai: "thời gian học .", "tâm lý .", "bài thuyết trình của các
  sinh viên ." là mảnh câu không có cảm xúc rõ, còn "môn học này giúp chúng em hiểu ra những vấn đề cơ bản ." thì nhãn
  neutral cũng gây tranh cãi. Giới hạn nằm ở nhãn và dữ liệu nhiều hơn ở model.
- LSTM một chiều chưa bão hoà ở epoch 6 (val F1 còn tăng); BiLSTM đạt đỉnh ở epoch 5 rồi tụt: chọn epoch theo
  validation có ý nghĩa: trên val, epoch 5 hơn epoch 6 tới 0.023 macro-F1.
- Thời gian lần đo này 5-6 phút mỗi LSTM vì CPU bị chia sẻ; trên laptop rảnh nhanh hơn vài lần. TF-IDF + LR train trong
  vài giây và chỉ kém 0.04 macro-F1: trong sản phẩm thật, baseline này thường là điểm khởi đầu hợp lý.

## Bẫy thường gặp

- Không pack: test "padding invariance" fail; trên dữ liệu thật accuracy vẫn ổn (câu thường ngắn) nên lỗi khó thấy.
- `h_n[-1]` thay vì nối hai chiều: chỉ dùng chiều ngược, mất nửa thông tin.
- Lưu `state_dict()` không copy: "bản tốt nhất" luôn là bản cuối.
- Lấy trung bình loss theo batch thay vì theo mẫu; quên `model.eval()` trong `predict` (dropout 0.3 làm dự đoán ngẫu nhiên).
- Chọn epoch theo test: số báo cáo bị lạc quan. Test chỉ dùng một lần ở cuối.
