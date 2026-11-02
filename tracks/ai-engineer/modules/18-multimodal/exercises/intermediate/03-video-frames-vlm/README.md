---
title: Video understanding bằng chọn frame và vision LLM
level: intermediate
services: []
files:
  - path: starter/video.ipynb
    note: 6 hàm TODO
  - path: tests/test_video.py
    note: Không sửa
run:
  - ollama pull qwen3-vl:2b
  - uv run jupyter lab tracks/ai-engineer/modules/18-multimodal/exercises/intermediate/03-video-frames-vlm/starter/video.ipynb
  - uv run pytest tracks/ai-engineer/modules/18-multimodal/exercises/intermediate/03-video-frames-vlm -q
---

## Mục tiêu

Hiểu video understanding với model nhỏ thực chất là bài toán **chọn frame**: bao nhiêu frame, frame nào, độ phân giải
bao nhiêu, gửi riêng hay ghép lưới. Bạn đo đánh đổi giữa độ đúng, số token và độ trễ trên video có đáp án biết trước, và
thấy loại câu hỏi nào không cách lấy mẫu thưa nào trả lời được.

## Đề bài

**Phần cứng:** GPU 4GB · ~75 phút

Thời gian trên là thời gian làm bài; phần gọi model (30 lượt, mỗi lượt 1 tới 30 ảnh) mất khoảng 1.5 phút trên GPU của PC
track (RTX 3060, dùng chung); chưa đo trên laptop GPU 4GB. Chỉ có CPU: mỗi lượt có thể mất vài phút (mục 2 lý thuyết đo một ảnh 640×480 mất khoảng 20 giây
với 4 luồng); giữ `"đều 4 frame"` và `"lưới 4x4"`, đổi chiều rộng frame xuống 224.

Video thử do notebook tự sinh bằng OpenCV (không có media bản quyền nào trong repo), ghi ra thư mục tạm của hệ điều hành.

Mở `starter/video.ipynb`. Trong cell chấm điểm viết `read_frames`, `scene_change_indices`, `segment_middles`,
`tile_grid`, `video_messages`, `score_answers` theo mô tả trong notebook. Rồi chạy các cell `explore`:

- sinh 5 video (seed 0 tới 4), xem frame và đáp án;
- so 6 cách chọn frame: đều 4, 8, 16 frame; mỗi giây một frame; theo đổi cảnh; lưới 4×4 của 16 frame đều. Bảng: tỉ lệ
  đúng từng câu, tổng số câu đúng trên 30, số frame, token, độ trễ;
- đếm số "cảnh" mà bộ phát hiện đổi cảnh tìm được so với số cảnh thật.

Sau đó làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `read_frames` trả frame RGB `uint8` theo đúng thứ tự chỉ số được hỏi (kể cả lặp lại).
- `scene_change_indices` tính chênh lệch bằng số thực (không tràn `uint8`), chỉ nhận khi **lớn hơn** ngưỡng, luôn có frame 0.
- `segment_middles`, `tile_grid` (điền theo hàng, ô thừa đen), `video_messages` (đúng câu thời điểm, prefill `"{"`) khớp test.
- `score_answers` so đúng kiểu: bool không được tính là số, chuỗi so sau chuẩn hoá, thiếu khoá là sai.
- Cell `explore` chạy hết và in bảng so sánh.

## Gợi ý

### Gợi ý 1

`np.abs(gray[1:] - gray[:-1])` trên mảng `uint8` cho kết quả sai mà không báo lỗi ($$10 - 200$$ thành 66): đổi kiểu
trước. `np.flatnonzero` trả chỉ số của hiệu, lệch một so với chỉ số frame.

### Gợi ý 2

Với `tile_grid`, số hàng là $$\lceil n / \mathrm{cols} \rceil$$, frame thứ $$k$$ ở hàng $$k$$ chia nguyên `cols`, cột
$$k$$ mod `cols`. Với `score_answers`, nhớ trong Python `True == 1` và `isinstance(True, int)` đều đúng: kiểm `bool`
**trước** `int`.
