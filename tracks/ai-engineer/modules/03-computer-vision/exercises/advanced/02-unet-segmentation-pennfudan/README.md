---
title: U-Net segmentation người đi bộ, encoder pretrain và hàm serve không lệch (portfolio)
level: advanced
services: []
files:
  - path: starter/segment.ipynb
    note: 4 hàm/lớp API, thí nghiệm do bạn thiết kế
  - path: starter/REPORT.md
    note: Báo cáo portfolio
  - path: tests/test_segment.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py penn-fudan
  - uv run jupyter lab tracks/ai-engineer/modules/03-computer-vision/exercises/advanced/02-unet-segmentation-pennfudan/starter/segment.ipynb
  - uv run pytest tracks/ai-engineer/modules/03-computer-vision/exercises/advanced/02-unet-segmentation-pennfudan -q
---

## Mục tiêu

Tự dựng và train một mạng semantic segmentation trên dữ liệu thật, rồi trả lời bằng số đo câu hỏi mà mọi dự án
segmentation nhỏ gặp: với 136 ảnh có mask, train từ đầu, dùng encoder pretrain, hay lấy luôn một model có sẵn? Bạn
cũng viết hàm serve nhận khung hình OpenCV cỡ bất kỳ và trả mask đúng độ phân giải gốc, thứ hay hỏng âm thầm nhất
khi đưa model segmentation vào sản phẩm. Kết quả và `REPORT.md` là một bài portfolio.

## Đề bài

**Phần cứng:** GPU 4GB · ~360 phút

Thời gian trên là thời gian làm bài (thiết kế, thí nghiệm, báo cáo). Một lần train U-Net 60 epoch ở 256×256 trên 136
ảnh mất vài phút trên GPU 4GB (dưới 2 GB VRAM với batch 8); cả bài cần khoảng 30–60 phút GPU cho các lần chạy và
ablation. Không có GPU: train ở `size=128`, `base=16`, 30 epoch trên CPU (vài chục phút) vẫn đủ để so thứ bậc; ghi rõ
cấu hình. Test chạy trên CPU, không tải gì.

Đọc mục 6 phần lý thuyết (U-Net, mIoU, Dice) và mục 7 (train/serve skew). Mở `starter/segment.ipynb`:

1. Cài bốn API mà test gọi: `joint_transform` (augmentation hình học áp **cùng một phép** cho ảnh và mask, mask chỉ được
   nội suy nearest), `UNet` (encoder 4 mức + đáy, decoder có skip connection), `dice_loss` (soft Dice lớp người trên cả
   batch), `predict_mask` (BGR cỡ bất kỳ → mask đúng `(H, W)`, ở `eval()`, trả model về chế độ cũ).
2. Chia dữ liệu bằng `split_names` có sẵn (giống hệt bài Advanced 01: 136 train, 34 val). Train ít nhất ba cấu hình
   và đo trên 34 ảnh val **ở độ phân giải gốc** qua `predict_mask`, mIoU trên tổng pixel:
   - `UNet` từ đầu;
   - U-Net với encoder ResNet-18 pretrain ImageNet (lớp của bạn, decoder tự viết; nhớ chuẩn hoá đúng thống kê ImageNet);
   - YOLO11n-seg zero-shot trên cùng 34 ảnh, gộp mask mọi người thành mask "người" (như bài Intermediate 03).
3. Ít nhất hai ablation, mỗi lần đổi một thứ (bỏ Dice loss, bỏ augmentation, đổi `size`, encoder không pretrain...),
   và ước lượng dao động giữa các seed ở cấu hình chính.
4. Đo ms/ảnh của `predict_mask` (ghi thiết bị, có warmup), lưu hình mask dự đoán trên ảnh val.
5. Viết `starter/REPORT.md` theo khung có sẵn, rồi làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- Test trên CPU: `joint_transform` eval tất định, đúng chuẩn hoá ImageNet, mask chỉ 0/1, giữ hình học; train ngẫu nhiên
  theo `generator`, tái lập theo seed, có lật ngang, ảnh và mask luôn khớp nhau (≥ 95% pixel trên 6 seed); `UNet` đúng
  shape output, đáy `16·base` kênh, có skip connection (logit phụ thuộc mạnh vào lân cận gần của nó); `dice_loss` khớp
  công thức trên cả batch, khả vi, gần 0 khi đúng hoàn toàn; `predict_mask` đổi BGR sang RGB, chạy ở `eval()`, trả mask
  đúng `(H, W)` của ảnh gốc, khớp pipeline eval của `joint_transform`, trả model về chế độ cũ.
- `REPORT.md` không còn TODO, ít nhất 600 từ, có bảng, mọi hình được nhắc tới đều tồn tại.
- Phần còn lại chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Cách chắc nhất để ảnh và mask không lệch nhau: rút **một lần** các tham số ngẫu nhiên (toạ độ crop, cỡ, có lật hay
không) từ `generator`, rồi áp cùng tham số cho cả hai tensor. Vẽ mask chồng lên ảnh sau augmentation trước khi train:
lệch vài pixel là đủ làm IoU viền tụt. Với 136 ảnh, overfit một batch 4 ảnh tới loss gần 0 là phép thử rẻ nhất cho
model và loss.

### Gợi ý 2

Encoder ResNet-18 của torchvision cho feature ở các độ phân giải 1/2 (`relu` sau `conv1`), 1/4 (`layer1`), 1/8, 1/16,
1/32: đó là các skip connection của bạn. Cross-entropy theo pixel cộng Dice loss thường ổn định hơn một mình từng cái.
Trong `predict_mask`, nội suy **logits** về `(H, W)` rồi mới `argmax` cho viền mượt hơn là phóng to mask nhị phân.
