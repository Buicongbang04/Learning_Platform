# Lời giải: hiện trường "quillo lên cluster production của công ty luật"

Lời giải ở `deploy.sh`, `values.yaml` và `push_images.py` cạnh tệp này (test chép mọi tệp trong thư mục vào
`/home/fde/deploy/`):

```bash
SOLUTION=1 nice -n 15 uv run pytest tracks/fde/modules/06-k8s-at-customer/exercises/intermediate/01-pods-not-up -q -s
```

Đo 2026-11-11 trên máy của repo: ~90 s cả bài (boot + API server sẵn sàng ~15 s, chép bundle 1,1 GB ~4 s, dựng image
models ~3 s, đẩy image ~14 s, `helm upgrade --wait` ~20 s, các kiểm tra ~15 s).

## Bốn lớp hỏng, theo thứ tự lộ ra

**1. LimitRange + quota: không pod nào được tạo.** Helm in `deployed` vì Deployment/StatefulSet được nhận; ReplicaSet
tạo pod thì bị admission từ chối. `kubectl get pods` rỗng, lý do nằm ở event của ReplicaSet/StatefulSet:

```text
$ kubectl get events --sort-by=.lastTimestamp | tail -3
Warning FailedCreate replicaset/quillo-api-6945cb8df9  Error creating: pods "quillo-api-…" is forbidden:
  [maximum cpu usage per Pod is 2.  No limit is specified, maximum memory usage per Pod is 3Gi.  No limit is specified]
```

LimitRange kiểu `Pod` chỉ có `max` (không sinh default), ResourceQuota có `requests.cpu`/`requests.memory`/
`limits.memory`: mọi container phải khai đủ requests và limits (cpu, memory). Chart mặc định để `resources: {}`.

**2. PSA restricted.** Thêm resources xong, lỗi kế tiếp cùng chỗ: `violates PodSecurity "restricted:latest":
allowPrivilegeEscalation != false …, runAsNonRoot != true …, seccompProfile …`. Đặt `podSecurityContext`/
`containerSecurityContext` chung và `runAsUser` riêng từng thành phần (pgvector và llama.cpp mặc định chạy root; thiếu
`runAsUser` thì pod qua admission nhưng container báo `CreateContainerConfigError`).

**3. Image không có trong registry.** Pod được tạo nhưng `ErrImagePull`: `10.0.2.101:5000/quillo-api:1.0.0: not
found`. Registry nội bộ chỉ có những gì đã đẩy lên; IT đặt `image.registry` nhưng không ai đẩy image. Máy không có Docker
(cũng không cần): `push_images.py` (thư viện chuẩn Python 3.8+, không cài gì) đọc OCI layout của `images/*.tar` và
`quillo-models.tar` (dựng tại chỗ bằng `ops/models_image.py`, sha256 so với `manifest.json`), đẩy blob rồi manifest qua
Registry HTTP API v2, bỏ host gốc như helper của chart (`ghcr.io/ggml-org/llama.cpp:server-b11718` →
`10.0.2.101:5000/ggml-org/llama.cpp:server-b11718`). `registries.yaml` của k3s đã khai registry này là HTTP, nên pull chạy
ngay; với `lawfirm-staging` thì đó lại là chỗ hỏng (bài intermediate 02).

**4. NetworkPolicy `default-deny`.** Pod `Running` nhưng api không `Ready`; `/healthz` qua port-forward trả `503`
`{"status":"degraded","checks":{"db":false,"llm":false,"embed":false}}`. Mọi kết nối giữa pod bị chặn trừ DNS.
`networkPolicy.enabled: true` của chart tạo đúng các luồng api→db/llm/embed, worker→db/embed; probe của kubelet và
`kubectl port-forward` không đi qua NetworkPolicy nên test vẫn tới được api.

## Các quyết định

- **Đẩy image từ trong VM** bằng Python chuẩn thay vì mang `skopeo`/`crane`: không phải ghim và chuyển thêm binary, và
  máy khách nào có Python 3.8+ cũng chạy được. Mang binary đã ghim sha256 (crane, regctl, skopeo tĩnh) trong `starter/`
  cũng đạt test và là lựa chọn đúng khi registry cần TLS/đăng nhập phức tạp.
- **`--wait --timeout 150s`** để `deploy.sh` thất bại có thông báo (in pod và event) thay vì "deployed" giả.
- **Không sửa `default-deny`** (ValidatingAdmissionPolicy của IT cũng chặn), không xin quyền mới: mọi thứ cần đều có
  trong Role `fde-deployer` (bài basic 01).
- Chạy lại `deploy.sh` an toàn: giải nén chỉ khi chưa có, blob đã có trên registry thì bỏ qua (HEAD trước khi upload),
  `helm upgrade --install` là idempotent; Secret `quillo-auth` giữ nguyên qua upgrade.

## Chấp nhận khác

- Tự viết NetworkPolicy (như bài basic 03) thay vì bật của chart: đạt nếu đủ luồng; `networkPolicy.apiFrom` có thể giới
  hạn nguồn gọi api. Allow-all trong namespace thì trượt tiêu chí "pod khác không nói chuyện với db/llm".
- Resources khác bảng trong `values.yaml` miễn vừa quota, LimitRange và node 2 vCPU: tổng `requests.cpu` của cả namespace
  vượt phần CPU còn lại của node thì pod `Pending` với `Insufficient cpu` dù quota còn chỗ.
