# Lời giải: CNN trên FashionMNIST

## Cách làm

- `standardize`: chia 255, trừ mean, chia std của **train** (0.2855 và 0.3528 trên 50 000 ảnh
  train), `unsqueeze(1)` để thêm chiều kênh. Tính thống kê trên cả train + test là leakage nhỏ,
  nhưng là thói quen xấu: ở production bạn không có test khi tính.
- `build_cnn`: `Conv(1→32) → ReLU → MaxPool → Conv(32→64) → ReLU → MaxPool → Flatten → Dropout →
  Linear(64·(s/4)², 128) → ReLU → Dropout → Linear(128, n)`. Tính số chiều sau `Flatten` từ
  `image_size` để cùng một hàm dùng cho ảnh test 8×8 và ảnh thật 28×28.
- `train_model`: vòng chuẩn của bài Basic 02; xáo bằng `torch.Generator().manual_seed(seed + epoch)`
  để mỗi epoch một thứ tự khác nhưng vẫn tái lập được.
- `predict`: `model.eval()` + `torch.no_grad()`, chia batch.
- `confusion_matrix`: `bincount` trên chỉ số `y_true * n + y_pred`.

## Kết quả thật

5 epoch, Adam lr 1e-3, batch 128, 50 000 ảnh train, CPU Intel i7-11800H dùng 8 luồng (máy đang chạy
việc khác, nên thời gian chỉ để so sánh tương đối):

| Model | Tham số | Thời gian train | Val accuracy | Test accuracy |
| --- | --- | --- | --- | --- |
| MLP 784-256-128-10, dropout 0.2 | 235 146 | 4 s | 0.8827 | 0.8768 |
| CNN 2 khối conv + 2 Linear | 421 642 | 52 s | 0.9085 | 0.9048 |

CNN hơn khoảng 2.8 điểm phần trăm test accuracy, tức giảm khoảng 23% số ảnh sai (từ 12.3% xuống
9.5%), nhưng chậm hơn khoảng 13 lần trên CPU. Trên GPU khoảng cách thời gian thu hẹp mạnh vì
convolution là phép toán GPU làm tốt nhất.

Bảng tham số cho thấy điều quan trọng: hai tầng conv chỉ có 18 816 tham số (320 + 18 496); 401 536
tham số nằm ở `Linear(3136, 128)`. Weight sharing làm conv rẻ; cái đắt là "trải phẳng" bản đồ đặc
trưng ra. Kiến trúc hiện đại thay `Flatten` bằng global average pooling vì lý do này.

Accuracy từng lớp của CNN: Shirt thấp nhất (0.678), sau đó T-shirt/top và Pullover (0.83); Sandal,
Sneaker, Bag, Trouser trên 0.97. Các cặp nhầm nhiều nhất: Shirt → Coat (116 ảnh), T-shirt/top →
Shirt (98), Pullover → Coat (97), Shirt → T-shirt/top (92). Mọi lỗi lớn đều nằm trong nhóm "áo
phần trên cơ thể", nơi ảnh 28×28 xám không giữ được chi tiết phân biệt.

## Mở rộng nếu muốn đi xa hơn

- Thêm `BatchNorm2d` sau mỗi conv và data augmentation (lật ngang, dịch 2 pixel), rồi đo lại trên
  validation xem được bao nhiêu điểm.
- Early stopping theo val loss bằng `fit` của bài Basic 02 thay cho 5 epoch cố định.
- Thay `Flatten` bằng `AdaptiveAvgPool2d(1)`: tổng tham số giảm khoảng 15 lần (421 642 xuống
  28 426), nhưng thường cần thêm khối conv để giữ accuracy.

## Bẫy thường gặp

- Quên `unsqueeze(1)`: `Conv2d` nhận `(N, C, H, W)`; tensor 3 chiều `(N, H, W)` bị hiểu là **một**
  ảnh không batch có N kênh, và lỗi báo về số kênh chứ không nói thiếu chiều.
- Đánh giá ở chế độ train: dropout bật, accuracy thấp hơn và thay đổi mỗi lần chạy.
- Chọn số epoch hay kiến trúc theo test accuracy.
- Đọc mỗi accuracy tổng: 90% che mất việc lớp Shirt chỉ đúng khoảng 2/3. Luôn xem theo lớp khi lỗi
  có giá khác nhau.
