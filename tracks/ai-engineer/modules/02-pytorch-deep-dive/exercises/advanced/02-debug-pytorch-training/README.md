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
bug nằm ở chỗ PyTorch làm việc ngầm (đăng ký module, chế độ train/eval, loss nhận gì, gradient cộng dồn, layout tensor).
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
2. Mỗi giả thuyết một phép thử, dùng mục 7 lý thuyết: loss khi model đúng tuyệt đối, đếm tham số so với tính tay,
   nạp `state_dict` vào model mới, so gradient với một backward trên cả batch (lr = 0), kiểm `model.training` và running
   stats của BatchNorm, vẽ lại ảnh sau tiền xử lý, hook đo activation và gradient (bài Basic 01). Thêm cell `explore` tuỳ ý.
3. Ghi `starter/BUGS.md`: mỗi bug một mục `## Bug N: <tên ngắn>` với **triệu chứng** (con số), **cách phát hiện** (phép thử
   nào, kết quả gì) và **sửa** (dòng trước và sau). Cuối cùng ghi thứ tự gỡ, val accuracy sau mỗi lần sửa, bug nào che bug
   nào, và checklist bạn sẽ chạy trước khi train lâu.
4. Làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- Siêu tham số mặc định, `accum_steps=2`, `DEVICE = "cpu"` không đổi.
- Tiền xử lý từ ảnh `(N, H, W, C)` uint8 ra đúng tensor `(N, C, H, W)` đã chuẩn hoá (so từng pixel).
- `Net(16)` có đúng 78 042 tham số được PyTorch đăng ký, và một `Net` mới nạp `state_dict` cho cùng output.
- `loss_fn` là cross-entropy trên logits (giá trị và gradient).
- `train_step` với `accum_steps=4` cho gradient bằng gradient của cả batch, kể cả khi `.grad` đang có giá trị cũ.
- `train` trên dữ liệu tổng hợp dễ (1 024 ảnh, 3 epoch, w = 8) đạt val accuracy ≥ 0.9, BatchNorm được train ở train mode
  (running stats thay đổi), history là số thực.
- `BUGS.md` không còn TODO, ít nhất 5 mục `## Bug N`, ít nhất 300 từ.
- Nội dung chấm theo rubric trong `SOLUTION.md`; trên CIFAR-10 bản đã sửa đạt khoảng 0.60 sau 4 epoch.

## Gợi ý

### Gợi ý 1

Tách câu hỏi theo tầng: dữ liệu vào model có đúng không (vẽ lại một ảnh), model có đủ tham số và được train không (đếm,
`state_dict`, so trọng số trước và sau một bước), loss và gradient có đúng không (so với công thức, so với cả batch), và
trạng thái giữa các bước có đúng không (`model.training`, running stats, `.grad`). Một bug có thể che bug khác: sửa xong
mỗi bug, chạy lại mọi phép thử.

### Gợi ý 2

Đọc từng hàm và hỏi: "PyTorch có biết thứ này không?", "hàm này để model ở chế độ nào khi trả về?", "loss này mong nhận
logits hay xác suất?", "gradient của micro-batch đầu còn sống tới lúc `step` không?", "`reshape` có đổi thứ tự trục không?".
