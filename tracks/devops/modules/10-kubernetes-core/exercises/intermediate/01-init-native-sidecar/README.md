---
title: Init container, native sidecar và Job không bao giờ xong
level: intermediate
services: []
files:
  - path: starter/k8s/api.yaml
    note: API chưa có init container, sidecar proxy; Service trỏ thẳng vào API
  - path: starter/k8s/db-check.yaml
    note: Job kiểm DB có sidecar kiểu cũ
  - path: tests/fixtures/deps.yaml
    note: Postgres, Redis, ConfigMap, Secret do test dựng
  - path: tests/fixtures/classic-sidecar-job.yaml
    note: Bản đối chứng sidecar kiểu cũ
  - path: tests/test_init_native_sidecar.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/10-kubernetes-core/exercises/intermediate/01-init-native-sidecar -q -rs
---

## Mục tiêu

Dùng đúng ba kiểu container phụ trong một pod: init container (chạy xong mới tới container chính), native sidecar (`initContainers`
kèm `restartPolicy: Always`: khởi động trước, sống cùng pod, dừng sau) và hiểu vì sao sidecar kiểu cũ làm Job không bao giờ
Complete.

## Đề bài

**API** (`starter/k8s/api.yaml`). Team muốn mọi request vào API đi qua một reverse proxy Nginx trong cùng pod (gắn `X-Request-ID`,
thêm header `X-Served-By: olist-proxy`; cấu hình đã có trong ConfigMap `api-proxy`), và API không khởi động khi Postgres chưa mở cổng.

1. Init container `wait-db` (image `devops-track/olist-shop:1.0`, dùng `python`) chờ `postgres:5432` mở kết nối TCP, tối đa 120 giây.
2. Native sidecar `proxy` (`nginx:1.30.6-alpine`) nghe 8080, mount ConfigMap `api-proxy` vào `/etc/nginx/conf.d`, có
   startupProbe (`/proxy-healthz` hay TCP 8080). Thứ tự trong `initContainers`: `wait-db` trước, `proxy` sau.
3. Service `api` cổng 80 trỏ vào cổng của proxy.

**Job** (`starter/k8s/db-check.yaml`). Job `db-check` kiểm kết nối Postgres qua một proxy TCP Nginx chạy cạnh (mô phỏng mẫu Cloud
SQL Auth Proxy). Hiện proxy nằm trong `containers` và Job chạy mãi dù container `check` đã xong. Chuyển `pg-proxy` thành native
sidecar (có startupProbe TCP 5432) để Job Complete.

**Cách test chấm.** Test dựng Postgres, Redis, ConfigMap, Secret từ `tests/fixtures/deps.yaml`, apply thư mục `k8s/`, chờ rollout
của `api` rồi kiểm:

| Kiểm | Cách |
| --- | --- |
| Init | Init container đầu tiên tên `wait-db`, có nhắc `postgres`, kết thúc mã 0 |
| Native sidecar | Native sidecar duy nhất của pod api tên `proxy`, image `nginx:1.30.6-alpine`, có startupProbe, `ready` |
| Thứ tự | Thời điểm: `wait-db` xong ≤ `proxy` khởi động ≤ `api` khởi động |
| Qua proxy | Service `api` nghe cổng 80; gọi `http://api/readyz` từ trong pod: `200`, body `{"db":"ok","redis":"ok"}`, header `X-Served-By: olist-proxy` |
| Job | Native sidecar duy nhất của Job tên `pg-proxy`; container chính kết nối qua `127.0.0.1` hay `localhost`; không có mật khẩu trong spec; Job `Complete` trong 150 giây; log có `postgres 16` |
| Đối chứng | Apply `tests/fixtures/classic-sidecar-job.yaml`: container `check` xong mã 0 mà Job vẫn `active` sau 15 giây |

Khoảng 1 phút.

## Tiêu chí đạt

- Mọi test pass.
- Giải thích được vì sao native sidecar không chặn Job, và thứ tự dừng của nó khi pod bị xoá.
- Gỡ lỗi được một pod kẹt `Init:0/2` bằng `kubectl describe pod` và `kubectl logs <pod> -c wait-db`.
- Thử `kubectl debug` gắn một ephemeral container vào pod api (mục 2 của module) và giải thích vì sao nó không có trong spec của
  Deployment.

## Gợi ý

### Gợi ý 1

Native sidecar là một phần tử của `initContainers` có thêm `restartPolicy: Always`. Kubelet chạy init container theo thứ tự; gặp
sidecar thì khởi động nó, chờ startupProbe của nó đạt, rồi mới chạy phần tử kế tiếp. Không có startupProbe thì "đã khởi động" chỉ
là tiến trình đã chạy, chưa chắc đã nghe cổng.

### Gợi ý 2

`kubectl get pod <pod> -o jsonpath='{.status.initContainerStatuses[*].state}'` cho thấy từng init container đang ở đâu. Job chỉ
Complete khi mọi container thường (`containers`) đã kết thúc; sidecar native bị kubelet dừng sau khi container chính xong.
