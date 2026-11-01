---
title: Helm chart cho API Olist Shop - template, helper, checksum, test hook, namespace restricted
level: basic
services: []
files:
  - path: starter/olist-api/Chart.yaml
    note: Có sẵn
  - path: starter/olist-api/values.yaml
    note: Thiếu securityContext
  - path: starter/olist-api/templates/_helpers.tpl
    note: Nhãn và selector chưa đúng chuẩn
  - path: starter/olist-api/templates/deployment.yaml
    note: Hard-code, lộ mật khẩu, thiếu probe
  - path: starter/olist-api/templates/configmap.yaml
    note: Cấu hình ứng dụng
  - path: starter/olist-api/templates/service.yaml
    note: Có sẵn
  - path: starter/olist-api/templates/tests/test-readyz.yaml
    note: Chưa có hook test
  - path: tests/test_helm_chart.py
    note: Không sửa
  - path: tests/fixtures/deps.yaml
    note: Postgres, Redis, Secret olist-db do test cài trước
run:
  - uv run pytest tracks/devops/modules/11-kubernetes-production/exercises/basic/01-helm-chart-olist-api -q -rs
---

## Mục tiêu

Tự viết một Helm chart dùng được ở production cho **một** thành phần của Olist Shop (API): helper đặt tên và nhãn chuẩn, selector
không đổi qua các bản, values điều khiển mọi thứ, mật khẩu không nằm trong chart, đổi cấu hình là rollout, chạy được trong namespace Pod
Security `restricted`, và có `helm test` để kiểm sau mỗi lần cài.

## Đề bài

Hoàn thiện chart `starter/olist-api/`. Postgres, Redis và Secret `olist-db` (khoá `DATABASE_URL`) đã có sẵn trong namespace (test cài
từ `tests/fixtures/deps.yaml`); chart chỉ lo API.

| Phần | Yêu cầu |
| --- | --- |
| Tên | Mọi object tên `{{ include "olist-api.fullname" . }}`: release `shop` cho ra `shop-olist-api` |
| Nhãn | Mọi object (kể cả pod test) có `app.kubernetes.io/name: olist-api`, `app.kubernetes.io/instance: <release>`, `app.kubernetes.io/managed-by: Helm`, `helm.sh/chart: olist-api-0.1.0` |
| Selector | `spec.selector.matchLabels` của Deployment và `selector` của Service đúng bằng `{name, instance}`, không gì khác |
| Values | `replicaCount` (mặc định 2), `image.repository`, `image.tag` (rỗng thì dùng `appVersion` 1.0), `config.logLevel`, `config.redisUrl`, `database.existingSecret`, `database.key`, `resources`, `podSecurityContext`, `securityContext` |
| Bí mật | `DATABASE_URL` lấy bằng `secretKeyRef` từ `database.existingSecret`/`database.key` (mặc định `olist-db`/`DATABASE_URL`); chuỗi mật khẩu không xuất hiện trong output của `helm template` |
| Cấu hình | ConfigMap có `LOG_LEVEL`, `REDIS_URL`; pod template có annotation `checksum/config` đổi khi nội dung ConfigMap đổi |
| Probe | readiness `/readyz`, liveness `/healthz` trên cổng `http` (8000) |
| Bảo mật | Pod: `runAsNonRoot: true`, `seccompProfile.type: RuntimeDefault`; mọi container: `allowPrivilegeEscalation: false`, `capabilities.drop: ["ALL"]` |
| Test hook | Một Pod có annotation `helm.sh/hook: test`, gọi `http://<fullname>:8000/readyz`, thoát 0 khi trả 200 và `{"db":"ok","redis":"ok"}`; cũng đạt restricted |

**Cách test chấm.** Phần tĩnh chạy `helm` trong sandbox, không cần cluster; phần còn lại dùng `KubeLab(pod_security="restricted")`.

| Kiểm | Cách |
| --- | --- |
| Lint | `helm lint --strict` không lỗi |
| Render mặc định | `helm template shop` (bỏ hook test) có đúng ConfigMap, Deployment, Service tên `shop-olist-api` |
| Nhãn, selector | Như bảng trên, trên mọi object đã render |
| Values | `--set replicaCount=3 --set image.tag=1.1` ra 3 replica, image `devops-track/olist-shop:1.1`; mặc định image tag `1.0` |
| Checksum | `--set config.logLevel=DEBUG` đổi `LOG_LEVEL` và đổi annotation `checksum/config` |
| Bí mật, probe, bảo mật, hook | Như bảng trên |
| Cài | `lab.helm_install("shop", chart, "--wait", "--timeout", "120s")` vào namespace restricted, Deployment có 2 pod ready |
| `helm test` | `helm test shop` thành công, pod test `Succeeded` |
| Nâng và lùi | Cài lại với `config.logLevel=DEBUG` đổi checksum; `helm rollback shop 1` cho revision 3, `LOG_LEVEL` về `INFO`, checksum về đúng bản đầu |

Khoảng 1 phút khi chart đúng. Thử tay trước (namespace riêng, như mục 0 của module):

```bash
export KUBECONFIG=~/.kube/devops-lab.yaml &&
kubectl create namespace helm-b01 &&
kubectl label namespace helm-b01 pod-security.kubernetes.io/enforce=restricted &&
kubectl -n helm-b01 apply -f tracks/devops/modules/11-kubernetes-production/exercises/basic/01-helm-chart-olist-api/tests/fixtures/deps.yaml &&
helm lint --strict tracks/devops/modules/11-kubernetes-production/exercises/basic/01-helm-chart-olist-api/starter/olist-api &&
helm upgrade --install shop tracks/devops/modules/11-kubernetes-production/exercises/basic/01-helm-chart-olist-api/starter/olist-api -n helm-b01 --wait --timeout 2m &&
helm test shop -n helm-b01
```

Xong thì `kubectl delete namespace helm-b01`.

## Tiêu chí đạt

- Mọi test pass.
- Giải thích được vì sao `app.kubernetes.io/version` không được nằm trong selector, và chuyện gì xảy ra ở lần `helm upgrade` sau nếu nó nằm
  ở đó.
- Giải thích được vì sao chart nhận tên Secret thay vì nhận mật khẩu qua values (Helm lưu values ở đâu).

## Gợi ý

### Gợi ý 1

`helm create /tmp/demo` sinh một chart mẫu có sẵn helper `fullname`, `labels`, `selectorLabels` theo đúng quy ước; so với
`_helpers.tpl` của starter. `toYaml .Values.podSecurityContext | nindent 8` đưa cả một khối từ values vào template mà không phải liệt kê
từng trường.

### Gợi ý 2

Annotation checksum: `{{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}`. Pod test chạy bằng image Olist Shop
(có Python), nên có thể dùng `python -c` với `urllib.request`; nhớ pod test cũng phải đạt restricted, không thì `helm test` báo lỗi
admission chứ không phải lỗi ứng dụng.
