# Lời giải: CronJob Kubernetes

## Cách làm và vì sao

- **ConfigMap vs Secret**: cấu hình thường (`TARGET_SCHEMA`) để ConfigMap, mật khẩu để Secret. Tách
  ra để phân quyền RBAC khác nhau và để Secret có thể bật encryption at rest. Giá trị ConfigMap phải
  là chuỗi nên `"5000"` có ngoặc.
- **`stringData`** cho phép viết giá trị thô; API server tự mã hoá base64 vào `data`. Lưu ý base64
  không phải mã hoá. Ở production không commit Secret thật vào Git: dùng External Secrets Operator,
  Sealed Secrets hoặc Vault.
- **`concurrencyPolicy: Forbid`**: nếu lần chạy 10h kéo dài sang 11h, lần 11h bị bỏ qua thay vì
  hai Pod cùng ghi một bảng.
- **`backoffLimit: 3`** + **`restartPolicy: OnFailure`**: lỗi tạm thời (DB khởi động lại) được thử
  lại, nhưng có giới hạn để không retry vô hạn. `activeDeadlineSeconds` chặn job treo.
- **`runAsNonRoot`** + `runAsUser: 10001` khớp user trong Dockerfile.
- **Image tag cố định** `1.4.0` (hoặc commit SHA): biết chính xác code nào đang chạy, rollback
  được. `latest` cùng `imagePullPolicy` mặc định khiến các node chạy phiên bản khác nhau.
- **requests/limits**: requests để scheduler đặt Pod đúng node; memory limit chặn job pandas ăn hết
  RAM node. Job vượt limit sẽ `OOMKilled`.

Áp dụng thử (nếu có cluster, vd. kind/minikube):

```bash
kubectl create namespace data
kubectl apply -f k8s.yaml
kubectl create job --from=cronjob/olist-ingest manual-run -n data
kubectl logs -n data job/manual-run
```
