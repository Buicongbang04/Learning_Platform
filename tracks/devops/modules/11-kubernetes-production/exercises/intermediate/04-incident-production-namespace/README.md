---
title: Sự cố - namespace production mới, apply thành công mà không lên pod
level: intermediate
services: []
files:
  - path: starter/base/kustomization.yaml
    note: Base Kustomize, secretGenerator
  - path: starter/base/api.yaml
    note: API
  - path: starter/base/pod-reporter.yaml
    note: Job nội bộ đếm pod qua API Kubernetes
  - path: starter/base/postgres.yaml
    note: Do team DBA giao, đã đạt restricted
  - path: starter/base/redis.yaml
    note: Do team DBA giao, đã đạt restricted
  - path: starter/overlays/production/kustomization.yaml
    note: Overlay production
  - path: starter/overlays/production/api-production.yaml
    note: Patch của production cho api
  - path: tests/fixtures/platform.yaml
    note: ResourceQuota, LimitRange của platform team, test cài trước; không sửa
  - path: tests/fixtures/incident/overlays/production/kustomization.yaml
    note: Bản lúc sự cố (cả thư mục incident), test dùng để tái hiện triệu chứng
  - path: tests/test_incident_production_namespace.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/11-kubernetes-production/exercises/intermediate/04-incident-production-namespace -q -rs
---

## Mục tiêu

Gỡ một sự cố nhiều lớp ở tầng namespace: đọc event của controller khi không có pod nào để `describe`, nhận ra từng cửa admission đang
chặn, sửa đúng chỗ trong một cây Kustomize base/overlay mà không đụng rào chắn của platform team, rồi xử lý lỗi quyền lộ ra phía sau.

## Đề bài

Olist Shop chuyển sang namespace production mới do platform team cấp: Pod Security `restricted`, một ResourceQuota và một LimitRange
(`tests/fixtures/platform.yaml`, đọc được nhưng không phải của bạn). Team ứng dụng deploy bằng `kubectl apply -k
overlays/production`. Sau lần deploy đầu:

1. `kubectl apply` in vài dòng `Warning`, kết thúc bằng một loạt `created`, mã thoát 0.
2. `kubectl get deploy`: `postgres`, `redis` `1/1`; `api` và `pod-reporter` `0/N`. `kubectl get pods` chỉ có hai pod.
3. Người trực sửa thử một chỗ rồi apply lại thì `api` vẫn `0/N`, nhưng lý do trong event đổi sang câu khác; sau lần sửa tiếp theo `api`
   lên được vài pod rồi dừng.
4. Khi `pod-reporter` cuối cùng chạy được, log của nó là các dòng JSON có `"error": 403`.

`pod-reporter` là job nội bộ: mỗi 10 giây gọi API Kubernetes liệt kê pod trong namespace, in số pod và số pod Ready (dashboard của team
đọc log này). Sửa `starter/` để mọi workload chạy, giữ các yêu cầu của production:

| Yêu cầu | Giá trị |
| --- | --- |
| api | Ít nhất 3 replica, tất cả Ready; `requests` đúng `cpu: 100m`, `memory: 256Mi` (đo từ staging); `LOG_LEVEL=WARNING` |
| Bí mật | Secret `olist-db` sinh từ `secretGenerator` (tên có hậu tố hash), api tham chiếu qua `secretKeyRef` |
| pod-reporter | Log dòng cuối có số pod Ready (ít nhất 6) và không có lỗi; ServiceAccount của nó không đọc Secret, không xoá pod |
| Rào của platform | Overlay không chứa ResourceQuota, LimitRange, Namespace; nhãn Pod Security của namespace giữ `restricted` |

Viết postmortem ngắn (không chấm tự động): nguyên nhân gốc theo thứ tự lộ ra, vì sao `kubectl apply` báo thành công, cách bắt sớm trong CI.

**Cách test chấm.** Hai `KubeLab(pod_security="restricted")`. Mỗi lab cài `tests/fixtures/platform.yaml` trước.

| Lab | Làm | Kiểm |
| --- | --- | --- |
| Bài của bạn | `lab.apply_learner(overlays/production)` (Kustomize render trong sandbox), `kubectl wait --for=condition=Available` cả bốn Deployment tối đa 180 giây | Apply thành công; bốn Deployment Available |
| | Đọc Deployment api | `replicas ≥ 3`, `readyReplicas` bằng `replicas`; requests và `LOG_LEVEL` như bảng; `/readyz` gọi từ pod-reporter trả 200 |
| | Render overlay, đọc quota | Không có ResourceQuota, LimitRange, Namespace; quota `production` giữ đúng `spec.hard` của fixture; nhãn `enforce=restricted` còn |
| | Đọc Deployment api | Mọi `secretKeyRef` trỏ Secret tên bắt đầu `olist-db-` |
| | Log và quyền của pod-reporter | Dòng cuối có `ready ≥ 6`, không có `error`; `lab.can_i`: list pods là yes, get secrets và delete pods là no |
| Tái hiện | Apply `tests/fixtures/incident/overlays/production` (giống starter), chờ 20 giây | Event `FailedCreate` của api nói về giới hạn bộ nhớ mỗi container, của pod-reporter nói về PodSecurity `restricted`; api không có pod Ready; ServiceAccount `pod-reporter` không list được pod |

Khoảng 1 phút khi đã sửa, 4 phút trên starter.

## Tiêu chí đạt

- Mọi test pass, kể cả ca tái hiện.
- Postmortem nêu đủ các lớp theo thứ tự lộ ra và chỉ ra vì sao từng lớp che lớp sau.
- Giải thích được vì sao sửa trong overlay hay trong base cho từng nguyên nhân (cái gì là của production, cái gì là của mọi môi trường).

## Gợi ý

### Gợi ý 1

Không có pod thì `describe` cái tạo ra pod: `kubectl describe rs -l app.kubernetes.io/name=api`, hay `kubectl events --for
deployment/api`. Đọc `kubectl describe quota` và `kubectl describe limitrange` để biết rào của namespace; `kubectl kustomize
overlays/production` để xem đúng thứ sẽ được apply.

### Gợi ý 2

Thông báo 403 của API server nói đủ user, verb, resource và nhóm API. So nó với Role của `pod-reporter`. Muốn biết một ServiceAccount làm
được gì: `kubectl auth can-i --list --as=system:serviceaccount:<namespace>:pod-reporter` (cần kubeconfig admin).
