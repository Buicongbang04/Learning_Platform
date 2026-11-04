---
title: Tìm điểm nghẽn nạp dữ liệu và chọn num_workers
level: intermediate
services: []
files:
  - path: starter/loader_bench.py
    note: 3 hàm TODO (profile, diagnose, smallest_sufficient)
  - path: tests/test_loader.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/15-distributed-training/exercises/intermediate/03-dataloader-bottleneck -q
---

## Mục tiêu

Đo xem vòng huấn luyện dành bao nhiêu thời gian **chờ dữ liệu** so với **tính toán**, kết luận điểm nghẽn nằm ở đâu, và chọn số
`num_workers` nhỏ nhất đủ để GPU không ngồi chờ, thay vì đoán hay đặt bừa một số lớn.

## Đề bài

`starter/loader_bench.py` có sẵn:

- `SlowDataset`: mỗi mẫu tốn `DECODE_S` = 2 ms "đọc và giải mã" (đứng thay cho đọc ảnh từ đĩa/S3 rồi decode, augment).
- `train_step(batch)`: đứng thay cho một bước huấn luyện trên GPU, chiếm `STEP_S` = 20 ms.

Một batch 16 mẫu đọc tuần tự mất khoảng 32 ms, lâu hơn bước huấn luyện. Điền 3 hàm:

**`profile(dataset, num_workers, batches=25, warmup=5, batch_size=BATCH, prefetch_factor=2, step=train_step) -> dict`**:

- Dựng `DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers)`, thêm `prefetch_factor` chỉ khi
  `num_workers > 0` (PyTorch báo lỗi nếu truyền khi không có worker).
- Lấy và xử lý tuần tự `warmup + batches` batch: với mỗi batch, đo thời gian **chờ** lấy batch tiếp theo từ iterator và thời gian gọi
  `step(batch)`. `warmup` batch đầu không được tính (worker đang khởi động).
- Trả `{"num_workers", "batches", "wait_s", "compute_s", "wait_fraction", "samples_per_s"}`, với `wait_fraction = wait_s / (wait_s + compute_s)`,
  `samples_per_s = batches x batch_size / (wait_s + compute_s)`.

**`diagnose(report, threshold=0.2) -> str`**: `"data"` nếu `wait_fraction > threshold`, ngược lại `"compute"`.

**`smallest_sufficient(dataset, candidates=(0, 1, 2, 4), **kwargs) -> (int | None, list[dict])`**: đo các giá trị trong `candidates`
**theo thứ tự tăng dần** (truyền `kwargs` cho `profile`), dừng ở giá trị đầu tiên mà `diagnose` trả `"compute"`; trả giá trị đó (hoặc
`None` nếu không có) cùng danh sách các report đã đo theo thứ tự đo.

Luật mà test kiểm (bằng đồng hồ thật, ngưỡng có dư cho máy đang bận):

- Không worker: `wait_s` ít nhất 90% thời gian giải mã tối thiểu, `compute_s` trong khoảng 0.9-2.5 lần `batches x STEP_S`, `wait_fraction`
  trên 0.4, chẩn đoán `"data"`; hai công thức `wait_fraction`, `samples_per_s` đúng như trên.
- 4 worker: `wait_fraction` dưới 0.2, chẩn đoán `"compute"`, thông lượng hơn 1.5 lần lúc không worker.
- `step` và `batch_size` truyền vào được dùng thật (test truyền hàm đếm và batch 8); batch warmup không bị tính (test cho bước warmup
  chậm 0.3 giây).
- Bước huấn luyện 0.2 giây thì không worker cũng chẩn đoán `"compute"`; `diagnose` theo đúng ngưỡng.
- `smallest_sufficient` với `candidates=(4, 0, 1, 2)` đo theo thứ tự tăng dần, mọi report trước cái cuối là `"data"`, cái cuối là
  `"compute"`, kết quả là 2 hoặc 4 (máy bận có thể cần 4); chỉ có `(0,)` thì trả `None`.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/15-distributed-training/exercises/intermediate/03-dataloader-bottleneck -q` pass.
- Bạn giải thích được vì sao 1 worker chưa đủ mà 2 worker đủ, chỉ bằng ba con số 2 ms, 16 mẫu, 20 ms.
- Bạn nói được vì sao với GPU thật phải `torch.cuda.synchronize()` trước khi bấm giờ bước huấn luyện.

## Gợi ý

### Gợi ý 1

`time.perf_counter()` trước và sau `next(iterator)`, rồi sau `step(batch)`. Dùng `iter(loader)` một lần, không `for` lồng.

### Gợi ý 2

Với `num_workers` worker song song, mỗi worker làm cả batch: một batch mới sẵn sàng sau khoảng `32 ms / num_workers`. So con số đó với 20 ms.
