---
title: Serving dưới tải với k6, p95 và thông lượng theo số replica, Triton batching
level: intermediate
services: []
files:
  - path: starter/isvc.yaml
    note: InferenceService custom predictor còn TODO
  - path: starter/load.js
    note: Script k6 còn TODO
  - path: starter/triton/eta/config.pbtxt
    note: Cấu hình model Triton còn TODO
  - path: starter/triton/eta/1/model.py
    note: Model Python backend có sẵn, không cần sửa
  - path: tests/test_load.py
    note: Không sửa
  - path: tests/test_triton.py
    note: Không sửa; phần chạy Triton thật cần MLOPS_TRITON=1
run:
  - bash setup/mlops/kind/up.sh --senior
  - nice -n 15 uv run pytest tracks/mlops/modules/14-kubernetes-ml-production/exercises/intermediate/03-serving-under-load -q -s
---

## Mục tiêu

Đo một service model dưới tải bằng công cụ thật và đọc số đo như kỹ sư capacity: p95 và thông lượng thay đổi thế nào khi tăng replica, vì sao. Cấu hình dynamic batching của Triton và biết cách chứng minh nó có tác dụng.

## Đề bài

**Phần A, KServe custom predictor (bắt buộc).** Image lab `ml-lab:dev` với `ROLE=predictor` là model ETA giả theo giao thức KServe v1: `GET /v1/models/eta` (sẵn sàng sau khi nạp model 2 giây), `POST /v1/models/eta:predict` với `{"instances": [[distance_km, hour, passengers], ...]}` trả `{"predictions": [...], "pod": ...}`. Mỗi request tốn `SERVICE_MS=20` ms và mỗi pod xử lý `CONCURRENCY=1` request một lúc (trần ~50 req/s mỗi pod).

1. Sửa `starter/isvc.yaml` (InferenceService `eta-load`): tắt autoscaler (`serving.kserve.io/autoscalerClass: none` hoặc `minReplicas == maxReplicas`); `readinessProbe` kiểu `httpGet` vào `/v1/models/eta`; `resources.requests` và `limits` có `cpu` và `memory`; `automountServiceAccountToken: false` ở predictor. Giữ nguyên `image: ml-lab:dev`, `SERVICE_MS`, `CONCURRENCY`.
2. Viết `starter/load.js`: kịch bản **8 VU chạy đều 15 giây** (executor `constant-vus`), mỗi vòng `POST ${__ENV.TARGET}/v1/models/eta:predict` với **2 dòng** `instances`, `check` mã 200 và đủ 2 dự đoán, khai `thresholds` (tỉ lệ lỗi dưới 1%, check đạt trên 99%).

Test build image, tạo Service `NodePort` trước các pod predictor và chạy k6 (`grafana/k6` qua `mlopskit.k6_run`) trong mạng Docker `kind`, gọi `http://<node>:<nodePort>`: request đi qua kube-proxy như client thật. Không dùng `port-forward`, vì nó chỉ nối vào một pod. Test đặt `minReplicas = maxReplicas` lần lượt là **1** rồi **3** và chạy script của bạn mỗi lần. Đòi:

- summary k6 có request, có check đạt, có threshold, tỉ lệ lỗi dưới 1%;
- thông lượng ở 3 replica **≥ 1,5 lần** ở 1 replica, và p95 ở 3 replica **≤ 0,75 lần** ở 1 replica (lý tưởng là 3 lần và 1/3; ngưỡng nới cho máy đang bận và cân bằng theo kết nối, xem mục 2 lý thuyết).

Test in bảng replica / req/s / p95 (chạy với `-s`).

**Phần B, Triton (cấu hình bắt buộc, chạy thật tuỳ chọn).** `starter/triton/eta/` là model repository Triton: `1/model.py` (Python backend, có sẵn, mỗi lần chạy model tốn 20 ms bất kể batch to nhỏ) và `config.pbtxt`. Sửa `config.pbtxt`:

- `max_batch_size` từ 8 đến 64;
- `dynamic_batching` với `max_queue_delay_microseconds` từ 1 đến 5000 (ngân sách chờ gộp tối đa 5 ms);
- `instance_group` **2** instance `KIND_CPU`.

`test_triton_config` kiểm tĩnh tệp này và luôn chạy. `test_triton_batches_under_load` mặc định **skip**: image `nvcr.io/nvidia/tritonserver:26.09-py3` nặng 9,04 GB nén, không có bản CPU-only (mục 2 lý thuyết). Muốn chạy: `docker pull nvcr.io/nvidia/tritonserver:26.09-py3` rồi `MLOPS_TRITON=1 uv run pytest ... -k triton -s`. Test nạp image vào kind, mount model repository từ ConfigMap, chạy k6 16 VU trong 20 giây vào `/v2/models/eta/infer`, rồi đọc `:8002/metrics`. Đòi tỉ lệ lỗi dưới 1% và số lần chạy model (`nv_inference_exec_count`) **dưới một nửa** số request thành công.

## Tiêu chí đạt

- Phần A đạt trên cluster; ghi bảng số đo của bạn.
- Từ số đo, tính được thông lượng mỗi replica và số replica cần cho 300 req/s với p95 dưới 100 ms, có dự phòng mất một pod.
- `config.pbtxt` đạt test tĩnh; nói được `max_queue_delay_microseconds` đổi gì lấy gì.

## Gợi ý

### Gợi ý 1

Script k6 cần `export const options = { scenarios: {...}, thresholds: {...} }` và `export default function () {...}`. Metric có sẵn để đặt ngưỡng: `http_req_failed` (tỉ lệ), `checks` (tỉ lệ).

### Gợi ý 2

Nếu thông lượng ở 3 replica chỉ gấp đôi, đếm xem bao nhiêu pod thật sự nhận request: k6 giữ kết nối keep-alive và kube-proxy chọn pod lúc mở kết nối. Trường `pod` trong phản hồi cho biết pod nào trả lời.
