---
title: Whisper trên FLEURS tiếng Việt và vòng TTS → STT
level: intermediate
services: []
files:
  - path: starter/speech.ipynb
    note: 4 hàm dán từ Basic 01, 4 hàm TODO
  - path: tests/test_speech.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py fleurs-vi
  - uv run jupyter lab tracks/ai-engineer/modules/18-multimodal/exercises/intermediate/02-speech-stt-tts/starter/speech.ipynb
  - uv run pytest tracks/ai-engineer/modules/18-multimodal/exercises/intermediate/02-speech-stt-tts -q
---

## Mục tiêu

Đo speech-to-text như một kỹ sư: WER/CER tự viết, mức corpus, trên 50 câu tiếng Việt thật nhiều người đọc; thấy cỡ model,
beam search, VAD, cách chuẩn hoá và audio dài đổi con số thế nào, và trả giá bao nhiêu thời gian. Rồi làm chiều ngược lại:
sinh giọng nói tiếng Việt, đánh giá bằng vòng TTS → STT, và sửa lỗi lớn nhất của TTS tiếng Việt bằng một hàm đọc số tiền.

## Đề bài

**Phần cứng:** CPU · ~120 phút

Thời gian trên là thời gian làm bài. Mọi cell `explore` chạy trên CPU (4 luồng) trong env gốc của repo; toàn bộ notebook
lời giải mất khoảng 20 phút trên PC của track (máy dùng chung), lần đầu tải thêm khoảng 700 MB model Whisper và 139 MB model
TTS. Cell cuối (không chấm) đo lại trên GPU khi bạn mở notebook bằng kernel `ai-gpu` (`setup/gpu`).

Mở `starter/speech.ipynb`. Trong cell chấm điểm:

1. Dán bốn hàm của bài Basic 01.
2. `read_wav` (tự đọc WAV PCM 16 bit và float 32 bit từ `bytes`), `pinned_subset` (50 câu khác nhau đầu tiên của
   `test.tsv`), `read_number_vi` (số nguyên thành chữ theo cách đọc phổ thông), `normalize_for_tts` (số tiền trong câu thành
   chữ), theo mô tả trong notebook.

Rồi chạy các cell `explore`:

- `tiny`, `base`, `small` với beam 1 và 5, `small` thêm VAD: bảng WER, CER, thời gian, RTF;
- WER của cùng bản nhận dạng khi không chuẩn hoá, chỉ đổi chữ thường, và sau `normalize_vi`;
- 50 câu nối thành một audio khoảng 9 phút, nhận dạng một lần với ba cấu hình;
- TTS 20 câu FLEURS và 10 câu tài chính tự viết (có số tiền), Whisper nghe lại, CER trước và sau `normalize_for_tts`; lưu
  vài file WAV để bạn **nghe**.

Sau đó làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- Bốn hàm dán từ Basic 01 qua kiểm tra nhanh (khớp `jiwer`, mức corpus).
- `read_wav` đọc đúng float 32 bit và PCM 16 bit (khớp module `wave` của Python), trộn kênh bằng trung bình, bỏ qua chunk
  lạ kể cả chunk có kích thước lẻ, từ chối file không phải WAV và định dạng không hỗ trợ.
- `pinned_subset` giữ dòng đầu tiên của mỗi id câu, đúng thứ tự file.
- `read_number_vi` đúng 23 số mẫu (mốt, tư, lăm, linh, không trăm, nhóm bằng 0, số âm); `normalize_for_tts` đổi số tiền có
  đơn vị và số nguyên, giữ nguyên số thập phân.
- Cell `explore` chạy hết và in các bảng.

## Gợi ý

### Gợi ý 1

`struct.unpack("<4sI", data[pos:pos + 8])` đọc tên và kích thước một chunk. `np.frombuffer(body, dtype="<f4")` đọc float
32 bit little-endian không cần vòng lặp; `reshape(-1, channels)` tách kênh. Thử hàm trên một file bạn tự ghi bằng module
`wave` trước khi chạy test.

### Gợi ý 2

`read_number_vi`: viết một hàm đọc **ba chữ số** (có cờ "phải đọc đủ hàng trăm" khi nhóm không đứng đầu), rồi tách số thành
nhóm ba từ phải sang trái và ghép với "nghìn", "triệu", "tỷ", bỏ nhóm bằng 0. `normalize_for_tts`: một `re.sub` với hàm
thay thế; dùng lookahead/lookbehind để không bắt phần nguyên của "3.5".
