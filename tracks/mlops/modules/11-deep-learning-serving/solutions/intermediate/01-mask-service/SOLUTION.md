# Lời giải: service trả mask PNG

## Cách làm

- **Lifespan** tạo `InferenceSession` một lần. Tạo session tốn hàng trăm ms tới vài giây với model thật (đọc tệp, tối ưu graph, cấp phát arena, trên GPU còn khởi tạo CUDA context); tạo mỗi request vừa chậm vừa làm bộ nhớ GPU phân mảnh.
- **Kiểm tra theo thứ tự rẻ tới đắt**: đếm byte (không decode), mở header PIL (rẻ), so kích thước, rồi mới resize và chạy model. Ảnh 20 000×20 000 px vượt `MAX_SIDE` bị từ chối trước khi decode pixel; nếu decode trước, một request có thể chiếm hàng GB RAM (decompression bomb, PIL cũng có `Image.MAX_IMAGE_PIXELS` cho việc này).
- **Mã lỗi**: 413 cho payload quá lớn, 400 cho dữ liệu không phải ảnh, 422 cho ảnh hợp lệ nhưng ngoài hợp đồng. Client phân biệt được "gửi sai thứ" và "ảnh không hợp lệ".
- **Tiền xử lý** phải khớp lúc train từng chi tiết: RGB, bilinear, `/255`, `MEAN`/`STD`, NCHW. Đổi một chi tiết (vd. quên chuẩn hoá) không gây lỗi, chỉ làm mask tệ đi: đây là training-serving skew của model ảnh.
- **Hậu xử lý**: argmax ở độ phân giải model rồi phóng mask bằng **nearest**. Phóng logits bằng bilinear rồi mới argmax cho biên mịn hơn nhưng tốn bộ nhớ gấp số lớp; đó là đánh đổi có chủ đích, không phải sửa tuỳ tiện.
- **`X-Model-Version` trên mọi response**: khi canary hay rollback, log của client và của service ghép được kết quả nào do model nào sinh ra; `/healthz` chỉ nói model đang nạp **bây giờ**.
- `run_in_threadpool`: `session.run` là lời gọi C++ chặn; chạy thẳng trong `async def` sẽ chặn event loop, request khác (kể cả `/healthz`) phải chờ.

## Rubric tự chấm

| Tiêu chí | Đạt khi |
| --- | --- |
| Test | Pass |
| Thứ tự kiểm tra | Giải thích được vì sao kích thước kiểm trên header, trước khi decode và resize |
| Version | Nêu được tình huống cần `model_version` trên từng response |
