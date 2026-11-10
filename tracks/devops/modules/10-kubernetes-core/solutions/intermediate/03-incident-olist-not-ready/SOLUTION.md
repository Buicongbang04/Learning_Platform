# Lời giải: Olist Shop staging lên mà không phục vụ được

Lời giải nằm trong `k8s/`: `10-postgres.yaml`, `30-api.yaml`, `40-worker.yaml` đổi; hai tệp còn lại giữ như starter.

## Nguyên nhân gốc

1. **`storageClassName: fast-ssd` trong `volumeClaimTemplates`.** Cluster không có StorageClass đó (`kubectl get storageclass` chỉ có
   `standard`), PVC `data-postgres-0` nằm `Pending` với event `ProvisioningFailed ... storageclass.storage.k8s.io "fast-ssd" not
   found`, pod `postgres-0` `Pending` vì PVC chưa bind. Postgres không chạy nên `/readyz` của API trả 503 và API `0/1` Ready. Sửa:
   `standard`. Trên cluster thật StatefulSet đã tồn tại thì `volumeClaimTemplates` không sửa tại chỗ được: xoá StatefulSet (giữ pod
   bằng `--cascade=orphan` nếu cần), xoá PVC hỏng, apply lại.
2. **Selector của Service `api` là `app: api`** trong khi pod mang `app.kubernetes.io/name: api` (PR "chuẩn hoá nhãn" đổi nhãn của
   pod mà quên Service). Service không chọn được pod nào: EndpointSlice rỗng **hoàn toàn**, không cả endpoint not-ready, kube-proxy
   cài rule REJECT nên client nhận `Connection refused` ngay cả với `/healthz`. Sửa selector về `app.kubernetes.io/name: api`.
3. **livenessProbe của worker gọi `:8000/healthz`**, chép từ API. Worker không nghe 8000 (chỉ metrics 9101), probe luôn fail,
   kubelet kill sau `failureThreshold` lần, restart với backoff tăng dần: `CrashLoopBackOff`. Log không có lỗi vì tiến trình không
   lỗi; lý do nằm ở Events của `kubectl describe pod`: `Liveness probe failed: ... connect: connection refused` rồi `Container
   worker failed liveness probe, will be restarted`. Sửa: probe cổng `metrics` (9101), thêm startupProbe vì worker chỉ mở cổng
   sau khi tạo được bảng.

## Vì sao không có báo động

`kubectl apply` chỉ kiểm schema và admission: class không tồn tại, selector không khớp, probe sai cổng đều là object hợp lệ.
`rollout restart` tạo pod mới y hệt nên không đổi gì. Triệu chứng 2 vẫn còn khi API đã Ready vì lỗi nằm ở Service chứ không ở pod.

## Postmortem mẫu (rút gọn)

- **Ảnh hưởng**: staging không phục vụ 2 giờ; QA chặn release.
- **Phát hiện sớm**: CI chạy `kubectl apply --dry-run=server` cộng một bước kiểm chéo: mỗi Service phải chọn được ít nhất một
  Deployment trong cùng bộ manifest (kube-linter, Polaris, hay script so selector với nhãn của template); `kubeconform` cho schema;
  lint mọi `storageClassName` phải nằm trong danh sách class của cluster đích.
- **Sau deploy**: pipeline chờ `rollout status` của mọi workload và gọi smoke test qua Service (không qua pod), fail thì dừng.
- **Giám sát**: alert khi PVC `Pending` quá 5 phút, khi `kube_pod_container_status_restarts_total` tăng, khi Service không có
  endpoint (`kube_endpoint_address_available == 0`, module 13).
