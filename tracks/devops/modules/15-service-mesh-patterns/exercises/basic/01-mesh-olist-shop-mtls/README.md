---
title: Đưa Olist Shop vào mesh Linkerd, mTLS và chỉ API, worker được gọi Redis
level: basic
services: []
files:
  - path: starter/k8s/olist-shop.yaml
    note: api, worker, Service api; 2 TODO
  - path: starter/k8s/redis-policy.yaml
    note: 3 TODO
  - path: tests/fixtures/data.yaml
    note: Postgres, Redis (đã trong mesh), Secret olist-db; không sửa
  - path: tests/fixtures/clients.yaml
    note: storefront, intruder (trong mesh), legacy-report (ngoài mesh); không sửa
  - path: tests/test_mesh_olist_shop.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/15-service-mesh-patterns/exercises/basic/01-mesh-olist-shop-mtls -q -rs
---

## Mục tiêu

Đưa API và worker của Olist Shop vào mesh Linkerd, mỗi workload có danh tính mTLS riêng theo ServiceAccount, rồi dùng danh tính đó
để khoá Redis: chỉ API và worker được nói chuyện với nó, kể cả khi pod khác nằm cùng namespace và cùng mesh.

## Đề bài

Namespace của lab **không** bật inject cho cả namespace; pod nào muốn vào mesh phải tự xin. Test cài sẵn từ `tests/fixtures/`:

- `postgres`, `redis` (ServiceAccount cùng tên, đã có annotation inject, Redis nghe cổng tên `redis` 6379);
- `storefront` và `intruder`: pod shell trong mesh, ServiceAccount cùng tên;
- `legacy-report`: pod shell ngoài mesh (không proxy, không mTLS).

Sửa hai tệp trong `starter/k8s/`:

1. `olist-shop.yaml`
   - Thêm hai ServiceAccount `api` và `worker` (`automountServiceAccountToken: false`; proxy Linkerd tự lấy token riêng để xin chứng chỉ).
   - Mỗi Deployment chạy bằng ServiceAccount của nó.
   - Đưa pod của `api` và `worker` vào mesh bằng annotation trên pod template, không sửa namespace.
2. `redis-policy.yaml`
   - Một `Server` (`policy.linkerd.io/v1beta3`) chọn pod Redis, cổng `redis`, giao thức `opaque` (Redis là TCP, không phải HTTP).
   - Một `MeshTLSAuthentication` nêu đúng hai danh tính của `api` và `worker` (dùng `identityRefs` kiểu ServiceAccount, hay `identities`
     dạng `<sa>.<namespace>.serviceaccount.identity.linkerd.cluster.local`; namespace của lab đổi theo mỗi lần chạy nên `identityRefs`
     tiện hơn).
   - Một `AuthorizationPolicy` có `targetRef` là Server trên, `requiredAuthenticationRefs` là MeshTLSAuthentication trên.

Token của lab chỉ ghi được object `policy.linkerd.io` trong namespace của lab, và chỉ tham chiếu danh tính trong namespace đó.

**Cách test chấm.** Cài phần trong `tests/fixtures/`, ghi một lần đối chứng (trước khi có manifest của bạn, `intruder` và `legacy-report`
đều PING được Redis), apply `starter/k8s/`, chờ rollout, rồi:

| Kiểm | Cách | Mong đợi |
| --- | --- | --- |
| Proxy và danh tính | `lab.mesh_status("deployment/api")`, `"deployment/worker"` | `injected`, `mtls`, `identity` là `api.<ns>.serviceaccount.identity.linkerd.cluster.local` (và `worker...`) |
| Ứng dụng chạy | exec vào api: `/readyz`; `POST /jobs/recompute` | `200` có `"db":"ok"`, `"redis":"ok"`; `jobs_processed_total` của worker (cổng 9101) tăng trong 60 giây |
| mTLS từ client | storefront gọi `http://api:8000/healthz` | 200; `mesh_status` của api có danh tính storefront trong `clients` |
| Redis bị khoá | intruder và legacy-report gửi `PING` tới `redis:6379` | Không nhận `+PONG`; `denied` của Redis tăng ít nhất 2 |
| Danh sách cho phép | Đọc MeshTLSAuthentication trong namespace | Chỉ nêu `api` và `worker` |

Khoảng 1 phút khi đạt, 3 phút trên starter (test chờ trạng thái mesh tới hạn rồi mới fail). Cần cluster `devops-lab` có Linkerd dùng
chung (mục 0 của README module).

## Tiêu chí đạt

- Mọi test pass.
- Giải thích được vì sao NetworkPolicy theo nhãn pod không phân biệt được `intruder` với `api` khi kẻ tấn công tạo được pod mang nhãn
  của api, còn danh tính mTLS theo ServiceAccount thì phân biệt được.
- Nói được vì sao `legacy-report` (không có proxy) bị chặn dù không có luật nào nhắc tới nó.
- Đọc được một dòng `inbound_tcp_authz_deny_total` trong metrics của proxy Redis và chỉ ra ai bị chặn.

## Gợi ý

### Gợi ý 1

Annotation đưa một pod vào mesh là `linkerd.io/inject: enabled`, đặt ở `spec.template.metadata.annotations`, không ở `metadata` của
Deployment. Tên cổng trong `Server.spec.port` có thể là tên (`redis`) hay số (6379). Khi đã có Server cho một cổng, mọi kết nối tới
cổng đó bị từ chối trừ khi một AuthorizationPolicy cho phép.

### Gợi ý 2

Xem tay bằng kubeconfig admin (CLI tuỳ chọn ở mục 0):
`linkerd --kubeconfig ~/.kube/devops-lab.yaml diagnostics proxy-metrics -n <ns> deploy/redis | grep -E 'tcp_open_total|authz_deny'`.
Nhãn `client_id` cho biết ai đã kết nối qua mTLS; `tls="no_identity"` là kết nối không mTLS.
