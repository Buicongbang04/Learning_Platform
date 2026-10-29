---
title: CNN trên FashionMNIST
level: intermediate
services: []
files:
  - path: starter/fashion_cnn.ipynb
    note: 6 hàm TODO (build_mlp có sẵn làm mẫu)
  - path: tests/test_fashion_cnn.py
    note: Không sửa
run:
  - uv run jupyter lab tracks/data-science/modules/13-deep-learning/exercises/intermediate/01-fashion-cnn/starter/fashion_cnn.ipynb
  - uv run pytest tracks/data-science/modules/13-deep-learning/exercises/intermediate/01-fashion-cnn -q
---

## Mục tiêu

Dựng trọn một pipeline phân loại ảnh bằng PyTorch thuần: chuẩn hoá đúng cách, CNN có kích thước
linh hoạt, train có seed, dự đoán theo batch, đọc confusion matrix. Thấy bằng số thật trên CPU vì
sao CNN thắng MLP trên ảnh, và cái giá về thời gian.

## Đề bài

Mở `starter/fashion_cnn.ipynb`. Cell `explore` đầu tiên tải FashionMNIST vào
`data/raw/fashion-mnist` (khoảng 30 MB, chỉ lần đầu) và tách 10 000 ảnh cuối của tập train làm
validation.

1. `standardize(images, mean=None, std=None)`: `uint8 (N, H, W)` thành `float32 (N, 1, H, W)` đã
   chuẩn hoá; thống kê lấy từ tập train và dùng lại cho validation/test.
2. `build_cnn(image_size, n_classes, channels=(32, 64), dropout=0.3)`: hai khối
   conv-ReLU-maxpool rồi hai tầng Linear, chạy được với mọi `image_size` chia hết cho 4
   (`ValueError` nếu không). `build_mlp` có sẵn làm mẫu.
3. `count_params(model)`: số tham số train được.
4. `train_model(model, X, y, epochs, lr, batch_size, seed) -> list[float]`: Adam,
   cross-entropy, xáo thứ tự mỗi epoch bằng generator có seed, trả loss trung bình theo mẫu từng
   epoch.
5. `predict(model, X, batch_size)`: nhãn dự đoán, chế độ eval, theo batch.
6. `confusion_matrix(y_true, y_pred, n_classes)`: hàng là nhãn thật, cột là dự đoán.

Chạy các cell `explore` để train MLP và CNN 5 epoch trên 50 000 ảnh, rồi trả lời ba câu hỏi ở cuối
notebook. Train CNN mất khoảng một phút trên CPU laptop 8 luồng.

## Tiêu chí đạt

- `standardize` cho mean 0, std 1 trên train; validation/test dùng lại đúng mean, std của train.
- Cả MLP và CNN cho logits `(N, n_classes)` với ảnh 8×8 và 28×28; CNN có ít nhất 2 `Conv2d` và
  có dropout; `build_cnn(30, 10)` báo `ValueError`.
- `count_params` bỏ qua tham số đã đóng băng.
- Hai lần train cùng seed cho cùng dãy loss; `predict` không phụ thuộc cỡ batch dù model đang ở
  chế độ train khi gọi.
- CNN đạt trên 90% trên ảnh giả 8×8 (vạch ngang, dọc, hai đường chéo ở vị trí ngẫu nhiên, có nhiễu).
- Trên FashionMNIST thật (cell `explore`): CNN khoảng 90% test, MLP khoảng 88%.

## Gợi ý

### Gợi ý 1

Sau `Conv2d(kernel_size=3, padding=1)` kích thước ảnh giữ nguyên; mỗi `MaxPool2d(2)` chia đôi. Vậy
sau hai khối, mỗi kênh còn `(image_size // 4) ** 2` giá trị, và tầng Linear đầu tiên nhận
`channels[1] * (image_size // 4) ** 2` đầu vào.

### Gợi ý 2

`confusion_matrix` không cần vòng lặp: mã hoá mỗi cặp thành `y_true * n_classes + y_pred`, đếm bằng
`torch.bincount(..., minlength=n_classes ** 2)`, rồi `view(n_classes, n_classes)`.
