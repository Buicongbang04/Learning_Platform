# Detector người đi bộ: fine-tune YOLO trên Penn-Fudan và app webcam

TODO: viết theo khung trong README của bài (ít nhất 600 từ). Người đọc là nhà tuyển dụng hoặc đồng nghiệp chưa xem
code: họ cần biết detector tốt tới đâu so với model có sẵn, chạy nhanh cỡ nào trên phần cứng nào, và bạn đo ra sao.

## Tóm tắt

TODO: 3–4 câu có số: AP50 và AP50-95 trên 34 ảnh val (zero-shot so với fine-tune, kèm độ bất định), ms/khung và FPS
của app trên phần cứng nào, và kết luận: fine-tune có đáng không.

## Dữ liệu

TODO: Penn-Fudan (nguồn, giấy phép, số ảnh, số người), quy ước hộp bạn dùng, cách chia train/val (seed), bạn đã kiểm
nhãn sinh ra thế nào (một hình vẽ ngược nhãn lên ảnh).

## Huấn luyện

TODO: model, weights khởi đầu, `imgsz`, batch, epoch, augmentation, seed, phần cứng (GPU, VRAM dùng), thời gian train.
Đường loss/mAP theo epoch (hình). Biến thể bạn thử và lý do.

## Kết quả

TODO: bảng trên cùng 34 ảnh val, cùng bộ đánh giá: zero-shot so với fine-tune (và biến thể), AP50, AP50-95,
precision/recall ở ngưỡng conf của app; độ bất định (bootstrap theo ảnh hoặc nhiều seed). Ảnh val có hộp dự đoán.
Phân tích lỗi: false positive và false negative điển hình, cái nào là lỗi nhãn.

## Độ trễ và app

TODO: bảng ms/khung của model theo thiết bị và `imgsz` (có warmup, bao nhiêu lần đo, máy có đang bận không); FPS của cả
vòng app và phần nào tốn thời gian ngoài model. Cách chạy app (webcam, tệp video, thư mục ảnh), ảnh chụp hoặc video.

## Lỗi và ngõ cụt

TODO: ít nhất 2 thứ đã thử mà không ăn thua hoặc gây lỗi, triệu chứng, cách phát hiện, bài học.

## Giới hạn và bước tiếp theo

TODO: kết quả này nói gì và không nói gì (tập val nhỏ, ảnh đường phố ban ngày, một lớp...), bạn sẽ làm gì tiếp (thêm
dữ liệu thật từ camera, tracker, export ONNX/TensorRT, INT8...).
