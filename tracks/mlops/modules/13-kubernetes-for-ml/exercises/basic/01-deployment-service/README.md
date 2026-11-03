---
title: Deployment, Service và ConfigMap cho service ETA
level: basic
services: []
files:
  - path: starter/eta-api.yaml
    note: ConfigMap + Deployment + Service, còn thiếu nhiều trường
  - path: tests/test_deployment.py
    note: Không sửa
run:
  - bash setup/mlops/kind/up.sh
  - nice -n 15 uv run pytest tracks/mlops/modules/13-kubernetes-for-ml/exercises/basic/01-deployment-service -q
---

## Mục tiêu

Chuyển service ETA từ một dòng `docker run` sang ba object Kubernetes cơ bản, và kiểm nó bằng request HTTP thật đi qua Service chứ không dừng ở "pod Running".

## Đề bài

Service ETA (code và `Dockerfile` ở `tracks/mlops/modules/13-kubernetes-for-ml/lab/service/`, không sửa) nghe cổng **8080**, đọc model ở đường dẫn trong biến `MODEL_PATH`, có `GET /healthz`, `GET /readyz` và `POST /predict` với body `{"rows": [[distance_km, hour, passengers], ...]}`; mỗi phản hồi có trường `model_version`. Image chứa sẵn ba model `/models/eta-v1.joblib`, `eta-v2`, `eta-v3`.

Sửa `starter/eta-api.yaml` để:

1. ConfigMap `eta-api-config` có `MODEL_PATH: /models/eta-v2.joblib`; container đọc nó qua `envFrom` (không đặt `prefix`) hoặc `configMapKeyRef`, **không** ghi cứng `MODEL_PATH` trong `env`. Service mặc định nạp v1 khi thiếu biến, nên chỉ thấy v2 khi biến thật sự tới container.
2. Deployment `eta-api`: **2 replica**, container cổng 8080, `readinessProbe` kiểu `httpGet`, `resources.requests` và `resources.limits` có cả `cpu` lẫn `memory`.
3. Service `eta-api` mở **cổng 80** chuyển tới cổng 8080 của pod.
4. Cứng hoá pod (service không gọi API Kubernetes và không cần quyền gì): ở mức pod `automountServiceAccountToken: false`; `runAsNonRoot: true` trong `securityContext` của pod hoặc của container (đặt ở container thì giá trị đó thắng); ở container `securityContext.allowPrivilegeEscalation: false` và `capabilities.drop: [ALL]`. Image đã chạy bằng user `10001`; nên thêm `seccompProfile: RuntimeDefault` và `readOnlyRootFilesystem: true` (service không ghi đĩa), test không bắt.

Giữ `image: eta-serve:dev`: test build image từ `lab/service`, nạp vào cluster kind bằng `mlopskit.kind_load` rồi thay tên image này bằng tag vừa build. Test tạo namespace tạm `mlops-ex-<uuid8>`, apply manifest, chờ đủ 2 pod Ready, `port_forward` vào `svc/eta-api` cổng 80, gọi `/healthz` và `/predict`.

Muốn tự thử bằng tay: `docker build -t eta-serve:dev tracks/mlops/modules/13-kubernetes-for-ml/lab/service`, `kind load docker-image eta-serve:dev --name mlops`, rồi `kubectl --context kind-mlops create ns eta-try` và `kubectl --context kind-mlops -n eta-try apply -f ...`; xong thì xoá namespace đó.

## Tiêu chí đạt

- ConfigMap có `MODEL_PATH` của model v2 và container lấy biến từ ConfigMap.
- Deployment 2 replica, có `readinessProbe` `httpGet`, có requests và limits cho cpu và memory; Service cổng 80.
- Pod có bốn trường cứng hoá ở mục 4.
- Qua Service, `/healthz` và `/predict` trả `model_version == "v2"`, dự đoán khớp model v2 (sai số 0,001).

## Gợi ý

### Gợi ý 1

Deployment tìm pod của nó bằng `spec.selector.matchLabels`; Service tìm pod bằng `spec.selector`. Cả hai phải khớp nhãn trong `spec.template.metadata.labels`.

### Gợi ý 2

Đặt tên cổng (`name: http`) trong container rồi dùng `targetPort: http` và `port: http` trong probe: đổi số cổng một chỗ là đủ.
