---
title: Benchmark harness có warmup, p50/p95 và throughput theo batch
level: basic
services: []
files:
  - path: starter/bench.py
    note: 2 hàm TODO
  - path: tests/test_bench.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/11-deep-learning-serving/exercises/basic/02-benchmark-harness -q
---

## Mục tiêu

Viết một bộ đo latency/throughput mà con số của nó đáng tin: loại lần chạy warmup, không đo nhầm việc chuẩn bị dữ liệu, báo phân vị thay vì trung bình, và so được giữa các batch size.

## Đề bài

Điền `starter/bench.py`:

- `summarize(latencies_ms, batch_size)` trả dict:
  - `p50_ms`, `p95_ms`: `np.percentile` (mặc định, nội suy tuyến tính) của các số đo;
  - `mean_ms`: trung bình;
  - `throughput_ips`: số ảnh mỗi giây, bằng `batch_size * số lần đo / (tổng latency tính bằng giây)`.
- `benchmark(run, make_batch, batch_sizes, warmup=5, iters=30)`: với **từng** batch size theo đúng thứ tự trong `batch_sizes`:
  1. gọi `make_batch(batch_size)` **đúng một lần**, trước mọi phép đo;
  2. gọi `run(batch)` `warmup` lần, **không đo**;
  3. gọi `run(batch)` `iters` lần, mỗi lần đo bằng `time.perf_counter()` (đổi ra ms).

  Trả list dict, mỗi dict có `batch_size`, `warmup`, `iters`, `latencies_ms` (list dài đúng `iters`) cộng mọi khoá của `summarize`.

Test dùng một hàm `run` giả có vài lần đầu chậm 200 ms (giống JIT, cấp phát bộ nhớ, nạp kernel lúc khởi động) rồi 2 ms; số đo không được chứa lần nào trên 100 ms. Một test khác chạy harness trên session ONNX Runtime thật của model tí hon với batch 1 và 8.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/11-deep-learning-serving/exercises/basic/02-benchmark-harness -q` pass.
- Chạy harness trên model tí hon với batch 1, 4, 16, 32 trên máy bạn và đọc được: throughput tăng tới đâu thì bão hoà, p95 tăng theo batch thế nào.
- Nói được vì sao trên GPU phải `synchronize` trước khi dừng đồng hồ (ONNX Runtime `run` đã đồng bộ, PyTorch CUDA thì không).

## Gợi ý

### Gợi ý 1

`time.perf_counter()` là đồng hồ đơn điệu độ phân giải cao; `time.time()` có thể nhảy khi NTP chỉnh giờ.

### Gợi ý 2

Throughput tính từ tổng thời gian đo (`sum(latencies)`), không phải `batch_size / p50`: p50 bỏ qua đuôi chậm, mà đuôi đó vẫn tốn thời gian thật.
