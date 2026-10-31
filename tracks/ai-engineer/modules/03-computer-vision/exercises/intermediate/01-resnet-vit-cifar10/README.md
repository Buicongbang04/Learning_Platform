---
title: LeNet, ResNet và ViT tự dựng, train trên CIFAR-10
level: intermediate
services: []
files:
  - path: starter/cnn_vit.ipynb
    note: 13 hàm/lớp TODO
  - path: tests/test_cnn_vit.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py cifar10
  - uv run jupyter lab tracks/ai-engineer/modules/03-computer-vision/exercises/intermediate/01-resnet-vit-cifar10/starter/cnn_vit.ipynb
  - uv run pytest tracks/ai-engineer/modules/03-computer-vision/exercises/intermediate/01-resnet-vit-cifar10 -q
---

## Mục tiêu

Dựng lại ba thế hệ kiến trúc thị giác bằng PyTorch (LeNet-5, ResNet cho CIFAR với residual và BatchNorm, Vision
Transformer với attention tự viết), train chúng trong cùng một vòng train với cùng ngân sách, và đọc kết quả như một
kỹ sư: tham số, thời gian, accuracy, khoảng cách train/test, tác dụng của augmentation và của đường tắt residual.
Làm xong bạn giải thích được vì sao ResNet thay LeNet, và vì sao ViT nhiều tham số hơn mà vẫn thua ở quy mô nhỏ.

## Đề bài

**Phần cứng:** GPU 4GB · ~150 phút

Thời gian trên là thời gian làm bài. Thí nghiệm có hai cấu hình chọn tự động: env gốc (CPU) train 10 000 ảnh, 4 epoch
mỗi model, cả notebook khoảng 5 phút trên CPU 4 luồng của PC rảnh, 10–30 phút trên laptop tuỳ tải máy, đủ để kiểm code và thấy thứ bậc; kernel
`ai-gpu` train đủ 50 000 ảnh, 15 epoch, thêm thí nghiệm 56 tầng (bảng số đo ở mục 2 lý thuyết). Lần đầu tải CIFAR-10
(137 MB). Test chạy trên CPU với dữ liệu sinh trong test, vài giây.

Đọc mục 2 và 3 phần lý thuyết. Mở `starter/cnn_vit.ipynb`; dùng `nn.Conv2d`, `nn.BatchNorm2d` thoải mái (conv bằng
numpy bạn đã viết ở bài Basic 01), nhưng **attention phải tự viết**:

1. `load_cifar10`, `channel_stats`, `to_tensor`: đọc parquet, giải mã PNG, thống kê theo kênh, đổi NHWC uint8 sang NCHW
   float32 đã chuẩn hoá.
2. `random_crop_flip`: đệm 4 pixel số 0, cắt ngẫu nhiên 32×32 và lật ngang p = 0.5, riêng cho từng ảnh, mọi số ngẫu
   nhiên từ một `torch.Generator`.
3. `LeNet5`, `BasicBlock` (identity hoặc projection shortcut, cờ `residual` để dựng bản "plain"), `ResNetCifar(depth)`
   với $$depth = 6n + 2$$ và global average pooling.
4. `PatchEmbed`, `MultiHeadSelfAttention` (không dùng `nn.MultiheadAttention` hay `F.scaled_dot_product_attention`),
   `TransformerBlock` pre-norm, `ViT` với CLS token và position embedding học được.
5. `train` (AdamW + OneCycleLR theo bước, tái lập theo `seed`, trả loss trung bình theo mẫu mỗi epoch) và `evaluate`.

Rồi chạy các cell `explore`: số tham số của từng model, rồi 5 thí nghiệm cùng ngân sách (LeNet-5, Plain-20, ResNet-20,
ResNet-20 không augment, ViT), đường loss, và trên GPU thêm Plain-56 so với ResNet-56. Sau đó làm phần trắc nghiệm của
bài trong app.

## Tiêu chí đạt

- `channel_stats` đúng mean/std theo kênh; `to_tensor` đổi trục bằng hoán vị (pixel ở hàng 1, cột 2 vẫn ở đó), đúng
  chuẩn hoá; `random_crop_flip` cho ra đúng một crop (có thể lật) của ảnh đã đệm 0, khoảng một nửa số ảnh bị lật, mỗi
  ảnh một độ dịch, cùng seed ra cùng kết quả.
- `LeNet5` có 62 006 tham số; `BasicBlock` dùng identity khi không đổi shape và projection conv 1×1 + BN khi đổi, conv
  không bias, ReLU sau phép cộng; `ResNetCifar(20)` có 272 474 tham số, `ResNetCifar(56)` có 855 770, bản plain cùng số
  tham số, nhận ảnh cỡ bất kỳ.
- `PatchEmbed` là phép tuyến tính dùng chung trên từng patch, patch xếp theo hàng rồi cột; attention khớp
  `F.scaled_dot_product_attention` của PyTorch, hoán vị đồng biến, được tự viết; `ViT()` có 811 146 tham số và nhạy với
  thứ tự patch.
- `train` học được dữ liệu dễ sinh trong test (val accuracy ≥ 0.9), tái lập khi chạy lại với cùng seed,
  loss mỗi epoch là trung bình theo mẫu, kết thúc ở `eval()`; `evaluate` dùng running stats của BatchNorm.
- Trên CIFAR-10 thật: thống kê tập test khớp giá trị đã biết; LeNet-5 2 epoch trên 4 000 ảnh đạt ≥ 0.30 trong vòng một
  phút trên CPU.

## Gợi ý

### Gợi ý 1

Các test của mục 3 và 4 so với công thức chứ không so với số ngẫu nhiên: đặt tên thuộc tính đúng như đề (`conv1`, `bn1`,
`conv2`, `bn2`, `shortcut`, `proj`, `qkv`, `cls_token`, `pos_embed`), vì test đọc trọng số qua chúng. Với attention,
viết shape của từng tensor ra giấy trước: `(B, N, 3·D)` cần thành ba tensor `(B, heads, N, D/heads)`; thứ tự trục sai
vẫn chạy mà trộn các head với nhau.

### Gợi ý 2

Tính tái lập cần **mọi** số ngẫu nhiên đi qua cùng một generator: thứ tự xáo dữ liệu, độ dịch và cờ lật của augmentation.
Khởi tạo trọng số đã xảy ra trước khi `train` được gọi, nên `train` chỉ cần lo phần của nó. OneCycleLR đếm theo bước
optimizer, nên tổng số bước là số epoch nhân số batch mỗi epoch (batch cuối có thể thiếu).
