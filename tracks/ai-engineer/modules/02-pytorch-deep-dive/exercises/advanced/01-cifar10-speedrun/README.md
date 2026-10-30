---
title: CIFAR-10 94% trên GPU 4GB nhanh nhất có thể (portfolio)
level: advanced
services: []
files:
  - path: starter/speedrun.ipynb
    note: 4 hàm API, thí nghiệm do bạn thiết kế
  - path: starter/REPORT.md
    note: Báo cáo portfolio
  - path: tests/test_speedrun.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py cifar10
  - uv run jupyter lab tracks/ai-engineer/modules/02-pytorch-deep-dive/exercises/advanced/01-cifar10-speedrun/starter/speedrun.ipynb
  - uv run pytest tracks/ai-engineer/modules/02-pytorch-deep-dive/exercises/advanced/01-cifar10-speedrun -q
---

## Mục tiêu

Gom cả module vào một bài toán có thước đo rõ: đạt **≥ 94% test accuracy trên CIFAR-10** trên RTX 3050 Laptop 4GB, với
peak memory **≤ 1.5 GB**, trong thời gian train ngắn nhất bạn làm được. Bạn phải làm GPU không chờ dữ liệu, dùng mixed
precision và layout đúng, chọn kiến trúc và lịch lr, rồi chứng minh bằng ablation có seed cái gì thật sự làm nhanh và
cái gì làm chính xác. Kết quả và `REPORT.md` là một bài portfolio: "94% CIFAR-10 trong X phút trên GPU laptop 4GB, đây là
vì sao".

## Đề bài

**Phần cứng:** GPU 4GB · ~480 phút

Thời gian trên là thời gian làm bài (thiết kế, thí nghiệm, báo cáo). Bản tham chiếu train 24 epoch trong 341 giây khi GPU rảnh (11–13 phút khi GPU có tiến trình khác); mỗi ablation tương tự,
nên cả bài cần khoảng 1–2 giờ GPU. Không có GPU: notebook vẫn chạy trên CPU với `width` nhỏ để kiểm code (test chạy trên
CPU), nhưng mục tiêu 94% chỉ tính trên GPU.

1. Trong `starter/speedrun.ipynb`, cài bốn hàm test gọi (tên và thứ tự tham số giữ nguyên, được thêm tham số keyword có
   mặc định):
   - `build_model(seed, width=64)`: model ảnh 32×32 → 10 logits, khởi tạo theo `seed`, `width` điều khiển độ rộng.
   - `lr_at(step, total_steps, peak_lr, warmup_frac)`: lịch tam giác theo bước (tăng tuyến tính trong
     `max(1, round(total_steps * warmup_frac))` bước, rồi giảm tuyến tính về 0, không âm).
   - `predict_tta(model, x, batch_size=1000)`: trung bình logits của ảnh và ảnh lật ngang, eval mode, không dựng graph,
     trả float32 ở CPU, trả model về chế độ cũ.
   - `fit(model, x_u8, y, epochs, batch_size=512, **options)`: train trên `DEVICE`, trả `{"loss": [...], "seconds": ...}`.
2. Lần chạy chính: train trên 50 000 ảnh train, đánh giá **một lần** trên 10 000 ảnh test, ít nhất 3 seed. Đo thời gian
   train bằng `torch.cuda.synchronize()` trước và sau (không tính decode dữ liệu và đánh giá), peak memory bằng
   `torch.cuda.max_memory_allocated()`.
3. Ablation: mỗi lần bỏ một thành phần (AMP, `channels_last`, dữ liệu nằm sẵn trên GPU so với `DataLoader` của bài Basic 03,
   label smoothing, TTA, lịch lr), cùng ngân sách epoch. Một trace `torch.profiler` của vài bước.
4. Viết `starter/REPORT.md` theo khung có sẵn, rồi làm phần trắc nghiệm của bài trong app.

**Một `REPORT.md` portfolio tốt** mở bằng tóm tắt có số ("ResNet-9, 94.1% ± 0.1 qua 3 seed, 6 phút train, 1.3 GB, RTX 3050
4GB"), ghi đủ thiết lập để người khác chạy lại, có bảng ablation với độ phân tán theo seed và câu diễn giải trung thực (chênh
lệch nào nằm trong dao động seed), đọc trace profiler như một kỹ sư (GPU có chờ không, kernel nào lớn nhất), kể ít nhất hai
ngõ cụt (OOM, NaN, thứ làm chậm đi) và nói rõ giới hạn. Không chọn siêu tham số theo tập test: nếu cần, tách 5 000 ảnh
train làm validation.

## Tiêu chí đạt

- Test trên CPU: `lr_at` đúng các mốc (0, giữa warmup, đỉnh, giữa đoạn giảm, 0 và không âm sau cùng); `predict_tta` khớp
  trung bình hai chiều ở eval mode, bất biến khi lật input, trả model về chế độ cũ; `build_model` tái lập theo seed và
  `width` đổi số tham số; `fit` (model `width=8`, 3 epoch, batch 64) học được dữ liệu tổng hợp dễ tới accuracy ≥ 0.9.
- `REPORT.md` không còn TODO, ít nhất 700 từ, có bảng, mọi hình được nhắc tới đều tồn tại.
- Kết quả GPU (chấm theo rubric trong `SOLUTION.md`): ≥ 94% test accuracy trung bình qua 3 seed, peak memory ≤ 1.5 GB.
  Bản tham chiếu: 94.33% trung bình 3 seed (94.37 / 94.36 / 94.26 với TTA), peak 1 330 MiB.

## Gợi ý

### Gợi ý 1

Bắt đầu từ ResNet-9 (mục 4 lý thuyết, bài Intermediate 01) và dữ liệu uint8 nằm sẵn trên GPU, augmentation theo batch
(crop pad reflect 4 + lật) bằng `augment_batch` của bài Basic 03, bf16 autocast, `channels_last`, SGD Nesterov
momentum 0.9 với lịch tam giác, batch 512. Đo một epoch trước, rồi mới tính số epoch cần.

### Gợi ý 2

Bản tham chiếu dùng thêm: label smoothing 0.2, weight decay 5e-4 chỉ cho tham số ≥ 2 chiều (bài Basic 02), lớp `Linear`
cuối không bias và nhân logits với 0.125, peak lr 0.4 với warmup 20% số bước, TTA lật ngang khi đánh giá. Lưu loss bằng
tensor rồi `.item()` một lần mỗi epoch, đừng `.item()` mỗi bước (mỗi lần là một lần CPU chờ GPU).
