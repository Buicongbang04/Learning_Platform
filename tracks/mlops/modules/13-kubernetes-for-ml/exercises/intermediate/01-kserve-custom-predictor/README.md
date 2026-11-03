---
title: InferenceService custom predictor phục vụ đúng model v2
level: intermediate
services: []
files:
  - path: starter/isvc.yaml
    note: InferenceService đã Ready nhưng chưa đúng
  - path: tests/test_isvc.py
    note: Không sửa
run:
  - bash setup/mlops/kind/up.sh
  - nice -n 15 uv run pytest tracks/mlops/modules/13-kubernetes-for-ml/exercises/intermediate/01-kserve-custom-predictor -q
---

## Mục tiêu

Đưa một container serving tự viết lên KServe (custom predictor), và chứng minh nó phục vụ đúng model bằng request HTTP, không chỉ bằng trạng thái Ready.

## Đề bài

`starter/isvc.yaml` là InferenceService `eta` mà một đồng nghiệp đã apply: `kubectl get isvc` báo `READY True`, nhưng đội nghi nó không phục vụ model mới. Nhiệm vụ: InferenceService `eta` phục vụ **model v2** (`/models/eta-v2.joblib` trong image, service lab ở `tracks/mlops/modules/13-kubernetes-for-ml/lab/service/`).

Luật mà test kiểm:

1. Dùng **custom container** (`spec.predictor.containers`), không dùng `spec.predictor.model`; đúng một container tên `kserve-container`, giữ `image: eta-serve:dev` (test thay bằng image vừa build).
2. Có `readinessProbe` `httpGet` vào `/v1/models/eta` (đường này chỉ trả 200 khi model đã nạp). Không để KServe tự đặt probe TCP.
3. Giữ annotation `serving.kserve.io/autoscalerClass: none` và `minReplicas == maxReplicas` (cluster không có metrics-server).

Service lab nghe cổng 8080, đọc `MODEL_PATH` và `MODEL_NAME` (mặc định `eta`), trả lời giao thức KServe v1: `GET /v1/models/eta` và `POST /v1/models/eta:predict` với body `{"instances": [[distance_km, hour, passengers], ...]}`; mọi phản hồi có `model_version`.

Test apply vào namespace tạm, chờ InferenceService Ready, rồi `port_forward` vào Service `eta-predictor` (KServe ở chế độ RawDeployment tạo Deployment và Service tên `<tên>-predictor`) và gọi cả hai đường, đòi `model_version == "v2"` và dự đoán khớp model v2.

## Tiêu chí đạt

- InferenceService `eta` Ready; `/v1/models/eta` và `:predict` qua Service trả `model_version == "v2"`, dự đoán khớp (sai số 0,001).
- readinessProbe hỏi `/v1/models/eta`.
- Giải thích được vì sao bản starter Ready mà vẫn sai.

## Gợi ý

### Gợi ý 1

`kubectl --context kind-mlops -n <ns> get deploy eta-predictor -o yaml`: xem KServe sinh ra Deployment nào từ spec của bạn, biến môi trường nào có trong container, probe nào được thêm.

### Gợi ý 2

Service lab có giá trị mặc định cho `MODEL_PATH`. Giá trị mặc định là thứ hay làm "Ready nhưng sai".
