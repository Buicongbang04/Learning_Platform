# Lời giải: Whisper trên FLEURS tiếng Việt và vòng TTS → STT

## Cách làm

- Bốn hàm của Basic 01 dán nguyên.
- `read_wav`: kiểm `RIFF`/`WAVE`, duyệt chunk từ byte 12 (`pos += 8 + size + (size & 1)`), đọc `fmt ` bằng
  `struct.unpack("<HHIIHH", ...)`, chunk `data` đọc bằng `np.frombuffer` với `"<i2"` (chia 32768) hoặc `"<f4"`,
  `reshape(-1, channels).mean(axis=1)`.
- `pinned_subset`: một `set` các id đã gặp, dừng khi đủ `n`.
- `read_number_vi`: hàm đọc ba chữ số với cờ "đọc đủ hàng trăm", tách nhóm ba từ phải sang trái, bỏ nhóm 0, ghép
  "nghìn/triệu/tỷ". Hàng chục 1 là "mười", từ 2 là "<số> mươi"; đơn vị sau "mươi": mốt, tư, lăm; sau "mười": một, bốn, lăm;
  chục 0 mà đơn vị khác 0 thì "linh".
- `normalize_for_tts`: một regex bắt số nguyên (`\d{1,3}(?:\.\d{3})+|\d+`) không đứng sát chữ số khác hay phần thập phân,
  tuỳ chọn đơn vị `đồng|đ|vnđ|vnd` theo sau, thay bằng `read_number_vi` + " đồng".

## Kết quả của lời giải mẫu

50 câu ghim (id câu khác nhau đầu tiên của `test.tsv`, 662 giây audio, câu dài nhất 25.4 giây), CPU 4 luồng, int8, PC của
track (máy dùng chung); toàn bộ notebook chạy khoảng 20 phút. Log: `.superpowers/scratch/logs/int02_solution_outputs.log`
và `int02_tts_fixed.log`.

| Model | Cấu hình | WER | CER | Giây | RTF |
| --- | --- | --- | --- | --- | --- |
| tiny | beam 1 | 0.627 | 0.341 | 40.0 | 0.060 |
| tiny | beam 5 | 0.594 | 0.320 | 41.2 | 0.062 |
| base | beam 1 | 0.460 | 0.226 | 33.7 | 0.051 |
| base | beam 5 | 0.441 | 0.215 | 50.5 | 0.076 |
| small | beam 1 | 0.242 | 0.115 | 108.9 | 0.165 |
| small | beam 5 | 0.234 | 0.115 | 123.4 | 0.187 |
| small | beam 5 + VAD | 0.243 | 0.113 | 128.3 | 0.194 |

- **Cỡ model là núm vặn lớn nhất**: từ `tiny` lên `small`, WER giảm từ khoảng 0.6 xuống 0.23, đổi lại RTF gấp khoảng 3 lần
  (vẫn nhanh hơn thời gian thực 5 lần trên 4 luồng CPU). `tiny` và `base` sai khoảng một nửa số từ tiếng Việt: không dùng
  được cho sản phẩm. Thời gian của `tiny` và `base` gần nhau vì phần cố định (nạp, tính Mel, VAD) chiếm nhiều.
- **Beam 5** giảm WER 0.008 tới 0.033 tuỳ cỡ, tốn thêm 3% tới 50% thời gian: với `small`, chênh lệch nằm trong nhiễu của 50 câu.
- **VAD** trên câu ngắn đã cắt sẵn gần như không đổi gì (0.234 so với 0.243): nó có ích với audio dài có khoảng lặng.
- **Chuẩn hoá**: cùng bản nhận dạng của `small` beam 5, WER 0.301 khi không chuẩn hoá, 0.268 khi chỉ đổi chữ thường, 0.234
  sau `normalize_vi`. Chênh 0.067 chỉ vì cách chuẩn hoá, lớn hơn chênh lệch giữa mọi cấu hình beam/VAD của `small`.
- **Audio dài** (50 câu nối lại, khoảng 9 phút, `small` beam 5): WER 0.306 và chỉ 1 381 từ ra trên 1 565 từ thật: model **bỏ
  sót** cả đoạn khi một cửa sổ 30 giây bị đoán sai ranh giới. VAD cho 1 461 từ (WER 0.305); tắt điều kiện câu trước cho
  1 527 từ và WER 0.270, tốt nhất trong ba. Câu ngắn riêng lẻ (0.234) vẫn tốt hơn: cắt audio theo câu hoặc theo khoảng lặng
  trước khi nhận dạng là cách đơn giản nhất.
- Lỗi điển hình đọc tận mắt: sai dấu thanh ("tân ngữ" thành "tăng ngữ"), tên riêng nước ngoài ("Plitvice Lakes" thành "lít
  vì kè la két"), số viết thành chữ số ("một phần" thành "1 phần").

TTS (`mms-tts-vie`, seed 0, CPU), Whisper `small` beam 5 nghe lại, CER tính sau khi đưa **cả hai phía** qua
`normalize_for_tts` (Whisper viết số nghe được bằng chữ số):

| Đầu vào | CER |
| --- | --- |
| 20 câu FLEURS (đã chuẩn hoá, không có số) | 0.113 |
| 10 câu tài chính, đưa nguyên chữ số vào TTS | 0.502 |
| 10 câu tài chính, `normalize_for_tts` trước TTS | 0.128 |

RTF của TTS trên CPU 0.245. Vocab của `mms-tts-vie` có 96 ký hiệu và chữ số duy nhất là "2"; tokenizer bỏ im lặng mọi
ký tự ngoài vocab, nên "45.000 đồng" chỉ còn "đồng". Chuẩn hoá số đưa CER của câu tài chính về ngang câu thường.

Về nghe: lời giải mẫu do một agent tự động chạy và **không nghe được audio**, nên không có nhận xét bằng tai ở đây; phần đó
là của bạn (file `tts_*.wav` trong thư mục cache). Thay vào đó là hai đặc điểm đo được bằng số trên 20 câu FLEURS, so giọng
TTS với giọng người đọc cùng câu: giọng TTS nói nhanh hơn (trung vị 3.18 so với 2.51 âm tiết mỗi giây, tính
trên đoạn có tiếng), và tỉ lệ khung "lặng" giữa đoạn có tiếng cao hơn (0.32 so với 0.24, ngưỡng năng lượng 10% của p95
mỗi câu, khung 25 ms). Người đọc FLEURS đọc chậm và rõ, nên đây không phải chuẩn của giọng tự nhiên; con số chỉ để bạn biết
nghe vào đâu (nhịp, chỗ ngắt) khi tự nghe. Log: `.superpowers/scratch/logs/tts_prosody.log`. CER thấp chỉ nói Whisper nghe ra chữ, không nói giọng dễ chịu.

## Bẫy thường gặp

- Dùng `faster_whisper.decode_audio` trong env GPU: lỗi với PyAV đang ghim.
- Đọc WAV float32 như int16: ra nhiễu trắng mà không báo lỗi.
- So CER vòng TTS → STT mà không chuẩn hoá phía Whisper: Whisper viết "45.000", văn bản đầu vào viết chữ, CER bị thổi phồng.
- Không ghim seed của VITS: chạy lại ra audio khác.
