---
title: Sự cố - job tính doanh thu không bao giờ xong sau đợt chuẩn hoá manifest worker
level: intermediate
services: []
files:
  - path: starter/k8s/worker.yaml
    note: Manifest worker đang chạy production
  - path: tests/fixtures/platform.yaml
    note: Postgres, Redis, api và policy của team platform; không sửa
  - path: tests/fixtures/clients.yaml
    note: Hai pod khác trong namespace; không sửa
  - path: tests/fixtures/incident/worker.yaml
    note: Bản manifest lúc sự cố, test dùng để tái hiện
  - path: tests/test_recompute_jobs.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/15-service-mesh-patterns/exercises/intermediate/02-incident-recompute-jobs-stuck -q -rs
---

## Mục tiêu

Chẩn đoán một sự cố trong mesh mà mọi thứ "trông có vẻ ổn": pod chạy, proxy có mặt, API trả lời. Tìm bằng chứng ở đúng chỗ (log của
ứng dụng, metrics của proxy hai phía, policy đang áp), sửa đúng manifest của mình, và không nới lỏng bảo mật của người khác để
"cho chạy".

## Đề bài

Olist Shop chạy trong một namespace có inject Linkerd cho mọi pod. Team platform sở hữu Postgres, Redis, api và các policy mesh
(`tests/fixtures/platform.yaml`); team của bạn sở hữu worker (`starter/k8s/worker.yaml`). Tuần trước có một đợt chuẩn hoá manifest
của worker (nhãn, annotation, tài nguyên). Từ khi bản mới lên:

- `POST /jobs/recompute` của api vẫn trả `202 {"job_id": ...}`, `/readyz` của api trả `{"db":"ok","redis":"ok"}`.
- Bảng doanh thu theo bang không bao giờ được cập nhật; `redis-cli llen olist:jobs` tăng dần theo số job đã gửi.
- `kubectl get pods`: worker `2/2 Running`, không restart.
- Log của worker lặp lại mỗi vài giây:

  ```json
  {"ts": "...", "level": "WARNING", "msg": "mất kết nối redis, thử lại", "request_id": "-", "trace_id": "-", "logger": "olist_shop.worker", "exc": "Traceback ... redis.exceptions.ConnectionError: ..."}
  ```

- `jobs_processed_total` ở cổng 9101 của worker đứng ở 0.

Yêu cầu khi sửa:

- Chỉ sửa `starter/k8s/worker.yaml`. Không tạo, không sửa object của team platform (Server, AuthorizationPolicy,
  MeshTLSAuthentication, HTTPRoute, và các workload `api`, `redis`, `postgres`).
- Worker vẫn chạy trong mesh như mọi service khác.
- Redis vẫn chỉ phục vụ Olist Shop: pod khác trong namespace (`intruder` trong mesh, `legacy-report` ngoài mesh) không được dùng nó.

**Cách test chấm.** Cài phần của platform và hai pod khác. Ca hồi quy: apply `tests/fixtures/incident/worker.yaml`, gửi 2 job, chờ 25
giây, ghi lại: hai job vẫn nằm trong `olist:jobs`, `jobs_processed_total` là 0, và proxy của Redis ghi nhận kết nối bị từ chối. Xoá bản
đó, apply `starter/k8s/`, rồi:

| Kiểm | Mong đợi |
| --- | --- |
| Apply | Thành công; manifest không chứa object của platform |
| Job | 3 job mới được xử lý trong 90 giây (`jobs_processed_total` tăng 3), `olist:jobs` về 0 |
| Mesh | `lab.mesh_status("deployment/worker")`: pod chạy, `injected`, `mtls` |
| Redis | `intruder` và `legacy-report` vẫn không PING được Redis |

Khoảng 2 phút. Cần cluster `devops-lab` có Linkerd dùng chung (mục 0 của README module).

Muốn thử tay: tạo namespace có nhãn `pod-security.kubernetes.io/enforce=baseline` và annotation `linkerd.io/inject=enabled` bằng
kubeconfig admin, apply `tests/fixtures/platform.yaml`, `tests/fixtures/clients.yaml` rồi `tests/fixtures/incident/worker.yaml`.

## Tiêu chí đạt

- Mọi test pass.
- Viết được trong `SOLUTION.md` của riêng bạn (hay nói lại): bằng chứng nào dẫn tới từng nguyên nhân, theo thứ tự bạn tìm ra.
- Giải thích được vì sao "pod có 2/2 container" chưa chứng minh traffic của pod đi qua mesh với đúng danh tính.
- Đề xuất một cách để lỗi kiểu này bị bắt trước khi lên production (kiểm trong CI, policy admission, hay alert).

## Gợi ý

### Gợi ý 1

Bắt đầu từ phía nhận. Proxy của Redis ghi lại mỗi kết nối nó từ chối, kèm thông tin về bên gọi:
`linkerd --kubeconfig ~/.kube/devops-lab.yaml diagnostics proxy-metrics -n <ns> deploy/redis | grep -E 'authz_deny|tcp_open_total'`.
So các nhãn trên dòng của worker với dòng của api.

### Gợi ý 2

Đặt cạnh nhau spec của pod worker sau khi inject (`kubectl get pod -o yaml`), spec của pod api, và những gì `platform.yaml`
cho phép. Sửa xong một chỗ mà vẫn lỗi thì đọc lại metrics:
nhãn trên dòng bị từ chối có đổi không?
