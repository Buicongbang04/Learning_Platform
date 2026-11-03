# Lời giải: hồ sơ Oxford-IIIT Pets và trimap

## Cách làm

- `list_trimaps` lọc theo tên (`._`) trước khi đọc. Thư mục giải nén có 14 780 tệp `*.png`, một nửa là AppleDouble; lọc theo tên rõ ràng hơn `try/except` quanh `Image.open` (cách đó nuốt luôn trimap hỏng thật).
- `trimap_profile` đếm pixel bằng `np.bincount`, chia cho diện tích.
- `image_table` chỉ đọc header ảnh (`Image.open(...).size` không decode pixel) nên 7 349 ảnh mất vài giây.
- `join_report` ghép theo `image_id`; `share_over` và `without_pet` là lọc đơn giản.

## Kết quả trên dữ liệu thật

| Chỉ số | Giá trị |
| --- | --- |
| Trimap hợp lệ / mọi tệp png | 7 390 / 14 780 |
| Ảnh trong mirror HF | 7 349 (train 3 680, test 3 669) |
| Ghép được / trimap không có ảnh / ảnh không có trimap | 7 349 / 41 / 0 |
| Kích thước lệch giữa ảnh và trimap | 0 |
| Tỉ lệ pixel trung bình: thú cưng / nền / viền | 30.0% / 58.2% / 11.8% |
| Trimap không có pixel thú cưng | 23 |
| Ảnh không phải RGB | 3 (RGBA) |
| Cạnh dài: trung vị, p99, max | 500, 636, 3 264 px |
| Cạnh dài > 500 / > 1024 px | 1.86% / 0.29% |

## Ý nghĩa cho service

- **Giới hạn kích thước**: 99% ảnh có cạnh dài ≤ 636 px; ảnh lớn nhất 3 264 px. Giới hạn 1024 px từ chối 0.3% ảnh của tập này; với ảnh điện thoại thật (4 000 px trở lên) tỉ lệ cao hơn nhiều, nên production thường resize phía client hoặc nhận ảnh lớn rồi thu nhỏ ngay khi decode (giới hạn byte của request vẫn phải có). Giới hạn dưới (cạnh ngắn nhất tập này là 103 px) chặn ảnh rác.
- **Mode**: có ảnh RGBA và PNG lẫn JPEG, nên service phải `convert("RGB")`; nếu không, tensor có 4 kênh và model báo lỗi shape.
- **Metric**: viền chỉ ~12% pixel, pixel accuracy có thể cao dù model bỏ hết viền. Dùng mIoU và IoU từng lớp.
- **Nhãn bẩn**: 23 trimap toàn nền là nhãn hỏng hoặc ảnh không thấy rõ con vật; nên loại khỏi tập đánh giá hoặc xem tay.
- **Resize mask**: mask là mã lớp, phóng to/thu nhỏ phải dùng nearest.

## Đáp án trắc nghiệm

- `trimap-count` b: 7 390 (14 780 nếu đếm cả `._*.png`).
- `unmatched` c: 41 trimap không có ảnh trong mirror HF; 7 349 là số ghép được.
- `pet-share` b: khoảng 30%.
- `over-500` b: khoảng 1.9%; 0.3% là ngưỡng 1024.
- `non-rgb` a: 3 ảnh RGBA.
- `appledouble` a: tệp metadata macOS; lọc theo tên rõ ràng, không che lỗi thật.
- `mask-resize` b: nearest, vì nội suy trộn mã lớp thành giá trị vô nghĩa (vd. 1.5).
- `metric` a, b: IoU từng lớp và mIoU nhạy với lớp hiếm; pixel accuracy bị lớp nền chiếm đa số chi phối; tỉ lệ HTTP 200 không nói gì về chất lượng.

## Rubric tự chấm

| Tiêu chí | Đạt khi |
| --- | --- |
| Test | Pass trên dữ liệu sinh và dữ liệu thật |
| Notebook | Chạy trọn vẹn, có `pets_profile.png` |
| Quyết định giới hạn | Nêu một giới hạn cạnh dài và tỉ lệ ảnh bị từ chối kèm số |
