# Lời giải: Helm chart cho API Olist Shop

Lời giải nằm trong `olist-api/`. Những điểm sửa so với starter và lý do:

## Helper

- `selectorLabels` chỉ gồm `app.kubernetes.io/name` và `app.kubernetes.io/instance`. Starter đặt cả `app.kubernetes.io/version` vào
  selector: `spec.selector` của Deployment bất biến, nên lần `helm upgrade` đổi `appVersion` sẽ lỗi `field is immutable` và phải xoá
  Deployment (mất capacity) mới cài được. Nhãn đổi theo bản nằm trong `labels`.
- `labels` thêm `helm.sh/chart` (tên-version của chart), `app.kubernetes.io/version`, `app.kubernetes.io/managed-by: {{ .Release.Service
  }}`: công cụ (ArgoCD, dashboard, `kubectl get -l`) và người đọc biết object thuộc release nào, chart bản nào.
- Helper `olist-api.image` gom `repository:tag` với tag mặc định là `.Chart.AppVersion`, để một chỗ quyết định image.

## Deployment

- `replicas: {{ .Values.replicaCount }}`, image qua helper: starter hard-code cả hai nên `--set` không có tác dụng.
- `DATABASE_URL` qua `secretKeyRef` của `database.existingSecret`. Starter ghi chuỗi có mật khẩu: nó nằm trong Git, trong output của
  `helm template`, và trong Secret `sh.helm.release.v1.shop.v*` của release (Helm lưu manifest và values đã cài), nên ai đọc được Secret của
  namespace là đọc được. Chart nhận tên Secret có sẵn (tạo bởi External Secrets, Vault, SOPS ở module 12).
- `checksum/config` trong pod template: ConfigMap đổi thì template đổi, Deployment rollout, và `helm rollback` đưa pod về đúng cấu hình cũ.
  Không có nó, env từ ConfigMap chỉ đổi khi pod tình cờ được tạo lại.
- Probe readiness `/readyz`, liveness `/healthz` (module 10); `resources` từ values.
- `podSecurityContext` (runAsNonRoot, UID 10001 của image, seccomp RuntimeDefault) và `securityContext` (allowPrivilegeEscalation
  false, drop ALL, readOnlyRootFilesystem) từ values; `readOnlyRootFilesystem` cần `emptyDir` ở `/tmp`. Namespace của bài là
  `restricted`: thiếu bất kỳ trường nào thì `helm install --wait` treo tới hết giờ vì ReplicaSet không tạo được pod (`FailedCreate`).
- `automountServiceAccountToken: false`: API không gọi Kubernetes API.

## Test hook

Pod `<fullname>-test-readyz` với `helm.sh/hook: test` gọi `/readyz` qua Service của release (đúng đường traffic thật, không gọi IP pod),
`assert` cả mã 200 lẫn nội dung. `hook-delete-policy: before-hook-creation` giữ pod sau khi chạy để đọc log (`helm test --logs`) và xoá
bản cũ trước lần chạy sau. Pod test dùng cùng `securityContext` nên chạy được trong namespace restricted.

## Kiểm tay

```bash
helm lint --strict olist-api
helm template shop olist-api --set config.logLevel=DEBUG | grep checksum
helm upgrade --install shop olist-api -n helm-b01 --wait && helm test shop -n helm-b01 --logs
helm history shop -n helm-b01
```

Mở rộng nên làm ở dự án thật: `values.schema.json` bắt kiểu của values, PodDisruptionBudget và HPA tuỳ chọn trong chart, hook
`pre-upgrade` cho Job migration, kiểm render bằng kubeconform trong CI.
