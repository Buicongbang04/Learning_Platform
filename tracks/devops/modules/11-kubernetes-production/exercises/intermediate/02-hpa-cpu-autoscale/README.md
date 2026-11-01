---
title: HPA theo CPU cho API, tải giả trong namespace, lên và xuống đúng hẹn
level: intermediate
services: []
files:
  - path: starter/k8s/api.yaml
    note: Deployment và Service api
  - path: starter/k8s/hpa.yaml
    note: HPA chưa xong
  - path: tests/fixtures/loadgen.yaml
    note: Deployment tạo tải (8 luồng gọi /healthz), test cài và gỡ
  - path: tests/fixtures/deps.yaml
    note: Postgres, Redis, Secret olist-db
  - path: tests/test_hpa.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/11-kubernetes-production/exercises/intermediate/02-hpa-cpu-autoscale -q -rs
---

## Mục tiêu

Cho API tự co giãn theo CPU: HPA đọc được số liệu từ metrics-server, scale lên khi có tải, về lại khi hết tải trong thời gian dự đoán
được, và manifest không đánh nhau với HPA.

## Đề bài

Sửa `starter/k8s/api.yaml` và `starter/k8s/hpa.yaml`:

| Phần | Yêu cầu |
| --- | --- |
| HPA | `autoscaling/v2`, tên `api`, `scaleTargetRef` Deployment `api` (`apiVersion: apps/v1`), `minReplicas: 1`, `maxReplicas: 4`, đúng một metric: Resource `cpu`, `type: Utilization`, `averageUtilization: 60` |
| Behavior | `behavior.scaleDown.stabilizationWindowSeconds` tối đa 60 (cho lab; production thường để mặc định 300); scaleUp tuỳ bạn |
| Deployment | Container có `requests.cpu` (giá trị tuỳ bạn; bài mẫu dùng 100m); không có `spec.replicas` trong manifest |

Cluster cần metrics-server dùng chung (mục 0 của module); thiếu thì test skip kèm lệnh cài.

**Cách test chấm.** `KubeLab` cài Postgres, Redis, rồi `k8s/`, chờ api rollout, rồi:

| Bước | Chờ tối đa | Kiểm |
| --- | --- | --- |
| Đọc tĩnh | | Spec HPA như bảng trên; container có `requests.cpu`; tệp không có `spec.replicas` cho Deployment api |
| HPA có số liệu | 150 giây | `status.currentMetrics` có CPU; lúc rảnh `currentReplicas` là 1 |
| Có tải | 300 giây | Test cài `tests/fixtures/loadgen.yaml`; `currentReplicas` lên ít nhất 2 và không vượt 4; `kubectl top pods` của api có số |
| Hết tải | 300 giây | Test xoá loadgen; `currentReplicas` về 1 |

Đo trên máy viết bài: số liệu xuất hiện sau khoảng 26 giây, lên 2 replica sau khoảng 30 giây có tải (chạm 4), về 1 sau khoảng 70 giây hết
tải. Thời gian chờ của test rộng gấp nhiều lần để không fail oan trên máy chậm. Khoảng 3 phút khi đúng; trên starter cũng khoảng 3 phút
(chờ số liệu tới hết giờ).

## Tiêu chí đạt

- Mọi test pass.
- Tính tay được: 2 pod, request 100m, mỗi pod dùng 150m, mục tiêu 60% thì HPA muốn bao nhiêu replica.
- Giải thích được vì sao để `spec.replicas` trong manifest làm HPA và pipeline deploy đánh nhau, và vì sao production không nên hạ cửa sổ
  scale-down xuống 30 giây.

## Gợi ý

### Gợi ý 1

`kubectl describe hpa api` cho biết HPA đang kẹt ở đâu: `ScalingActive False` kèm `FailedGetResourceMetric` và lý do. Đọc kỹ tên
Deployment mà HPA trỏ tới.

### Gợi ý 2

`kubectl explain hpa.spec.behavior --api-version=autoscaling/v2`. Theo dõi trực tiếp trong namespace thử của bạn: `kubectl get hpa api
--watch` trong một terminal, cài loadgen ở terminal khác.
