# Lời giải: video understanding bằng chọn frame

## Cách làm

- `read_frames`: mở reader một lần, `get_data(i)` cho từng chỉ số theo thứ tự được hỏi, `finally: reader.close()`.
- `scene_change_indices`: `gray.astype(np.float32)` trước khi trừ, `np.abs(gray[1:] - gray[:-1]).mean(axis=(1, 2))`,
  `np.flatnonzero(diffs > threshold) + 1`, ghép `[0]` ở đầu.
- `segment_middles`: điểm cuối mỗi đoạn là đầu đoạn kế tiếp (đoạn cuối: `n_frames`), lấy `(s + e - 1) // 2`.
- `tile_grid`: `rows = ceil(n / cols)`, mảng 0 cỡ `(rows*h, cols*w, c)`, frame $$k$$ vào ô `divmod(k, cols)`.
- `video_messages`: câu thời điểm `", ".join(f"{t:.1f}s" ...)`, prefill `"{"`.
- `score_answers`: kiểm `bool` trước số; số chấp nhận `float(got) == want` (chuỗi số được), từ chối `bool`; chuỗi so sau
  `strip().lower()`.

## Kết quả của lời giải mẫu

5 video (seed 0 tới 4), `qwen3-vl:2b`, PC của track; toàn bộ notebook chạy khoảng 1.5 phút. Log:
`.superpowers/scratch/logs/int03_solution_outputs.log`, dự đoán thô của vài lượt: `int03_debug_preds.log`.

| Cách chọn | Frame | Token prompt TB | Giây p50 | scene_count | first_shape | last_number | has_red_triangle | ball_direction | flash_count | Đúng / 30 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| đều 4, rộng 448 | 4 | 608 | 1.02 | 0.0 | 0.4 | 0.0 | 0.4 | 0.4 | 0.2 | 7 |
| đều 8, rộng 448 | 8 | 1 098 | 1.43 | 0.0 | 0.8 | 0.0 | 0.4 | 0.4 | 0.0 | 8 |
| đều 16, rộng 448 | 16 | 2 080 | 2.22 | 0.0 | 0.8 | 0.2 | 0.4 | 0.4 | 0.0 | 9 |
| mỗi giây 1, rộng 320 | 30 | 2 417 | 2.50 | 0.0 | 1.0 | 0.0 | 0.4 | 0.4 | 0.0 | 9 |
| theo đổi cảnh, rộng 448 | 7.2 | 1 000 | 1.24 | 0.0 | 0.8 | 0.0 | 0.4 | 0.4 | 0.2 | 9 |
| lưới 4×4 của 16 frame đều | 16 | 1 236 | 1.38 | 0.0 | 0.8 | 0.2 | 1.0 | 0.4 | 0.2 | 13 |

Đọc bảng (30 câu mỗi dòng: chênh 1 tới 2 câu là nhiễu; câu trả lời của model còn đổi nhẹ giữa các lần chạy):

- **Model 2B là nút thắt, không phải cách chọn frame.** Đọc dự đoán thô: model đếm thiếu cảnh (3 hoặc 4 thay vì 4 hoặc 5),
  trả `last_number` là số của **cảnh đầu** (89 khi đáp án 22), và luôn trả `left_to_right`. `ball_direction` 0.4 ở mọi
  dòng đúng bằng tỉ lệ video có bóng chạy trái sang phải: model không suy luận được chuyển động qua nhiều ảnh. Đây là giới
  hạn đã biết của vision LLM nhỏ khi nhận nhiều ảnh: chúng mô tả từng ảnh khá tốt nhưng yếu ở so sánh và đếm xuyên ảnh.
- **Lưới 4×4 tốt nhất** (13/30) với 59% token của 16 frame riêng: trên một ảnh lưới, model thấy cả 16 thời điểm cùng lúc
  và trả lời đúng `has_red_triangle` ở 5/5 video, trong khi mọi cách gửi ảnh riêng đều chỉ đúng 2/5 (luôn trả `False`).
- **Thêm frame không cứu được**: 30 frame (mỗi giây một) tốn gần 4 lần token của 4 frame mà chỉ hơn 2 câu.
- **`flash_count`** gần như không bao giờ đúng: loé dài 0.3 giây, 16 frame đều cách nhau gần 2 giây.
- **Bộ phát hiện đổi cảnh** cho 5 tới 9 đoạn trên video có 4 hoặc 5 cảnh: mỗi lần loé trắng tạo thêm hai ranh giới (vào và
  ra). Với câu "có bao nhiêu cảnh" thì đó là lỗi; với câu "có lần loé nào không" thì đó lại là tín hiệu tốt, nhưng phải
  đếm bằng code chứ không nhờ LLM đếm.

Kết luận thực tế: với model 2B, câu hỏi về **nội dung một khoảnh khắc** (hình gì, màu gì) dùng được; câu hỏi về **thứ tự,
số lượng, chuyển động** cần công cụ chạy trên mọi frame (đổi cảnh, phát hiện chuyển động, OCR từng frame) rồi đưa **kết
quả có cấu trúc** cho LLM, hoặc một model lớn hơn có hỗ trợ video gốc. Đo lại trên PC 12GB với model lớn hơn là phần mở
rộng đáng làm.

## Bẫy thường gặp

- Trừ hai ảnh `uint8`: $$10 - 200$$ thành 66, đổi cảnh tối thành sáng bị bỏ sót.
- `np.flatnonzero` cho chỉ số của **hiệu**: quên cộng 1 là lệch một frame.
- `isinstance(True, int)` đúng: chấm `True` là số 1.
- Không đóng reader: video dài giữ file và bộ giải mã mở.
