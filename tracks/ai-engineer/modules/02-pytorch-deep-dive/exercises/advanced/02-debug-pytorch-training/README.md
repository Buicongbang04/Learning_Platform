---
title: Gỡ lỗi vòng train PyTorch hỏng mà không báo lỗi
level: advanced
services: []
files:
  - path: starter/broken.ipynb
    note: 5 bug im lặng, không nói ở đâu
  - path: starter/BUGS.md
    note: Ghi lại từng bug
  - path: tests/test_broken.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py cifar10
  - uv run jupyter lab tracks/ai-engineer/modules/02-pytorch-deep-dive/exercises/advanced/02-debug-pytorch-training/starter/broken.ipynb
  - uv run pytest tracks/ai-engineer/modules/02-pytorch-deep-dive/exercises/advanced/02-debug-pytorch-training -q
---

## Mục tiêu

Module 01 cho bạn gỡ bug trong backprop tự viết. Ở đây gradient do autograd lo và luôn đúng, nhưng vòng train vẫn hỏng:
bug nằm ở những chỗ PyTorch làm việc ngầm thay bạn, và khi dùng sai thì nó lặng lẽ làm việc khác.
Làm xong bạn có quy trình khoanh vùng bằng phép đo cho một vòng train PyTorch thật, và một `BUGS.md` đáng đưa vào portfolio.

## Đề bài

**Phần cứng:** CPU · ~120 phút

Thời gian trên là thời gian điều tra. Mỗi lần chạy `train` trên 10 000 ảnh CIFAR-10 mất khoảng 35–45 giây trên CPU laptop rảnh (lâu hơn nhiều khi máy đang bận);
dùng tập nhỏ hơn hoặc ít epoch hơn khi thử giả thuyết.

`starter/broken.ipynb` train một ResNet nhỏ (stem, 3 `ResBlock` độ rộng w → 2w → 4w, average pool, `Linear`; 78 042 tham
số với w = 16) trên 10 000 ảnh train đầu của CIFAR-10, validation là 2 000 ảnh test đầu, bằng SGD Nesterov + OneCycle,
gradient accumulation 2 micro-batch, augmentation lật ngang. Notebook chạy hết, loss có giảm một chút, nhưng val accuracy
sau 4 epoch chỉ khoảng 0.22. Trong các cell định nghĩa có **5 bug im lặng**, mỗi bug một chỗ, đều là lỗi đặc trưng của
PyTorch. Đề không nói chúng ở đâu.

1. Tìm và sửa cả 5 bug ngay trong notebook. Không đổi chữ ký hàm, siêu tham số mặc định của `train`
   (`seed=0, epochs=4, batch_size=128, lr=0.2, w=16`), `accum_steps=2` của `train_step`, kiến trúc dự định và `DEVICE`:
   sửa ở gốc, không bù triệu chứng bằng cách chỉnh lr hay thêm epoch.
2. Mỗi giả thuyết một phép thử, dùng quy trình ở mục 7 lý thuyết và công cụ của các bài trước (hook đo activation và
   gradient ở Basic 01, so với cài đặt tham chiếu). Thêm cell `explore` tuỳ ý.
3. Ghi `starter/BUGS.md`: mỗi bug một mục `## Bug N: <tên ngắn>` với **triệu chứng** (con số), **cách phát hiện** (phép thử
   nào, kết quả gì) và **sửa** (dòng trước và sau). Cuối cùng ghi thứ tự gỡ, val accuracy sau mỗi lần sửa, bug nào che bug
   nào, và checklist bạn sẽ chạy trước khi train lâu.
4. Làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- Siêu tham số mặc định của `train`, `accum_steps=2` của `train_step` và `DEVICE = "cpu"` không đổi.
- Mỗi hàm làm đúng việc mà tên và docstring của nó nói: test so `preprocess`, `loss_fn` và `train_step` với một cài đặt
  tham chiếu trên dữ liệu nhỏ (giá trị và gradient), kể cả khi trạng thái trước đó của model và optimizer không sạch.
- `Net(16)` có đúng số tham số của kiến trúc dự định (78 042) và đi trọn qua `state_dict`: một `Net` mới nạp trạng thái của
  `Net` khác cho cùng output.
- `train` trên dữ liệu tổng hợp dễ (1 024 ảnh, 3 epoch, w = 8) đạt val accuracy ≥ 0.9, history là số thực, và model trả về có
  trạng thái hợp lệ của một model vừa được train (test kiểm cả buffer).
- `BUGS.md` không còn TODO, ít nhất 5 mục `## Bug N`, ít nhất 300 từ.
- Nội dung chấm theo rubric trong `SOLUTION.md`; trên CIFAR-10 bản đã sửa đạt khoảng 0.60 sau 4 epoch.

## Gợi ý

### Gợi ý 1

Đi từ đầu vào tới bước cập nhật, mỗi tầng một phép thử độc lập: dữ liệu vào model có đúng như bạn nghĩ không (nhìn tận mắt),
model có đúng như kiến trúc bạn định không (đếm, so với tính tay), loss và gradient có khớp một cài đặt tham chiếu không, và
trạng thái nào sống qua các bước (cờ, buffer, `.grad`) có đúng không. Đừng sửa gì trước khi có một con số chứng minh nó sai.

### Gợi ý 2

Một bug có thể che bug khác: sửa xong mỗi bug, chạy lại mọi phép thử và ghi val accuracy. Ưu tiên phép thử rẻ, tất định trên
batch nhỏ (lr = 0 để chỉ nhìn gradient, model đúng tuyệt đối để nhìn loss, `assert` ngay trong vòng train) hơn là train lại
cả tập rồi đoán.
