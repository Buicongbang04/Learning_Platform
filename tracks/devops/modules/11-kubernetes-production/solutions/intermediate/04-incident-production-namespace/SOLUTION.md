# Lời giải: namespace production mới, apply thành công mà không lên pod

Lời giải nằm trong `base/` và `overlays/production/`. Bốn nguyên nhân, lộ ra lần lượt vì mỗi cửa admission chỉ báo lỗi đầu tiên nó gặp.

## Nguyên nhân gốc, theo thứ tự lộ ra

1. **LimitRange**: overlay production đặt `limits.memory: 1Gi` cho api, LimitRange của namespace cho tối đa `512Mi` mỗi container.
   `FailedCreate: pods "api-..." is forbidden: maximum memory usage per Container is 512Mi, but limit is 1Gi`. LimitRanger chạy trước
   PodSecurity nên đây là lý do đầu tiên của api. Sửa trong overlay (`512Mi`): giới hạn này là của production.
2. **Pod Security restricted**: api và pod-reporter không có `securityContext`. `kubectl apply` in `Warning: would violate PodSecurity
   "restricted:latest"` (triệu chứng 1) nhưng vẫn tạo Deployment; ReplicaSet không tạo được pod. Sửa trong **base**: runAsNonRoot,
   runAsUser 10001, seccomp RuntimeDefault, allowPrivilegeEscalation false, drop ALL, readOnlyRootFilesystem cộng emptyDir `/tmp`. Đây là
   cấu hình đúng cho mọi môi trường, không phải riêng production; postgres, redis của team DBA đã làm sẵn.
3. **ResourceQuota**: overlay đặt `replicas: 8` với request `256Mi`: 2Gi, trong khi quota `requests.memory: 1280Mi` (postgres, redis,
   pod-reporter đã chiếm 192Mi). Sau khi qua hai cửa trên, ReplicaSet tạo được vài pod rồi `exceeded quota: production, requested:
   requests.memory=256Mi` (triệu chứng 3). Sửa: `replicas: 3` (768Mi, cộng 256Mi cho một pod surge của rolling update vẫn vừa 1280Mi; với 3
   replica `maxUnavailable` 25% làm tròn xuống là 0, nên rollout **cần** chỗ cho pod surge, quota sát nút sẽ làm rollout treo), giữ request
   đo được. Cần đỉnh cao hơn thì HPA (bài 02) trong giới hạn quota,
   hay xin platform nâng quota, không đè quota.
4. **RBAC của pod-reporter**: Role chỉ có `get pods`, script gọi `GET /api/v1/namespaces/<ns>/pods` là **list**. API trả `403 pods is
   forbidden: User "system:serviceaccount:<ns>:pod-reporter" cannot list resource "pods" in API group "" in the namespace "<ns>"`. Sửa:
   verb `list` (bỏ `get` không dùng). Lớp này chỉ lộ ra khi pod-reporter đã qua được PSA.

## Vì sao `kubectl apply` báo thành công

`apply` tạo Deployment, và Deployment hợp lệ. Pod do ReplicaSet controller tạo sau đó, bằng danh tính của controller; mọi từ chối admission
của pod chỉ nằm trong event `FailedCreate` của ReplicaSet. `kubectl rollout status` mới bắt được (hết giờ chờ).

## Postmortem mẫu (rút gọn)

- **CI**: `kubectl apply -k overlays/production --dry-run=server` vào một namespace staging có **đúng** nhãn Pod Security, quota, LimitRange
  như production (dry-run server chạy admission của Deployment nhưng không của pod, nên thêm bước render pod template ra Pod và dry-run
  từng cái, hay dùng kube-score, Kyverno CLI với policy restricted).
- **Sau deploy**: `kubectl rollout status` mọi Deployment có timeout, fail pipeline nếu hết giờ; alert khi ReplicaSet có event
  `FailedCreate`.
- **Quyền**: test RBAC bằng ma trận `auth can-i` như Basic 02 cho ServiceAccount của từng job.
- **Quy trình**: platform team công bố quota và LimitRange của namespace mới cùng ví dụ manifest đạt restricted trước khi giao.
