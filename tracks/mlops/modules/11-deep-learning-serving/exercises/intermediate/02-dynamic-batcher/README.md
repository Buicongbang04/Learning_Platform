---
title: Dynamic batcher bằng asyncio, gom tối đa N request hoặc T ms
level: intermediate
services: []
files:
  - path: starter/batcher.py
    note: 3 phương thức TODO
  - path: tests/test_batcher.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/11-deep-learning-serving/exercises/intermediate/02-dynamic-batcher -q
---

## Mục tiêu

Tự viết lớp gom request mà Triton hay TorchServe gọi là dynamic batching: nhiều request ảnh đến gần nhau được chạy chung một lần qua model, tăng throughput mà mỗi request vẫn nhận đúng kết quả của mình.

## Đề bài

`starter/batcher.py` có `DynamicBatcher(infer, max_batch_size=8, max_wait_ms=10.0)` dùng được với `async with`. `infer(batch)` là hàm **đồng bộ** nhận mảng `(N, ...)` (các item xếp chồng theo trục 0) và trả mảng/list dài `N`, phần tử thứ `i` ứng với item thứ `i`. Điền `start`, `stop`, `submit` (thêm phương thức riêng tuỳ ý) sao cho:

- `await submit(item)` trả **đúng** kết quả của `item`, kể cả khi hàng chục request đến xen kẽ.
- Một batch đóng lại khi đủ `max_batch_size` item **hoặc** đã qua `max_wait_ms` kể từ khi item **đầu tiên** của batch đó đến, cái nào tới trước. Batch không bao giờ lớn hơn `max_batch_size`.
- Mỗi lần gọi `infer`, nối kích thước batch vào `self.batch_sizes`.
- `infer` chạy **ngoài** event loop (`asyncio.to_thread`): trong lúc nó chạy, các coroutine khác vẫn chạy được.
- `infer` ném lỗi: mọi request trong **batch đó** nhận đúng lỗi ấy (`await submit` ném lại), batcher tiếp tục phục vụ request sau.
- `stop()` dừng task nền; thoát `async with` không treo.

Test kiểm: 50 request xen kẽ nhận đúng kết quả; 40 request đồng thời với `max_batch_size=8` gom thành không quá 7 batch, không batch nào quá 8; 8 request cách nhau 5 ms với `max_wait_ms=150` vào **một** batch; request đơn lẻ không bị giữ quá 0.4 s với `max_wait_ms=40`; với `infer` tốn cố định 20 ms mỗi lần gọi, 64 request đồng thời ở `max_batch_size=16` nhanh hơn ít nhất 2 lần so với `max_batch_size=1`; event loop không bị chặn; lỗi chỉ ảnh hưởng batch của nó; chạy với session ONNX Runtime thật của model tí hon cho output khớp từng ảnh chạy riêng (`atol=1e-5`).

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/11-deep-learning-serving/exercises/intermediate/02-dynamic-batcher -q` pass.
- Giải thích được đánh đổi khi tăng `max_wait_ms`: throughput, p50 lúc tải thấp, p95 lúc tải cao.
- Nói được vì sao chỉ cần `max_wait_ms` mà không có `max_batch_size` (hoặc ngược lại) là chưa đủ.

## Gợi ý

### Gợi ý 1

Mỗi `submit` tạo một `Future` (`asyncio.get_running_loop().create_future()`), đưa cặp `(item, future)` vào `asyncio.Queue`, rồi `await future`. Task nền lấy item, chạy `infer`, `future.set_result(...)` theo đúng thứ tự.

### Gợi ý 2

Lấy item đầu bằng `await queue.get()` (chờ vô hạn), đặt `deadline = loop.time() + max_wait_ms / 1000`, rồi lấy tiếp bằng `asyncio.wait_for(queue.get(), deadline - loop.time())` cho tới khi đủ hoặc hết hạn.
