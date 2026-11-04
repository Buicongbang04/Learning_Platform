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

Test đọc tĩnh `isvc.yaml` chỉ để kiểm autoscaler đã tắt và `SERVICE_MS`, `CONCURRENCY` không đổi; probe, resources và `automountServiceAccountToken` được kiểm trên **pod predictor thật** mà KServe sinh ra. Test build image, tạo Service `NodePort` trước các pod predictor và chạy k6 (`grafana/k6` qua `mlopskit.k6_run`) trong mạng Docker `kind`, gọi `http://<node>:<nodePort>`: request đi qua kube-proxy như client thật. Không dùng `port-forward`, vì nó chỉ nối vào một pod. Với keep-alive, 8 kết nối chia ngẫu nhiên cho 3 pod thỉnh thoảng (~1–3% số lần) bỏ trống một pod và làm thông lượng chỉ gấp đôi (xem gợi ý 2), nên nếu lần đo 3 replica đầu trông lệch (thông lượng dưới 2 lần hoặc trung vị trên 0,5 lần so với 1 replica), test **đo lại một lần** và giữ lần có thông lượng cao hơn rồi mới chấm. Test đặt `minReplicas = maxReplicas` lần lượt là **1** rồi **3** và chạy script của bạn mỗi lần. Đòi:

- summary k6 có request, có check đạt, có threshold, tỉ lệ lỗi dưới 1%;
- thông lượng ở 3 replica **≥ 1,5 lần** ở 1 replica, latency trung vị **≤ 0,7 lần** và p95 **≤ 0,9 lần** ở 1 replica (lý tưởng là 3 lần và 1/3; ngưỡng nới cho máy đang bận, và p95 nới hơn vì script không dùng keep-alive cũng hợp lệ nhưng có đuôi latency dài hơn, xem mục 2 lý thuyết).

Test in bảng replica / req/s / trung vị / p95 (chạy với `-s`).

**Phần B, Triton (cấu hình bắt buộc, chạy thật tuỳ chọn).** `starter/triton/eta/` là model repository Triton: `1/model.py` (Python backend, có sẵn, mỗi lần chạy model tốn 20 ms bất kể batch to nhỏ) và `config.pbtxt`. Sửa `config.pbtxt`:

- `max_batch_size` từ 8 đến 64;
- `dynamic_batching` với `max_queue_delay_microseconds` từ 1 đến 5000 (ngân sách chờ gộp tối đa 5 ms);
- `instance_group` **2** instance `KIND_CPU`.

`test_triton_config` đọc tệp này bằng một parser protobuf text format (chịu `{}`, `[]` lồng; cộng `count` của mọi `instance_group`) và luôn chạy. `test_triton_batches_under_load` mặc định **skip**, và **chưa chạy thật lần nào** khi viết bài (không kéo image), nên có thể cần chỉnh khi bạn bật nó lần đầu:

- Image `nvcr.io/nvidia/tritonserver:26.09-py3` nặng 9,04 GB nén, không có bản CPU-only (mục 2 lý thuyết). Chi phí đĩa ~2–3 lần con số đó: bản trong Docker, tệp tar tạm ở `~/.cache/mlops-kind/load` lúc `kind load` (xoá ngay sau khi nạp), bản trong containerd của node.
- Chạy: `docker pull nvcr.io/nvidia/tritonserver:26.09-py3` rồi `MLOPS_TRITON=1 uv run pytest ... -k triton -s`. Test nạp image vào kind, mount model repository từ ConfigMap, chạy Triton với `--model-control-mode=explicit --load-model=eta` (ConfigMap mount tạo thêm thư mục ẩn `..data`, `..<thời điểm>` trong `/models`; chế độ explicit chỉ nạp đúng model `eta`), pod chạy non-root uid 1000 (user `triton-server` của image theo tài liệu NGC, chưa kiểm), seccomp `RuntimeDefault`, bỏ mọi capability, `/tmp` là emptyDir. k6 chạy 16 VU trong 20 giây vào `/v2/models/eta/infer`, rồi test đọc `:8002/metrics`. Đòi tỉ lệ lỗi dưới 1% và số lần chạy model (`nv_inference_exec_count`) **dưới một nửa** số request thành công.
- Gỡ sau khi xong: `docker exec mlops-control-plane crictl rmi nvcr.io/nvidia/tritonserver:26.09-py3` và `docker rmi nvcr.io/nvidia/tritonserver:26.09-py3`.

## Tiêu chí đạt

- Phần A đạt trên cluster; ghi bảng số đo của bạn.
- Từ số đo, tính được thông lượng mỗi replica và số replica cần cho 300 req/s với p95 dưới 100 ms, có dự phòng mất một pod.
- `config.pbtxt` đạt test tĩnh; nói được `max_queue_delay_microseconds` đổi gì lấy gì.

## Gợi ý

### Gợi ý 1

Script k6 cần `export const options = { scenarios: {...}, thresholds: {...} }` và `export default function () {...}`. Metric có sẵn để đặt ngưỡng: `http_req_failed` (tỉ lệ), `checks` (tỉ lệ).

### Gợi ý 2

Nếu thông lượng ở 3 replica chỉ gấp đôi, đếm xem bao nhiêu pod thật sự nhận request (trường `pod` trong phản hồi): k6 giữ kết nối keep-alive và kube-proxy chọn pod lúc mở kết nối. `noConnectionReuse: true` chia đều theo request, nhưng p95 lại cao hơn vì mỗi pod nhận hàng đợi ngẫu nhiên: thử cả hai và so.
