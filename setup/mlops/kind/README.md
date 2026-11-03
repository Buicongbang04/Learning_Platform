# Cluster kind `mlops` (Giai đoạn 3 track MLOps)

Một cluster Kubernetes local duy nhất, tên `mlops`, context `kind-mlops`, dùng chung cho module 13 và capstone m12.
Test không bao giờ tạo hay xoá cluster: chúng gọi `mlopskit.require_kind()` và skip kèm lệnh dựng khi cluster chưa có.

| Thành phần | Bản ghim | Ghi chú |
| --- | --- | --- |
| kind | v0.33.0 | cài vào `~/.local/bin/kind`, kiểm sha256 |
| Kubernetes (node image) | v1.35.8, ghim theo digest | 1 node control-plane |
| kubectl | v1.35.8 | cài vào `~/.local/bin/kubectl`, kiểm sha256 |
| cert-manager | v1.20.4 | KServe cần để cấp chứng chỉ cho webhook |
| KServe | v0.21.0 | chế độ **RawDeployment**, không Knative, không Istio; tắt tạo Ingress |
| Argo Workflows | v4.1.5 | namespace `argo`, controller theo dõi mọi namespace |
| MinIO (kho artifact của Argo) | `pgsty/minio:RELEASE.2026-08-04T00-00-00Z` | Deployment `argo-artifacts` trong `argo`, dữ liệu `emptyDir` |

Phiên bản, ngày phát hành và checksum nằm ở `versions.env` (mọi bản phát hành ≥2 tuần trước ngày thêm 2026-11-03).
`up.sh` kiểm sha256 của mọi tệp tải về (binary và manifest) **trước** khi dùng; không có `curl | bash`, không cần `sudo`.

## Dựng, kiểm, gỡ

```bash
bash setup/mlops/kind/up.sh                          # lần đầu ~6-7 phút (kéo image), chạy lại ~1 phút
kubectl --context kind-mlops get pods -A             # mọi pod Running
bash setup/mlops/kind/down.sh                        # xoá cluster (mất mọi thứ bên trong)
rm ~/.local/bin/kind ~/.local/bin/kubectl            # gỡ hẳn công cụ (tuỳ chọn)
rm -rf ~/.cache/mlops-kind                           # xoá cache manifest/binary đã tải
```

`up.sh` chạy lại an toàn (idempotent): binary đã có và đúng checksum thì bỏ qua; cluster đã có thì chỉ khởi động
lại node nếu container đang dừng (vd. sau khi tắt Docker) rồi `apply --server-side` lại các manifest và chờ
Available. Riêng KServe: khi controller đã đúng bản và `inferenceservice-config` đã ở RawDeployment thì bỏ qua (apply
lại `kserve.yaml` với `--force-conflicts` sẽ trả ConfigMap về `Serverless` trong vài giây trước khi vá lại, InferenceService
tạo đúng lúc đó sẽ hỏng). Đổi bản KServe thì `down.sh` rồi `up.sh`. Sau khi máy khởi động lại, node `mlops-control-plane` tự chạy lại và các pod tự hồi phục (đã kiểm);
nếu node vẫn dừng thì chạy lại `up.sh`.

## Cổng

`cluster.yaml` map hai cổng của node ra máy, chỉ bind `127.0.0.1`:

| Cổng máy | Cổng trong node | Biến `setup/.env` |
| --- | --- | --- |
| 28081 | 30080 (NodePort) | `MLOPS_KIND_HTTP_PORT` |
| 28444 | 30443 (NodePort) | `MLOPS_KIND_HTTPS_PORT` |

Service `type: NodePort` với `nodePort: 30080` sẽ mở ở `http://127.0.0.1:28081`. Đổi cổng trong `setup/.env` chỉ có
tác dụng khi **tạo** cluster (chạy `down.sh` rồi `up.sh`). Test dùng `mlopskit.port_forward`, không dựa vào hai cổng này.

## KServe ở chế độ RawDeployment

`up.sh` đặt `inferenceservice-config`: `deploy.defaultDeploymentMode = "RawDeployment"` (KServe 0.21 gọi là "Standard",
vẫn nhận tên cũ) và `ingress.disableIngressCreation = true` (không có Istio). Mỗi InferenceService thành một
Deployment + Service thường; gọi bằng `port_forward` vào Service `<tên>-predictor`. Chỉ áp `ClusterServingRuntime` từ
`kserve-cluster-resources.yaml`: các `LLMInferenceServiceConfig` của bản v0.21.0 bị chính webhook KServe từ chối
(`can't evaluate field TrustRemoteCode`), và track không dùng LLM serving.

### Không có metrics-server: tắt HPA trong manifest bài tập

Ở RawDeployment, KServe mặc định tạo HorizontalPodAutoscaler cho predictor. Cluster không cài metrics-server nên HPA
hiện `<unknown>` và namespace đầy event `FailedGetResourceMetric` (không hỏng service, nhưng làm nhiễu `describe`/events
mà `mlopskit.wait_for` in ra khi fail). Manifest bài tập và capstone nên tắt autoscaler:

```yaml
metadata:
  annotations:
    serving.kserve.io/autoscalerClass: none
```

hoặc đặt `minReplicas` bằng `maxReplicas` trong `predictor`.

## Argo Workflows và artifact

- `argo-artifacts.yaml` dựng MinIO trong namespace `argo` và đặt kho artifact mặc định trong
  `workflow-controller-configmap` (`s3`, bucket `argo-artifacts`, tự tạo bucket). Thông tin đăng nhập (chỉ dùng local)
  được đưa vào container executor qua `executor.env` + `useSDKCreds`, nên Workflow ở **bất kỳ namespace nào** truyền
  artifact được mà không cần tạo Secret trong namespace đó.
- Executor cần quyền tạo `workflowtaskresults`. ClusterRole `mlops-argo-executor` có sẵn; `mlopskit.k8s_namespace()`
  gắn nó cho ServiceAccount `default` của namespace tạm. Tự tạo namespace thì chạy:
  `kubectl --context kind-mlops -n <ns> create rolebinding mlops-argo-executor --clusterrole=mlops-argo-executor --serviceaccount=<ns>:default`.
- Dữ liệu MinIO nằm trong `emptyDir`: mất khi pod khởi động lại. Đủ cho bài tập, không dùng làm kho lâu dài.

## Image tự build

`mlopskit.kind_load(tag)` nạp image từ Docker của máy vào node (`docker save --platform` rồi `kind load image-archive`,
vì `kind load docker-image` lỗi `content digest ... not found` với image đa nền tảng khi Docker dùng containerd image
store). Image đã nạp ở lại trong node; dọn khi node đầy:
`docker exec mlops-control-plane crictl rmi --prune` (xoá image không có container nào dùng).

## Tài nguyên

Đo trên laptop 16 nhân, 31 GB RAM sau khi mọi pod Running và không có workload bài tập: container node dùng khoảng
2,3 GB bộ nhớ anon (3,5 GB tính cả page cache), CPU nền 10-20% của một nhân. Phần lớn là `kube-apiserver` (~1,3 GB, do
các CRD lớn của KServe/Argo/cert-manager). Không dùng thì `docker stop mlops-control-plane`; bật lại bằng `up.sh`.
