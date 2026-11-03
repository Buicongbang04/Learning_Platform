# Lời giải: /readyz, warmup, timeout, kiểm tra đầu vào

## Cách làm

`create_app` giữ trạng thái `ready`, `model`, `error` trong một dict. Lifespan khởi động một thread nền chạy `boot()`: gọi `load_model()`, gọi `predict(warmup_rows)` ba lần, rồi mới đặt `ready=True`. Lỗi bất kỳ được ghi vào `error` và `ready` giữ `False`.

- `/healthz` không đọc trạng thái nào: "tiến trình còn xử lý được request". Nếu nó kiểm model, một lần registry chập chờn làm orchestrator giết cả đàn replica đang khoẻ.
- `/readyz` trả 503 kèm lỗi cho tới khi `ready`. Đây là thứ load balancer dùng để quyết định gửi traffic.
- `/predict` kiểm `ready` trước, rồi `validate` (số dòng, 3 số hữu hạn, `hour` trong 0..23), rồi chạy `model.predict` trong thread pool dưới `asyncio.wait_for`.

## Đánh đổi

- **Nạp nền** cho phép `/healthz` trả lời ngay (không bị `livenessProbe` giết khi nạp lâu) nhưng mọi endpoint phải biết trạng thái "chưa có model". Nạp đồng bộ trong khởi động đơn giản hơn và hợp lý khi model nhỏ và `startupProbe` đủ rộng.
- **Timeout** `wait_for` trả 504 đúng hạn nhưng không dừng được thread đang chạy: công việc vẫn chiếm một thread cho tới khi xong. Giới hạn kích thước thread pool và kích thước batch (tối đa 100 dòng) là phần còn lại của hợp đồng.
- **Warmup 3 lần** là số tối thiểu để test kiểm; trên model thật, số lần và kích thước dữ liệu warmup nên đại diện cho request thật.
- Validate bằng `math.isfinite` chặn `NaN` và `Infinity`; pydantic đã parse `1e999` thành `inf`.

## Rubric tự chấm

| Tiêu chí | Đạt khi |
| --- | --- |
| Liveness và readiness tách biệt | `/healthz` 200 mọi lúc, `/readyz` phản ánh model + warmup |
| Không chặn khởi động | Thread nền, test thấy 503 trong lúc nạp |
| 422 và 504 đúng | Từng loại đầu vào xấu, và 504 đúng hạn |
