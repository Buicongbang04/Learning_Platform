# Lời giải: transfer learning trên Oxford-IIIT Pet

## Cách làm

**Dữ liệu.** `pd.read_parquet`, giữ ảnh ở dạng `bytes` (giải mã 7 349 ảnh vào RAM tốn vài GB), nhãn `int64`, `image_id`
dạng chuỗi. `class_names` lấy tên giống bằng `re.sub(r"_\d+$", "", image_id)` cho ví dụ đầu tiên của mỗi nhãn: chỉ bỏ hậu
tố số, giữ nguyên chữ hoa (giống mèo viết hoa, giống chó viết thường trong bộ gốc) và dấu gạch dưới bên trong.
`PetsDataset.__getitem__` giải mã bằng `Image.open(io.BytesIO(...)).convert("RGB")`: bộ dữ liệu có ảnh RGBA và ảnh xám,
thiếu `convert` thì transform hoặc model nhận sai số kênh.

**Transform.** Eval: `Resize(round(size / 0.875))` cạnh ngắn, `CenterCrop(size)`, `ToImage`, `ToDtype(float32,
scale=True)`, `Normalize` ImageNet. Train: `RandomResizedCrop(size, scale=(0.35, 1.0))`, `RandomHorizontalFlip()`, rồi
cùng ba bước cuối. Cùng `Normalize` cho train và eval là điều kiện bắt buộc: weights ImageNet chỉ "hiểu" input có thống kê
đó.

**Model.** `resnet18(weights=...)`, thay `fc` bằng `nn.Linear(512, C)` mới. `freeze_backbone` đặt `requires_grad` theo
tên tham số (`fc.` hay không). `set_bn_eval` đưa mọi `BatchNorm2d` về `eval()`; phải gọi **sau** `model.train()` vì
`train()` đặt lại mọi module con. `param_groups` gom theo cặp `(lr, weight_decay)`: tên bắt đầu `fc.` dùng `lr_head`;
`p.ndim == 1` (bias, γ/β của BN) thì weight decay 0; bỏ tham số không `requires_grad`, không tạo nhóm rỗng.

**Feature, train, evaluate.** `extract_features` tạm thay `model.fc` bằng `nn.Identity()` trong `try/finally`, chạy ở
`eval()` dưới `no_grad`, trả `(N, 512)` float32. `train_one_epoch` gọi `train()`, rồi `set_bn_eval` nếu `freeze_bn`,
cộng `loss.item() * len(y)` và chia tổng số mẫu, `scheduler.step()` ngay sau `optimizer.step()`. `evaluate` là
accuracy ở `eval()`.

## Kết quả thật

Oxford-IIIT Pet (mirror `timm/oxford-iiit-pet`): 3 680 ảnh train (93–100 ảnh mỗi giống), 3 669 ảnh test (ít nhất 88 mỗi
giống), 37 giống; 500 ảnh đầu có cạnh rộng trung vị 500 pixel, cao trung vị 375. Ảnh test đầu tiên sau transform eval:
`(3, 160, 160)`, mean −0.252, std 1.596 (Normalize theo thống kê ImageNet, không theo ảnh này).

ResNet-18 ảnh 160 px, batch 64, seed 0, PC RTX 3060 (kernel `ai-gpu`; GPU đang chạy song song một bài train khác):

| Chiến lược | Tham số được train | Loss train theo epoch | Test acc |
| --- | --- | --- | --- |
| Linear probe (logistic regression full-batch trên feature 512 chiều, 100 bước AdamW) | 18 981 | | **0.8626** |
| Linear probe, quên `Normalize` (chỉ chia 255) | 18 981 | | 0.7651 |
| Fine-tune toàn bộ 3 epoch (lr backbone 1e-4, head 1e-3, OneCycle, augmentation) | 11.2 triệu | 2.346, 0.597, 0.385 | **0.8708** |
| Train từ đầu 3 epoch (cùng kiến trúc, lr 1e-3) | 11.2 triệu | 3.549, 3.261, 2.937 | 0.2011 |
| Đoán ngẫu nhiên | | | 0.0270 |

Đọc kết quả:

- **Linear probe là baseline rất mạnh**: một tầng Linear trên feature ImageNet đạt 86%. Trích feature 7 349 ảnh là phần
  tốn thời gian (hai phút trên GPU dùng chung, phần lớn là giải mã JPEG), train head chỉ vài giây và có thể thử lại hàng
  chục lần.
- **Fine-tune 3 epoch chỉ hơn probe 0.8 điểm** (khoảng 30 ảnh trên 3 669): một lần chạy một seed không đủ để nói fine-tune
  tốt hơn; cần nhiều epoch hơn và vài seed. Với ngân sách nhỏ, probe là lựa chọn đúng.
- **Quên Normalize mất gần 10 điểm** dù backbone, head và dữ liệu y hệt: feature ImageNet được học trên input có mean 0,
  std 1 theo kênh; input `[0, 1]` dịch toàn bộ phân phối activation của tầng đầu. Đây là dạng train/serve skew rẻ nhất
  để mắc và đắt nhất để tìm nếu không có phép đo đối chứng.
- **Từ đầu: 20% sau 3 epoch**, loss 2.94 vẫn chưa xa mức đoán mò $$\ln 37 \approx 3.61$$. Khoảng 100 ảnh mỗi lớp là quá ít để
  học feature thị giác từ số 0 trong ngân sách này.

Env gốc (CPU 4 luồng, nbconvert cả notebook 751 s trên PC Xeon rảnh) chạy đúng cấu hình này: probe 0.8626, quên Normalize
0.7653, fine-tune 0.8694, từ đầu 0.2020, chỉ lệch GPU ở chữ số thứ ba (thứ tự cộng khác). Laptop CPU chậm hơn nhiều lần.

## Bẫy thường gặp

- Normalize bằng thống kê của chính bộ dữ liệu, hoặc quên Normalize: backbone pretrain nhìn thấy phân phối input khác lúc
  train ImageNet; linear probe tụt rõ (bảng trên).
- Đóng băng bằng `requires_grad = False` mà để BatchNorm ở chế độ train: running mean/var trôi theo dữ liệu mới, feature
  của backbone "đóng băng" vẫn đổi.
- Một lr chung cho cả model: lr đủ lớn cho head mới thì phá feature pretrain trong vài trăm bước; lr đủ nhỏ cho backbone
  thì head học quá chậm.
- Lật dọc hoặc xoay mạnh ảnh thú nuôi: dạy model những ảnh không bao giờ gặp.
- Đo "fine-tune tốt hơn probe" trên một seed và một tập test nhỏ rồi kết luận: chênh lệch dưới 1 điểm thường nằm trong
  dao động giữa các lần chạy.
