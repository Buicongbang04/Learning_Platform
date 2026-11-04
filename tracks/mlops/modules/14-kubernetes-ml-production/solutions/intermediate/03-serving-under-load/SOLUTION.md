# Lời giải: serving dưới tải, p95 theo số replica, Triton batching

Lời giải ở `isvc.yaml`, `load.js`, `triton/eta/config.pbtxt`.

## Phần A

Số đo tham khảo trên laptop 16 nhân (máy đang chạy việc khác):

| Replica | req/s | p95 |
| --- | --- | --- |
| 1 | ~49 | ~170 ms |
| 3 | ~95–145 | ~60–105 ms |

- **1 replica**: trần `CONCURRENCY / SERVICE_MS` = 1 / 0,02 s = 50 req/s; 8 VU chờ nhau nên mỗi request xếp sau trung bình ~7 request khác, p95 ≈ 8 × 20 ms cộng mạng.
- **3 replica**: lý tưởng 150 req/s. Với keep-alive, 8 kết nối chia không đều cho 3 pod (kube-proxy chọn pod lúc mở kết nối): có lần chỉ 2 pod nhận kết nối, thông lượng ~100. Test vì vậy đo lại lần 3 replica một lần khi lần đầu lệch; ngưỡng 1,5 lần (không phải 3) để dư cho máy đang bận, và chấm latency bằng trung vị (≤ 0,7 lần) cộng p95 nới (≤ 0,9 lần). Bỏ keep-alive chia đều theo request (~130 req/s) nhưng p95 tăng (~120 ms) vì hàng đợi từng pod dao động ngẫu nhiên.
- **Capacity cho 300 req/s, p95 < 100 ms**: ở 3 replica đều tải mỗi pod ~45 req/s với p95 ~60 ms, nên dùng `r` ≈ 40 req/s mỗi pod (giữ p95 dưới ngưỡng). `ceil(300 / 40)` = 8 replica, cộng 1 dự phòng mất pod/rolling update = **9**. Kiểm lại bằng k6 ở 300 req/s (executor `constant-arrival-rate`) trước khi tin.

`constant-vus` là tải **đóng** (closed): VU chờ phản hồi mới gửi tiếp, nên khi service chậm tải tự giảm và p95 trông dễ chịu hơn thực tế. Để kiểm SLO ở một mức req/s cố định, dùng tải **mở** `constant-arrival-rate`: hàng đợi lộ ra ngay khi vượt capacity.

## Phần B

```text
max_batch_size: 32
dynamic_batching {
  preferred_batch_size: [ 8, 16 ]
  max_queue_delay_microseconds: 2000
}
instance_group [ { count: 2 kind: KIND_CPU } ]
```

- `max_queue_delay_microseconds` là thời gian tối đa một request chờ để được gộp với request khác. Đổi tối đa 2 ms latency lấy số lần chạy model ít hơn. Model trong lab tốn 20 ms mỗi lần chạy **bất kể batch**, giống GPU với batch nhỏ, nên gộp 8 request là thông lượng gấp ~8.
- `instance_group` 2 instance: hai batch chạy song song. Trên GPU, nhiều instance trên một card giúp che thời gian chuyển dữ liệu; trên CPU thì bị giới hạn bởi số nhân.
- Bằng chứng: `nv_inference_exec_count` (số lần chạy model) nhỏ hơn hẳn `nv_inference_request_success`. Test Triton (khi bật) đòi dưới một nửa.
- `model.py` dùng Python backend để không cần chuyển model sang ONNX; production thường dùng backend ONNX Runtime/TensorRT, nơi batching còn lợi hơn.
