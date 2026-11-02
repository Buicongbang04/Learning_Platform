# Segmentation người đi bộ trên Penn-Fudan: U-Net từ đầu, encoder pretrain, YOLO-seg

TODO: viết theo khung trong README của bài (ít nhất 600 từ). Người đọc chưa xem code: họ cần biết model nào tốt hơn,
hơn bao nhiêu, có chắc không, và mask chạy ra sao trên khung hình thật.

## Tóm tắt

TODO: 3–4 câu có số: mIoU và IoU lớp người trên 34 ảnh val ở độ phân giải gốc của từng cấu hình, ms/ảnh của
`predict_mask`, cấu hình bạn chọn và vì sao.

## Dữ liệu

TODO: Penn-Fudan (nguồn, giấy phép, số ảnh), mask gộp mọi người thành lớp 1, cách chia train/val (giống bài Advanced 01,
seed), `joint_transform` (augmentation nào, vì sao giữ nhãn). Một hình batch sau augmentation có mask chồng lên ảnh.

## Cấu hình

TODO: ba cấu hình so sánh: U-Net từ đầu, U-Net với encoder pretrain (encoder nào, decoder ra sao), YOLO11n-seg zero-shot
(conf, cách gộp mask). Với mỗi cấu hình: số tham số, upsample bằng gì, loss, optimizer, lịch lr, epoch, `size`, seed, phần
cứng, VRAM và thời gian train. Bảng kết quả: IoU nền, IoU người, mIoU. Đường loss.

## Ablation và dao động giữa các seed

TODO: ít nhất 2 thay đổi, mỗi lần một thứ, cùng ngân sách (bỏ Dice, bỏ augmentation, bỏ pretrain, đổi `size`...). Dao
động giữa ít nhất 2–3 seed ở cấu hình chính. Chênh lệch nào lớn hơn dao động, chênh lệch nào không?

## Serve và độ trễ

TODO: `predict_mask` làm gì để không lệch với lúc eval (BGR, chuẩn hoá, resize, `eval()`, nội suy logits), ms/ảnh theo
thiết bị (warmup, số lần đo, máy có bận không). Hình mask dự đoán trên vài ảnh val, cả tốt lẫn tệ.

## Lỗi và ngõ cụt

TODO: ít nhất 2 thứ đã thử mà không ăn thua hoặc gây lỗi (mask lệch ảnh, nội suy mask sinh nhãn lạ, BGR/RGB, OOM...),
triệu chứng, cách phát hiện, bài học.

## Giới hạn và bước tiếp theo

TODO: tập val 34 ảnh, semantic chứ không instance, ảnh ban ngày... Bạn sẽ thử gì tiếp (instance segmentation, SAM để
gán nhãn thêm, export, chạy trong app của bài Advanced 01).
