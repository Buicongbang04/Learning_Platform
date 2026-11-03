# Cluster kind `mlops` (Giai đoạn 3–4 track MLOps)

Một cluster Kubernetes local duy nhất, tên `mlops`, context `kind-mlops`, dùng chung cho module 13, capstone m12 và
(với add-on senior, xem mục [Add-on senior](#add-on-senior---senior)) module 14–18.
Test không bao giờ tạo hay xoá cluster: chúng gọi `mlopskit.require_kind()` và skip kèm lệnh dựng khi cluster chưa có.

| Thành phần | Bản ghim | Ghi chú |
| --- | --- | --- |
| kind | v0.33.0 | cài vào `~/.local/bin/kind`, kiểm sha256 |
| Kubernetes (node image) | v1.35.8, ghim theo digest | 1 node control-plane |
| kubectl | v1.35.8 | cài vào `~/.local/bin/kubectl`, kiểm sha256 |
| cert-manager | v1.20.4 | KServe cần để cấp chứng chỉ cho webhook |
| KServe | v0.21.0 | chế độ **RawDeployment**, không Knative, không Istio; tắt tạo Ingress |
| Argo Workflows | v4.1.5 | namespace `argo`, controller theo dõi mọi namespace |
| MinIO + mc (kho artifact của Argo) | `pgsty/minio`, `pgsty/mc` `RELEASE.2026-08-04T00-00-00Z`, ghim digest | Deployment `argo-artifacts` trong `argo`, dữ liệu `emptyDir` |

Phiên bản, ngày phát hành và checksum nằm ở `versions.env` (mọi bản phát hành ≥2 tuần trước ngày thêm 2026-11-03).
`up.sh` kiểm sha256 của mọi tệp tải về (binary và manifest) **trước** khi dùng; không có `curl | bash`, không cần `sudo`.
Binary chọn theo kiến trúc máy (`uname -m`: amd64 hoặc arm64, checksum riêng từng kiến trúc); kiến trúc khác thì dừng
ngay. Helper `mlopskit` và `down.sh` ưu tiên bản ghim trong `~/.local/bin` trước bản trên PATH.

Rủi ro chấp nhận (ghi cả trong `versions.env`):

- Manifest upstream (cert-manager, KServe, Argo, metrics-server, KEDA, Kueue) kéo image theo **tag** (vd. `kserve/kserve-controller:v0.21.0`), không
  theo digest. Tệp manifest được ghim sha256 nên không ai đổi được tag trong đó, nhưng nội dung tag trên registry thì
  tin vào nhà phát hành. Không viết lại thành digest để manifest giữ đúng bản phát hành.
- `pgsty/minio`, `pgsty/mc` là bản build của bên thứ ba (MinIO ngừng phát hành image Docker chính thức từ cuối 2025),
  cùng họ image với stack Compose `setup/mlops`, ghim theo digest.

`up.sh` **không đổi current-context** của kubectl: `kind create cluster` và `kind export kubeconfig` vẫn ghi context
`kind-mlops` vào kubeconfig, nhưng current-context cũ được trả lại khi script kết thúc (kể cả khi lỗi; current-context
trống thì vẫn để trống). Helper luôn truyền `--context kind-mlops`; tự gõ lệnh thì cũng thêm `--context kind-mlops`.
Cổng trong `MLOPS_KIND_HTTP_PORT`/`MLOPS_KIND_HTTPS_PORT` phải là số 1024-65535, sai thì script dừng trước khi làm gì.

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

## Add-on senior (`--senior`)

Module 14–18 cần thêm ba thành phần, cài bằng `bash setup/mlops/kind/up.sh --senior` (chạy toàn bộ `up.sh` như trên rồi
cài thêm; không bắt buộc cho module 13). Chạy lại an toàn; không đổi current-context. Test cần add-on gọi
`mlopskit.require_senior_addons()` và skip kèm đúng lệnh này khi thiếu CRD của KEDA hoặc Kueue.

| Thành phần | Bản ghim | Phát hành | Ghi chú |
| --- | --- | --- | --- |
| metrics-server | v0.9.0 | 2026-07-13 | `components.yaml`; `up.sh` thêm `--kubelet-insecure-tls` (kubelet của kind dùng chứng chỉ tự ký). Cho `kubectl top`, HPA theo CPU/RAM |
| KEDA | v2.21.0 | 2026-09-23 | `keda-2.21.0.yaml` (CRD + operator + metrics apiserver + admission webhook), namespace `keda`. Webhook của KEDA là `failurePolicy: Ignore` |
| Kueue | v0.20.2 | 2026-10-15 | `manifests.yaml`, namespace `kueue-system`, API `kueue.x-k8s.io/v1beta2` |

Ngày lấy từ GitHub Releases (`published_at`, kiểm 2026-11-04), mọi bản ≤ 2026-10-21; checksum là digest asset của
release, `up.sh` kiểm sha256 trước khi dùng. Hai chỗ sửa so với manifest gốc, làm trên bản đã kiểm checksum (bản gốc giữ
nguyên trong `~/.cache/mlops-kind`, bản sửa có hậu tố `-kind`/`-batchjob`), script dừng nếu không thấy đúng chỗ cần sửa:

- metrics-server: thêm `--kubelet-insecure-tls`. Không có cờ này metrics-server không scrape được kubelet của kind và
  `kubectl top` báo `Metrics API not available`.
- Kueue: `integrations.frameworks` chỉ còn `batch/job`, và bỏ 8 webhook `m|v` + `pod`, `deployment`, `statefulset`,
  `leaderworkerset`. Bản gốc chặn **mọi** lệnh tạo Pod/Deployment ở mọi namespace (trừ `kube-system`, `kueue-system`)
  qua webhook `failurePolicy: Fail`: khi controller Kueue chưa lên (vd. vừa khởi động lại node) thì KServe, Argo và bài
  module 13 không tạo được pod. Bài Kueue của module 14 dùng `batch/v1` Job (nhãn `kueue.x-k8s.io/queue-name`), không
  cần các tích hợp kia.

Webhook `mjob.kb.io`/`vjob.kb.io` của Kueue vẫn `failurePolicy: Fail` cho **mọi** `batch/v1` Job ngoài `kube-system` và
`kueue-system`, kể cả Job không có nhãn queue: ngay sau khi node khởi động lại (hoặc `docker start mlops-control-plane`),
tạo Job bị từ chối (`failed calling webhook "mjob.kb.io" ... connection refused`) tới khi controller Kueue lên, thường
30–60 giây. Cách chờ:

```bash
kubectl --context kind-mlops -n kueue-system wait --for=condition=Available deployment/kueue-controller-manager --timeout=180s
bash setup/mlops/kind/up.sh --senior    # hoặc chạy lại up.sh: cuối bước --senior đã thử webhook bằng dry-run
```

Test không phải tự chờ: `mlopskit.require_senior_addons()` thử `create --dry-run=server` một ResourceFlavor (đi qua cùng
webhook server) tới khi được, tối đa 120 giây, quá hạn thì fail kèm lệnh xem log. Chọn chờ trong `require_senior_addons`
thay vì thêm helper riêng vì mọi test dùng Kueue đã gọi nó trước, và chi phí khi đã sẵn sàng chỉ một lệnh dry-run.

Cuối bước `--senior`, script chờ APIService `v1beta1.metrics.k8s.io` và `v1beta1.external.metrics.k8s.io` Available,
`kubectl top node` trả số, và webhook Kueue nhận `create --dry-run=server` một ResourceFlavor thử.

Đo trên laptop 16 nhân, 31 GB RAM (2026-11-04), cluster rảnh, không workload bài tập:

| | Thời gian `up.sh --senior` | Bộ nhớ container node (`docker stats`) |
| --- | --- | --- |
| Trước khi cài | | 3,17 GiB |
| Lần đầu (kéo 5 image) | 113 giây | |
| Chạy lại | 9 giây | |
| Sau khi cài, đã ổn định 3 phút | | 3,72 GiB (**+0,55 GiB**, dưới ngân sách 1,5 GB) |

`kubectl top pods`: Kueue ~145 MiB, KEDA 3 pod ~80 MiB, metrics-server ~26 MiB; phần còn lại là `kube-apiserver` lớn lên
vì thêm CRD của KEDA và Kueue. Gỡ add-on mà giữ cluster: không có lệnh riêng, chạy `down.sh` rồi `up.sh` (không `--senior`).

Tài nguyên cluster-scoped (ClusterQueue, ResourceFlavor, PriorityClass, WorkloadPriorityClass...) trong test chỉ tạo qua
`mlopskit.cluster_scoped(manifest)` (tên chứa run id, nhãn `mlops-ex-run=<uuid8>`, xoá trong `finally`); extended
resource giả trên node chỉ qua `mlopskit.fake_extended_resource(...)`. `mlopskit.leftovers()` liệt kê cả hai loại.

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

### Không có metrics-server (khi chưa chạy `--senior`): tắt HPA trong manifest bài tập

Ở RawDeployment, KServe mặc định tạo HorizontalPodAutoscaler cho predictor. Cluster cơ bản không cài metrics-server nên HPA
hiện `<unknown>` và namespace đầy event `FailedGetResourceMetric` (không hỏng service, nhưng làm nhiễu `describe`/events
mà `mlopskit.wait_for` in ra khi fail). Manifest bài tập và capstone nên tắt autoscaler:

```yaml
metadata:
  annotations:
    serving.kserve.io/autoscalerClass: none
```

hoặc đặt `minReplicas` bằng `maxReplicas` trong `predictor`. Bài module 13 giữ cách này kể cả khi cluster đã có
metrics-server (từ `--senior`), để không phụ thuộc vào add-on.

## Argo Workflows và artifact

- `argo-artifacts.yaml` dựng MinIO trong namespace `argo` và đặt kho artifact mặc định trong
  `workflow-controller-configmap` (`s3`, bucket `argo-artifacts`). Sidecar `provision` (mc) tạo bucket và user
  `mlops-argo-workflow` chỉ có quyền đọc/ghi/xoá object trong bucket đó (policy `argo-artifacts-rw`), mỗi lần pod khởi động.
  Root của MinIO chỉ nằm trong Secret `argo/argo-artifacts`.
- Executor nhận khoá của user giới hạn đó qua `executor.env` + `useSDKCreds`, nên Workflow ở **bất kỳ namespace nào**
  truyền artifact được mà không cần Secret trong namespace đó. Không dùng `accessKeySecret`/`secretKeySecret`: Argo đọc
  Secret đó trong namespace của Workflow, tức phải chép khoá vào mọi namespace bài tập (lan rộng hơn, không hẹp hơn).
  Khoá này chỉ dùng cho cluster local, ai đọc được ConfigMap trong `argo` hoặc env của pod workflow đều thấy.
- NetworkPolicy `argo-artifacts` chỉ cho pod có nhãn `workflows.argoproj.io/workflow` (pod của Workflow, mọi namespace)
  và pod trong namespace `argo` gọi tới MinIO:9000; pod không có nhãn đó bị chặn (kindnet thực thi NetworkPolicy, có test).
  Đây chỉ là hàng rào chống truy cập **vô tình**, không phải ranh giới bảo mật: pod nào tự gắn nhãn
  `workflows.argoproj.io/workflow` vẫn vào được, và ai tạo được pod thì cũng tự gắn được nhãn. Đủ cho lab local, không
  dùng cách này cho cluster nhiều người dùng.
- Khoá của user workflow có ở hai chỗ trong `argo-artifacts.yaml`: Secret (`workflow-accesskey`/`workflow-secretkey`, sidecar
  dùng để tạo user) và `executor.env` của `workflow-controller-configmap` (Argo không đọc env executor từ Secret dùng chung
  cho mọi namespace). Test `test_argo_artifacts_scoped_and_isolated` bắt hai chỗ phải khớp. `up.sh` gắn sha256 của cả tệp
  vào annotation `mlops/config-sha256` của pod MinIO, nên sửa tệp (đổi khoá, policy, script) rồi chạy lại `up.sh` sẽ
  rollout pod và sidecar tạo lại user theo khoá mới (dữ liệu artifact trong `emptyDir` mất theo pod cũ).
- Executor cần quyền tạo `workflowtaskresults`. ClusterRole `mlops-argo-executor` có sẵn; `mlopskit.k8s_namespace()`
  gắn nó cho ServiceAccount `default` của namespace tạm. Tự tạo namespace thì chạy:
  `kubectl --context kind-mlops -n <ns> create rolebinding mlops-argo-executor --clusterrole=mlops-argo-executor --serviceaccount=<ns>:default`.
- Dữ liệu MinIO nằm trong `emptyDir`: mất khi pod khởi động lại. Đủ cho bài tập, không dùng làm kho lâu dài.

## Image tự build

`mlopskit.kind_load(tag)` nạp image từ Docker của máy vào node (`docker save --platform` rồi `kind load image-archive`,
vì `kind load docker-image` lỗi `content digest ... not found` với image đa nền tảng khi Docker dùng containerd image
store). Tệp tar tạm nằm ở `~/.cache/mlops-kind/load` (quyền 0700, trên đĩa; `/tmp` của máy là tmpfs) và bị xoá ngay sau khi nạp. Image đã nạp ở lại trong node; dọn khi node đầy:
`docker exec mlops-control-plane crictl rmi --prune` (xoá image không có container nào dùng).

## Tài nguyên

Đo trên laptop 16 nhân, 31 GB RAM sau khi mọi pod Running và không có workload bài tập: container node dùng khoảng
2,3 GB bộ nhớ anon (3,5 GB tính cả page cache), CPU nền 10-20% của một nhân. Phần lớn là `kube-apiserver` (~1,3 GB, do
các CRD lớn của KServe/Argo/cert-manager). Không dùng thì `docker stop mlops-control-plane`; bật lại bằng `up.sh`.
