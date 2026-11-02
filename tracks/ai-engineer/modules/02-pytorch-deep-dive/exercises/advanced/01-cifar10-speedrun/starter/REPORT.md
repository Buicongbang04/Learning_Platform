# CIFAR-10 speedrun trên GPU 4GB

TODO: viết theo khung trong README của bài (ít nhất 700 từ). Người đọc là nhà tuyển dụng hoặc đồng nghiệp chưa xem
code: họ cần biết bạn đạt gì, trên phần cứng nào, nhờ đâu, và bạn đo ra sao.

## Tóm tắt

TODO: 3–4 câu có số: test accuracy, thời gian train, peak memory, GPU, và thay đổi nào đóng góp nhiều nhất.

## Thiết lập

TODO: model (kiến trúc, số tham số), dữ liệu và augmentation, optimizer, lịch lr, batch, số epoch, dtype, seed, phần cứng
(GPU, driver, phiên bản torch), cách đo thời gian (có `synchronize` không, tính những gì) và peak memory.

## Kết quả chính

TODO: test accuracy (có/không TTA) qua ít nhất 3 seed (trung bình, min, max), thời gian, peak memory. Đường loss.

## Ablation

TODO: bảng: mỗi dòng bỏ MỘT thành phần (AMP, channels_last, dữ liệu nằm trên GPU so với DataLoader, label smoothing,
TTA, lịch lr...), cùng ngân sách epoch; cột thời gian, peak memory, test acc. Diễn giải: cái gì làm nhanh, cái gì làm
chính xác, chênh lệch nào nằm trong dao động seed.

## Profiler

TODO: đọc trace của vài bước: GPU có chờ không, top kernel theo thời gian, có kernel đổi layout không, op nào cấp phát
nhiều nhất. Một hình hoặc bảng.

## Lỗi và ngõ cụt

TODO: ít nhất 2 thứ đã thử mà không ăn thua hoặc gây lỗi (OOM, NaN, chậm đi), triệu chứng, cách bạn phát hiện, bài học.

## Giới hạn và bước tiếp theo

TODO: kết quả này nói gì và không nói gì (một GPU, một bộ dữ liệu nhỏ, GPU dùng chung...), bạn sẽ thử gì tiếp
(`torch.compile`, kiến trúc khác, batch lớn hơn...).
