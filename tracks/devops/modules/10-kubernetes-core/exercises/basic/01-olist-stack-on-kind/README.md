---
title: Đưa Olist Shop lên kind - API, worker, Postgres StatefulSet, Redis
level: basic
services: []
files:
  - path: starter/k8s/00-config.yaml
    note: ConfigMap có sẵn, thiếu Secret
  - path: starter/k8s/10-postgres.yaml
    note: StatefulSet chưa có Service headless và volume bền
  - path: starter/k8s/20-redis.yaml
    note: Hoàn chỉnh, đọc để tham khảo
  - path: starter/k8s/30-api.yaml
    note: Thiếu probe, resources, Secret
  - path: starter/k8s/40-worker.yaml
    note: Chưa có gì
  - path: tests/test_olist_stack.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/10-kubernetes-core/exercises/basic/01-olist-stack-on-kind -q -rs
---

## Mục tiêu

Tự viết manifest đưa cả bốn thành phần của Olist Shop lên cluster: chọn đúng loại workload cho từng thành phần, tách cấu hình và bí
mật, đặt probe đúng ngữ nghĩa, khai báo tài nguyên, rồi kiểm từ ngoài vào bằng `kubectl port-forward`.

## Đề bài

Hoàn thiện các tệp trong `starter/k8s/` (test apply cả thư mục, theo thứ tự tên tệp, vào namespace riêng của lab):

| Thành phần | Yêu cầu |
| --- | --- |
| Secret `olist-db` | `type: Opaque`, `stringData`: `POSTGRES_USER=olist`, `POSTGRES_PASSWORD=olist-k8s-lab`, `POSTGRES_DB=olist`, `DATABASE_URL=postgresql+psycopg://olist:olist-k8s-lab@postgres:5432/olist` |
| Postgres | StatefulSet `postgres` (`postgres:16.15-alpine`), `serviceName: postgres` trỏ Service **headless** cùng tên, `volumeClaimTemplates` 1Gi StorageClass `standard`, ba biến `POSTGRES_*` lấy từ Secret |
| Redis | Deployment và Service `redis` (đã có) |
| API | Deployment `api` 2 replica (`devops-track/olist-shop:1.0`, cổng 8000 tên `http`), Service `api` ClusterIP cổng 8000; `DATABASE_URL` từ Secret; readinessProbe `/readyz`, livenessProbe `/healthz`, startupProbe tuỳ chọn; requests và `limits.memory` |
| Worker | Deployment `worker` 1 replica, cùng image, `command: ["python", "-m", "olist_shop.worker"]`, cổng metrics 9101; cùng cấu hình như API; có livenessProbe và resources |

Mọi pod mang nhãn `app.kubernetes.io/name: <tên thành phần>`. Mật khẩu không được nằm thẳng trong pod spec của Deployment hay
StatefulSet nào.

**Cách test chấm.** Test tạo namespace riêng (`KubeLab`), apply thư mục `k8s/` bằng quyền của lab, chờ `rollout status` của bốn
workload (tối đa 3 phút mỗi cái), rồi kiểm:

| Kiểm | Cách |
| --- | --- |
| Rollout xong | `kubectl rollout status` của `statefulset/postgres`, `deployment/redis`, `deployment/api`, `deployment/worker` |
| Postgres bền | `serviceName: postgres`, Service `postgres` có `clusterIP: None`, PVC `<tên template>-postgres-0` Bound với class `standard` |
| Probe | readiness của `api` gọi `/readyz`, liveness gọi `/healthz` |
| Tài nguyên | `api`, `worker` có `requests.memory`, `limits.memory`; pod có QoS `Burstable` hay `Guaranteed` |
| Bí mật | Secret `olist-db` tồn tại; pod template của `api`, `worker`, `postgres` tham chiếu `olist-db` và không chứa chuỗi mật khẩu |
| Từ ngoài vào | Script của test chạy `kubectl port-forward svc/api <cổng trống>:8000` trong sandbox rồi `curl /readyz`: `200 {"db":"ok","redis":"ok"}` |
| Endpoint | EndpointSlice của Service `api` có ít nhất 2 endpoint ready |
| Worker chạy | `POST /jobs/recompute` qua port-forward trả `202`, log của worker có `"job done"` trong 60 giây |
| DNS | Từ pod worker, `redis.<namespace>.svc.cluster.local` phân giải ra ClusterIP của Service `redis`, `postgres-0.postgres.<namespace>.svc.cluster.local` ra IP của pod `postgres-0` |

Image phải có sẵn trong hai worker của `devops-lab` (mục 0 của module); thiếu thì test skip kèm lệnh `kind load`. Khoảng 1 phút.

Thử tay trước khi chạy test (namespace riêng có Pod Security `baseline`):

```bash
export KUBECONFIG=~/.kube/devops-lab.yaml &&
kubectl create namespace olist-b01 &&
kubectl label namespace olist-b01 pod-security.kubernetes.io/enforce=baseline &&
kubectl -n olist-b01 apply -f tracks/devops/modules/10-kubernetes-core/exercises/basic/01-olist-stack-on-kind/starter/k8s/ &&
kubectl -n olist-b01 get pods,svc,pvc,endpointslices
```

Xong thì `kubectl delete namespace olist-b01`.

## Tiêu chí đạt

- Mọi test pass.
- Giải thích được vì sao Postgres là StatefulSet còn Redis là Deployment trong bài này, và vì sao liveness không gọi `/readyz`.
- Đọc được output của `kubectl describe pod` khi pod `Pending` vì PVC, hay `0/1 Ready` vì readiness.

## Gợi ý

### Gợi ý 1

`kubectl explain statefulset.spec.volumeClaimTemplates` và `kubectl explain pod.spec.containers.env.valueFrom.secretKeyRef` cho
đúng cấu trúc. Service headless chỉ khác Service thường ở `clusterIP: None`. PVC của StatefulSet tên theo mẫu
`<tên template>-<tên StatefulSet>-<số thứ tự>`.

### Gợi ý 2

Worker chỉ mở cổng metrics sau khi tạo được bảng trong Postgres, có khi mất vài chục giây lúc Postgres còn đang khởi động. Một
livenessProbe chặt mà không có startupProbe sẽ giết nó trước khi nó kịp lên (mục 3 của module).
