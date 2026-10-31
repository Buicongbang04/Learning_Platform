---
title: Transfer learning trên Oxford-IIIT Pet, linear probe, fine-tune và train từ đầu
level: intermediate
services: []
files:
  - path: starter/transfer.ipynb
    note: 11 hàm/lớp TODO
  - path: tests/test_transfer.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py oxford-pets
  - uv run jupyter lab tracks/ai-engineer/modules/03-computer-vision/exercises/intermediate/02-transfer-learning-pets/starter/transfer.ipynb
  - uv run pytest tracks/ai-engineer/modules/03-computer-vision/exercises/intermediate/02-transfer-learning-pets -q
---

## Mục tiêu

Dựng đủ các mảnh của một pipeline transfer learning thật và so ba chiến lược có đối chứng trên 37 giống chó mèo, mỗi
giống khoảng 100 ảnh train: linear probe, fine-tune toàn bộ, và train từ đầu cùng ngân sách. Làm xong bạn biết những
chỗ nhỏ làm hỏng transfer learning mà không báo lỗi (thống kê chuẩn hoá, BatchNorm khi đóng băng, learning rate cho
backbone) và chọn được chiến lược theo số đo chứ không theo cảm giác.

## Đề bài

**Phần cứng:** GPU 4GB · ~120 phút

Thời gian trên là thời gian làm bài. Notebook chạy được trên CPU (env gốc) nhưng hai lần fine-tune 3 epoch chiếm phần
lớn thời gian: khoảng 25–40 phút trên CPU 4 luồng tuỳ tải máy; với kernel `ai-gpu` trên GPU 4GB còn vài phút (batch 64
ảnh 160 px dưới 1.5 GB VRAM). Lần đầu tải bộ dữ liệu (754 MB) và weights ImageNet của ResNet-18 (45 MB, vào
`~/.cache/torch`). Test không tải gì: chúng dùng ResNet-18 khởi tạo ngẫu nhiên.

Đọc mục 4 phần lý thuyết. Mở `starter/transfer.ipynb`:

1. `load_pets`, `class_names`, `PetsDataset`: đọc parquet, lấy tên giống từ `image_id`, giải mã ảnh thành PIL **RGB**
   (bộ dữ liệu có ảnh RGBA và ảnh xám).
2. `build_transforms(train, size)`: eval là resize cạnh ngắn `round(size / 0.875)`, center crop, `Normalize` ImageNet;
   train là `RandomResizedCrop(size, scale=(0.35, 1))`, lật ngang, rồi `Normalize` như eval.
3. `build_model`, `freeze_backbone`, `set_bn_eval`, `param_groups`: thay `fc`, đóng băng mọi thứ trừ `fc`, đưa BatchNorm
   về `eval()`, chia tham số theo (head hay backbone) × (có weight decay hay không).
4. `extract_features`, `train_one_epoch` (có `scheduler` tuỳ chọn, bước theo batch), `evaluate`.

Rồi chạy các cell `explore`: linear probe trên feature ImageNet, cùng probe nhưng quên `Normalize`, fine-tune 3 epoch
(lr backbone 1e-4, head 1e-3, OneCycle), và đối chứng train từ đầu với cùng ngân sách. Sau đó làm phần trắc nghiệm của
bài trong app.

## Tiêu chí đạt

- `class_names` giữ nguyên chữ hoa/thường và dấu gạch dưới bên trong tên; `PetsDataset` trả ảnh 3 kênh cho ảnh xám và
  RGBA, nhãn là `int`.
- Transform eval tất định, đúng resize rồi center crop, ảnh màu trung bình ImageNet về gần 0; transform train ngẫu
  nhiên, không lật dọc.
- `freeze_backbone` để lại đúng `512 × 37 + 37` tham số train được; `set_bn_eval` giữ nguyên running stats khi forward
  ở chế độ train.
- `param_groups`: mỗi tham số đúng một nhóm, `fc` dùng lr của head, bias và tham số BatchNorm không weight decay, bỏ
  nhóm rỗng, chỉ gồm tham số có `requires_grad`.
- `extract_features` trả vector 512 chiều sau global average pooling, ở eval mode, không làm mất `model.fc`;
  `train_one_epoch` trả loss trung bình theo mẫu, bước `scheduler` sau mỗi batch, giữ BatchNorm đóng băng khi
  `freeze_bn=True`; `evaluate` đúng accuracy.
- Trên dữ liệu thật: 3 669 ảnh test, 37 lớp, lớp ít ảnh nhất có 88 ảnh.

## Gợi ý

### Gợi ý 1

Feature trước `fc` lấy được mà không viết lại forward của ResNet: tạm thay `model.fc` bằng một module không làm gì,
và nhớ trả lại dù có lỗi giữa chừng. Với `param_groups`, tên tham số (`named_parameters`) cho biết nó thuộc head hay
không, còn số chiều của tensor cho biết nó là bias/BatchNorm hay trọng số.

### Gợi ý 2

`model.train()` đặt **mọi** module con về chế độ train, kể cả BatchNorm bạn vừa đưa về eval; thứ tự gọi quyết định
kết quả. Trong `build_transforms`, chuỗi đổi PIL sang tensor của `transforms.v2` gồm hai bước (đổi kiểu ảnh rồi đổi
dtype có scale), sau đó mới tới `Normalize`.
