---
title: Tiền xử lý media trước model đa phương thức
level: basic
services: []
files:
  - path: starter/media.py
    note: 5 hàm TODO
  - path: tests/test_media.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/18-multimodal/exercises/basic/03-media-preprocessing -q
---

## Mục tiêu

Phần lớn lỗi của ứng dụng đa phương thức nằm **trước** model: audio sai tần số lấy mẫu, video gửi quá nhiều frame, ảnh
quá to làm tiền token tăng gấp chục lần, message sai định dạng của nhà cung cấp. Bài này cho bạn viết năm hàm nhỏ mà các
bài sau dùng lại, mỗi hàm gắn với một con số đo được ở lý thuyết.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Trong `starter/media.py`:

1. `to_mono_float32(x) -> np.ndarray`: PCM `int16` chia 32768, `int32` chia $$2^{31}$$, `uint8` (có offset 128) thành
   `(x - 128) / 128`, số thực giữ nguyên giá trị; mảng `(n, ch)` trộn về mono bằng **trung bình** các kênh. Trả mảng
   1 chiều `float32`. Dtype khác hoặc mảng hơn 2 chiều thì `ValueError`.
2. `resample(x, sr_in, sr_out) -> np.ndarray`: đổi tần số lấy mẫu **có lọc chống aliasing** (Whisper cần 16 kHz, file
   thu âm thường 44.1 hoặc 48 kHz). Độ dài kết quả lệch $$\mathrm{len}(x)\cdot sr_{out}/sr_{in}$$ không quá 1 mẫu, kiểu
   `float32`; `sr_in == sr_out` trả bản sao; tần số không dương thì `ValueError`. Được dùng `scipy.signal`.
3. `sample_frame_indices(n_frames, fps, *, num=None, every_s=None) -> list[int]`: truyền **đúng một** trong hai tham số
   (không thì `ValueError`); `n_frames <= 0` trả `[]`.
   - `num`: chia video thành `num` đoạn bằng nhau, lấy frame ở **tâm** mỗi đoạn, chỉ số
     $$\lfloor (i + 0.5)\, n / \mathrm{num} \rfloor$$; `num >= n_frames` thì lấy mọi frame.
   - `every_s`: frame tại các thời điểm $$t = k\cdot \mathrm{every\_s}$$ còn nhỏ hơn độ dài video $$n / \mathrm{fps}$$,
     chỉ số $$\lfloor t \cdot \mathrm{fps} \rfloor$$ (cộng thêm $$10^{-9}$$ trước khi lấy sàn để tránh lỗi làm tròn số
     thực), bỏ trùng, tăng dần.
4. `vlm_image_tokens(width, height, *, factor=32, min_pixels=64*32*32, max_pixels=2048*32*32) -> int`: số token ảnh của
   họ Qwen-VL (mục 2 lý thuyết). Mỗi cạnh làm tròn (hàm `round` của Python) về bội của `factor` (tối thiểu `factor`); nếu
   diện tích vượt `max_pixels`, thu nhỏ đều với
   $$\beta = \sqrt{hw / \mathrm{max\_pixels}}$$ và lấy **sàn** $$\lfloor h/(\beta\cdot \mathrm{factor}) \rfloor\cdot \mathrm{factor}$$
   (tối thiểu `factor`); nếu nhỏ hơn `min_pixels`, phóng to với $$\beta = \sqrt{\mathrm{min\_pixels}/(hw)}$$ và lấy
   **trần**. Token là $$(h'/\mathrm{factor})\cdot(w'/\mathrm{factor})$$. Tỉ lệ cạnh dài/cạnh ngắn vượt 200 hoặc kích
   thước không dương thì `ValueError`. Mặc định ứng với `qwen3-vl:2b` trên Ollama (patch 16, gộp 2×2 patch thành một
   token, tức 32×32 pixel một token); `factor=28` là Qwen2.5-VL (patch 14).
5. `lc_user_message(text, images=(), audio=()) -> HumanMessage`: message của `langchain-core` 1.x dùng **content block
   chuẩn**: block `{"type": "text", "text": ...}` trước, rồi mỗi ảnh một block `{"type": "image", "base64": ...,
   "mime_type": ...}`, rồi mỗi audio một block `{"type": "audio", ...}` cùng dạng. `images`, `audio` là list
   `(bytes, mime)`; mime không bắt đầu bằng `image/` (hoặc `audio/`) thì `ValueError`.

## Tiêu chí đạt

- Âm thanh: thang đo đúng cho 4 kiểu dữ liệu, trộn kênh bằng trung bình; resample giữ nguyên tông 440 Hz và **lọc bỏ** tông
  10 kHz khi về 16 kHz.
- Frame: đúng chỉ số trên các ví dụ của test, kể cả fps lẻ 29.97 và khoảng lấy mẫu nhỏ hơn khoảng cách hai frame.
- Token ảnh khớp số đo thật trên Ollama của `qwen3-vl:2b` (9 cỡ ảnh) và Qwen2.5-VL (6 cỡ ảnh), không phụ thuộc chiều xoay.
- Message chuyển được sang định dạng OpenAI (`image_url` với data URL) và Ollama (`images`) bằng chính các hàm chuyển
  đổi của LangChain.

## Gợi ý

### Gợi ý 1

`scipy.signal.resample_poly(x, up, down)` lọc thông thấp rồi đổi tần số theo tỉ lệ nguyên $$\mathrm{up}/\mathrm{down}$$;
`fractions.Fraction(sr_out, sr_in)` rút gọn tỉ lệ (44 100 → 16 000 là 160/441). `np.interp` thì không lọc gì: thử nó
trên tông 10 kHz rồi nghe (hoặc in RMS) để thấy aliasing.

### Gợi ý 2

Với `vlm_image_tokens`, tự tính tay 1280×960 trước: 1280/32 = 40, 960/32 = 30. Rồi một ảnh 4000×3000: diện tích vượt
trần, nên $$\beta > 1$$. `math.floor`, `math.ceil` và `round` cho kết quả khác nhau đúng ở những cỡ ảnh test dùng. Kiểu
block xem trong `langchain_core.messages.content` (`ImageContentBlock`, `AudioContentBlock`).
