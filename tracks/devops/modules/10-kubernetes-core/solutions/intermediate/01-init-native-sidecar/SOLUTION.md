# Lời giải: init container, native sidecar và Job

Lời giải: `k8s/api.yaml`, `k8s/db-check.yaml`.

## API

- `initContainers[0]` là `wait-db`: vòng lặp Python mở TCP tới `postgres:5432`, tối đa 120 giây, rồi thoát 0. Kubelet chạy init
  container tuần tự, cái trước xong mã 0 mới tới cái sau; lỗi thì restart theo `restartPolicy` của pod (Deployment luôn là
  `Always`), pod hiện `Init:CrashLoopBackOff`. Chỉ chờ cổng mở là đủ cho bài; muốn chặt hơn thì chạy `pg_isready` hay chính lệnh
  migration.
- `initContainers[1]` là `proxy` có `restartPolicy: Always`: native sidecar (GA từ 1.33). Kubelet khởi động nó, chờ **startupProbe**
  của nó đạt, rồi mới chạy container chính. Nó sống suốt đời pod, được restart riêng nếu chết, readiness của nó tính vào readiness
  của pod, và khi pod dừng nó dừng **sau** container chính (ngược thứ tự khai báo), nên request cuối của API vẫn đi qua proxy.
- Service `api` cổng 80 trỏ `targetPort: proxy` (8080). Mọi request vào pod đi qua Nginx; cổng 8000 của API vẫn mở trong pod nhưng
  Service không trỏ vào. Muốn chặn hẳn đường vòng thì API nghe `127.0.0.1` (sample-app nghe `0.0.0.0`) hay NetworkPolicy (module 11).

## Job

Job Complete khi mọi container trong `containers` kết thúc thành công. Sidecar kiểu cũ (một container thường chạy mãi) giữ pod
`Running`, Job `active: 1` tới khi `activeDeadlineSeconds` giết nó và Job thành `Failed`. Trước 1.28 người ta vá bằng cách để
container chính ghi tệp "xong" vào volume chung rồi sidecar tự thoát, hay `kill` qua `shareProcessNamespace`. Native sidecar bỏ
được mẹo đó: kubelet dừng sidecar khi container chính xong.

## Ephemeral container

```bash
kubectl debug -it deploy/api --image=nginx:1.30.6-alpine --target=api -- sh
```

`kubectl debug` thêm một **ephemeral container** vào pod đang chạy qua subresource `pods/ephemeralcontainers` (không sửa được spec
thường của pod, không có probe, cổng hay resources, không restart). `--target` cho nó chung PID namespace với container `api` nên thấy
được tiến trình của API (`ps`, `/proc/1/root`). Nó không có trong Deployment vì gắn vào **một pod**, mất khi pod mất. Namespace
Pod Security `baseline` vẫn áp cho ephemeral container: không debug kiểu privileged được, đúng ý đồ.

## Sai lầm hay gặp

- Đặt `proxy` trước `wait-db`: proxy khởi động khi Postgres chưa có, vẫn chạy được (proxy HTTP tới 127.0.0.1:8000), nhưng thứ tự
  khởi động không còn đúng ý đồ; test kiểm thứ tự.
- Sidecar không có startupProbe: kubelet coi sidecar đã khởi động ngay khi tiến trình chạy, container chính có thể nhận request khi
  Nginx chưa nghe.
- Nginx stream `proxy_pass postgres:5432` phân giải tên lúc khởi động; Service `postgres` đổi ClusterIP (xoá tạo lại) thì phải
  restart proxy, hoặc dùng `resolver` cộng biến.
