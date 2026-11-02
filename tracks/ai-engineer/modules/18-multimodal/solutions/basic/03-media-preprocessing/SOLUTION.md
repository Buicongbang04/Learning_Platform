# Lời giải: tiền xử lý media

## Cách làm

- `to_mono_float32`: chọn hệ số theo `dtype` (`int16` chia 32768, `int32` chia $$2^{31}$$, `uint8` trừ 128 rồi chia 128),
  `float` thì `astype(np.float32)`; mảng 2 chiều lấy `mean(axis=1)`.
- `resample`: `Fraction(sr_out, sr_in)` rút gọn tỉ lệ, `scipy.signal.resample_poly(x, p, q)`. Hàm này chèn $$p - 1$$ số 0
  giữa các mẫu, lọc bằng bộ lọc FIR thông thấp (cửa sổ Kaiser) có tần số cắt ở Nyquist nhỏ hơn trong hai tần số, rồi
  giữ một mẫu mỗi $$q$$.
- `sample_frame_indices`: `num` thì `int((i + 0.5) * n / num)`; `every_s` thì duyệt $$k = 0, 1, \dots$$ khi
  $$k\cdot\mathrm{every\_s} < n/\mathrm{fps}$$, gom vào `set` để bỏ trùng.
- `vlm_image_tokens`: đúng thuật toán `smart_resize` của Qwen-VL, trả tích hai cạnh chia cho `factor`.
- `lc_user_message`: dựng list dict theo thứ tự text, ảnh, audio; `base64.b64encode(data).decode("ascii")`.

## Vì sao các lựa chọn này

- **Chống aliasing.** Tín hiệu 10 kHz lấy mẫu ở 16 kHz không thể giữ nguyên: Nyquist mới là 8 kHz. Không lọc thì nó gập
  về $$16 - 10 = 6$$ kHz, một âm có thật trong dải nghe, lẫn vào giọng nói. Đo trên tông 10 kHz biên độ 0.8 (RMS 0.57) từ
  44.1 kHz về 16 kHz: `np.interp` còn RMS 0.48, gần trọn năng lượng chuyển sang 6 kHz; `resample_poly` còn 0.0008. Audio thu bằng điện thoại có nhiều năng lượng trên 8 kHz
  (tiếng xì, tiếng ồn), nên đây không chỉ là chuyện lý thuyết.
- **Trung bình kênh** chứ không lấy kênh trái: bản ghi cuộc gọi hay đặt mỗi người một kênh, lấy một kênh là mất nửa hội thoại.
- **Frame ở tâm đoạn** thay vì đầu đoạn: frame 0 của video thường là màn hình đen hoặc logo; tâm đoạn tránh cả hai đầu
  và chia đều thời lượng. `np.linspace(0, n - 1, num)` cũng hay gặp, nó lấy cả frame đầu lẫn cuối.
- **Đếm token trước khi gửi.** Ảnh 4000×3000 từ điện thoại và ảnh 1000×750 cùng một hoá đơn có thể chênh hai lần số token
  (2 028 so với 713 với `qwen3-vl:2b`); với API tính tiền theo token, bạn trả gấp đôi mà chưa chắc đọc đúng hơn (bài
  Intermediate 01 đo). Hàm này cho phép đặt ngân sách token trước khi gọi.
- **Content block chuẩn** thay vì định dạng của một nhà cung cấp: cùng message chuyển được sang OpenAI (`image_url` với
  data URL, `input_audio`) và Ollama (`images`) bằng hàm của LangChain; đổi nhà cung cấp không phải sửa code dựng message.

## Bẫy thường gặp

- Chia `int16` cho 32767: sai số nhỏ nhưng làm `-32768` thành $$-1.00003$$, vượt khoảng $$[-1, 1]$$ mà một số model kiểm.
- Coi `uint8` là có dấu: WAV 8 bit lưu không dấu với 128 là im lặng.
- `round` trong nhánh thu nhỏ: ảnh có thể vượt `max_pixels` (2560×1440 ra 2 040 token thay vì 1 980 đúng như Ollama đếm).
- Gửi ảnh qua `url` cho ChatOllama: LangChain 1.6 báo `ValueError`, Ollama chỉ nhận base64; với audio, ChatOllama báo
  "Blocks of type audio not supported".
