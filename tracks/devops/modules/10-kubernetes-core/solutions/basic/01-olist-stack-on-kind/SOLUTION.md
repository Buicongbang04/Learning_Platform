# Lời giải: đưa Olist Shop lên kind

Lời giải nằm trong `k8s/` (năm tệp cùng tên với starter).

## Các quyết định

- **Secret riêng, tham chiếu bằng `secretKeyRef`/`secretRef`.** Mật khẩu không nằm trong Deployment hay StatefulSet, nên ai đọc
  được pod spec (quyền `view` không có Secret) cũng không đọc được mật khẩu. Secret chỉ là base64 trong etcd; ở production bật
  encryption at rest và dùng External Secrets hay Vault (module 12).
- **Postgres là StatefulSet có Service headless và `volumeClaimTemplates`.** Pod tên ổn định `postgres-0`, DNS
  `postgres-0.postgres.<ns>.svc`, PVC `data-postgres-0` đi theo tên đó: xoá pod, pod mới gắn lại đúng volume. `PGDATA` là thư mục
  con vì gốc volume có thể có `lost+found`, mà `initdb` từ chối thư mục không rỗng.
- **Redis là Deployment, không volume.** Trong Olist Shop Redis chỉ là hàng đợi; mất thì enqueue lại. Thêm volume cho Redis là giữ
  thứ không cần giữ.
- **Ba probe của API khác nhau có chủ đích.** startupProbe `/healthz` cho phép khởi động tới 60 giây; readiness `/readyz` (kiểm DB
  và Redis) quyết định pod có nhận traffic không; liveness `/healthz` (chỉ tiến trình) quyết định restart. Liveness gọi `/readyz` thì
  DB chậm làm restart mọi pod API cùng lúc.
- **Worker có startupProbe và livenessProbe trên cổng metrics.** Worker chỉ mở 9101 sau khi tạo được bảng; startupProbe
  `periodSeconds: 2, failureThreshold: 60` cho nó 2 phút. Liveness trên thread metrics chỉ chứng minh tiến trình còn sống, không
  chứng minh vòng `BLPOP` không treo; production thêm metric "lần xử lý job cuối" và alert.
- **Resources.** requests cho scheduler biết chỗ, `limits.memory` chặn rò rỉ RAM ăn cả node. Không đặt `limits.cpu`: CPU limit gây
  throttle cả khi node rảnh; nhiều team chỉ đặt request CPU. Kết quả là QoS Burstable.

## Lệnh kiểm tay

```bash
kubectl get pods -o wide
kubectl get endpointslices -l kubernetes.io/service-name=api
kubectl port-forward svc/api 18000:8000 &
curl -s localhost:18000/readyz
kubectl logs deploy/worker --tail=5
```

## Sai lầm hay gặp

- Service `postgres` thiếu `clusterIP: None`: vẫn chạy, nhưng không có bản ghi DNS cho từng pod, và StatefulSet replica > 1 không
  phân biệt được primary.
- `targetPort: 8000` thay vì tên cổng: chạy, nhưng đổi cổng container thì quên Service. Dùng tên (`http`) cho Service theo pod.
- Quên `envFrom` ConfigMap ở worker: worker dùng `REDIS_URL` mặc định `localhost:26379` và CrashLoop.
