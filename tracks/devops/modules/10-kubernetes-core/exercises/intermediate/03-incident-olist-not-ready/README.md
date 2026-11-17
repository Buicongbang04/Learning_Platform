---
title: Sự cố - Olist Shop staging lên mà không phục vụ được
level: intermediate
services: []
files:
  - path: starter/k8s/00-config.yaml
    note: ConfigMap, Secret
  - path: starter/k8s/10-postgres.yaml
    note: Postgres
  - path: starter/k8s/20-redis.yaml
    note: Redis
  - path: starter/k8s/30-api.yaml
    note: API
  - path: starter/k8s/40-worker.yaml
    note: Worker
  - path: tests/fixtures/incident/30-api.yaml
    note: Bản lúc sự cố (cả thư mục incident), test dùng để tái hiện triệu chứng
  - path: tests/test_incident_olist_not_ready.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/10-kubernetes-core/exercises/intermediate/03-incident-olist-not-ready -q -rs
---

## Mục tiêu

Chẩn đoán như người on-call một bản deploy "apply thành công" mà không phục vụ được: đọc trạng thái pod, event, EndpointSlice, PVC,
log và lịch sử restart; tìm nguyên nhân gốc của từng triệu chứng; sửa mà không đổi thiết kế; giữ được một ca hồi quy.

## Đề bài

Sáng thứ hai, team merge PR "chuẩn hoá manifest staging và chuyển storage sang SSD" rồi apply `starter/k8s/` lên staging. `kubectl
apply` không báo lỗi nào. Mười phút sau:

1. `kubectl get pods`: `postgres-0` vẫn `Pending`. `api` có hai pod `Running` nhưng `0/1` Ready.
2. Từ một pod khác trong namespace, `curl http://api:8000/healthz` báo `Connection refused` dù `/healthz` không chạm database.
3. `worker` có cột RESTARTS tăng đều mỗi phút, trạng thái lúc `Running`, lúc `CrashLoopBackOff`. `kubectl logs deploy/worker
   --previous` không có traceback; dòng cuối thường là cảnh báo "tạo bảng lỗi, thử lại".
4. Người trực trước đã thử `kubectl rollout restart deployment/api` hai lần, không có gì khác.

Sửa `starter/k8s/` cho hết cả ba triệu chứng mà không đổi thiết kế: Postgres vẫn là StatefulSet với volume bền 1Gi, Service vẫn
tên `api` cổng 8000, nhãn `app.kubernetes.io/name` của pod giữ nguyên (dashboard và NetworkPolicy của team khác dựa vào nó), worker
vẫn có livenessProbe. Viết postmortem ngắn (không chấm tự động): nguyên nhân gốc từng triệu chứng, vì sao `kubectl apply` không báo
động, cách phát hiện sớm lần sau.

**Cách test chấm.** Hai `KubeLab` riêng. Lab đầu apply `starter/k8s/` (hay lời giải với `SOLUTION=1`), chờ rollout của bốn
workload (tối đa 2 phút mỗi cái), đợi thêm 30 giây rồi kiểm:

| Kết quả cần có | Test kiểm |
| --- | --- |
| Rollout | `statefulset/postgres`, `deployment/redis`, `deployment/api`, `deployment/worker` rollout xong |
| Volume | PVC `data-postgres-0` Bound |
| API phục vụ | Service `api` có ít nhất 2 endpoint ready; gọi `http://api:8000/readyz` từ pod worker trả `200` |
| Worker ổn định | Tổng `restartCount` của pod worker bằng 0 sau 30 giây |
| Thiết kế giữ nguyên | Pod api mang nhãn `app.kubernetes.io/name: api` |

Lab thứ hai apply `tests/fixtures/incident/` (bản lúc sự cố, giống starter) và đòi nó tái hiện đúng các triệu chứng: PVC có event
lỗi provisioning và vẫn `Pending`, worker bị restart trong 2 phút, EndpointSlice của Service `api` rỗng. Khoảng 3
phút khi đã sửa, 7 phút trên starter (chờ rollout hết giờ).

## Tiêu chí đạt

- Mọi test pass, kể cả ca tái hiện sự cố.
- Postmortem chỉ ra nguyên nhân gốc của từng triệu chứng và một cách phát hiện tự động cho mỗi cái.
- Giải thích được vì sao `rollout restart` không giúp gì, và vì sao triệu chứng 2 vẫn xảy ra ngay cả khi pod api đã Ready.

## Gợi ý

### Gợi ý 1

Đi từ dưới lên: storage, rồi pod, rồi Service. `kubectl describe pvc`, `kubectl get events --sort-by=.lastTimestamp`,
`kubectl get endpointslices -l kubernetes.io/service-name=api -o yaml`, `kubectl get pods --show-labels`. Một Service có
EndpointSlice rỗng hoàn toàn (không cả endpoint not-ready) nghĩa là gì?

### Gợi ý 2

Với worker, `kubectl describe pod` cho biết container bị kill vì lý do gì ở phần `Last State` và Events (`Liveness probe failed:
...`). So probe với những gì tiến trình worker thật sự mở (README của sample-app liệt kê cổng của từng thành phần).
