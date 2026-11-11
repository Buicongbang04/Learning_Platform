# Lời giải: values file của quillo cho cluster công ty luật

Lời giải ở `values.yaml` cạnh tệp này:

```bash
SOLUTION=1 nice -n 15 uv run pytest tracks/fde/modules/06-k8s-at-customer/exercises/basic/02-values-for-customer -q
```

Đo 2026-11-11 trên máy của repo: ~15 s.

## Đọc luật của khách trước

```text
$ kubectl describe resourcequota quillo-quota
requests.cpu 200m/3, requests.memory 1Gi/4Gi, limits.memory 1Gi/5Gi, pods 1/12   (đã có it-backup-agent)
$ kubectl describe limitrange quillo-limits
Pod  cpu  max 2 / memory max 3Gi        PersistentVolumeClaim storage max 10Gi
$ kubectl get ns quillo --show-labels    (fde có quyền view; nhãn pod-security.kubernetes.io/enforce=restricted)
```

Ba hệ quả cho values:

1. **ResourceQuota có `requests.cpu`, `requests.memory`, `limits.memory`** ⇒ mọi container (cả initContainer) phải khai
   ba thứ đó, không thì pod bị từ chối "must specify ...".
2. **LimitRange kiểu `Pod` chỉ có `max`, không có `default`** ⇒ không ai điền hộ; có `max cpu` nên container còn phải
   khai `limits.cpu` (thiếu thì "No limit is specified").
3. **PSA restricted** ⇒ `runAsNonRoot: true`, `allowPrivilegeEscalation: false`, `capabilities.drop: [ALL]`,
   `seccompProfile: RuntimeDefault` cho mọi container. PSA chỉ đọc manifest: image pgvector và llama.cpp chạy root theo
   mặc định, nên còn phải đặt `runAsUser` khác 0, không thì pod qua admission rồi kubelet từ chối container
   (`CreateContainerConfigError: container has runAsNonRoot and image will run as root`). UID chọn theo image: 999
   (`postgres` trong pgvector), 10001 (quillo-api), 65534 (nobody) cho llama.cpp và initContainer chép model.

## Ngân sách

Còn lại sau `it-backup-agent`: CPU theo quy định IT 1000m − 200m = **800m**; `requests.memory` 4Gi − 1Gi = **3Gi**;
`limits.memory` 5Gi − 1Gi = **4Gi**. Tính cả một pod api thêm lúc rolling update (api là Deployment `RollingUpdate`;
worker, llm, embed dùng `Recreate`, db là StatefulSet).

| Thành phần | requests.cpu | requests.memory | limits.memory |
| --- | --- | --- | --- |
| api ×2 (gồm pod rolling update) | 200m | 512Mi | 1024Mi |
| worker | 50m | 128Mi | 384Mi |
| db | 100m | 256Mi | 512Mi |
| llm (initContainer 50m/64Mi/128Mi nhỏ hơn) | 250m | 1024Mi | 1536Mi |
| embed | 100m | 384Mi | 512Mi |
| **Tổng** | **700m ≤ 800m** | **2304Mi ≤ 3072Mi** | **3968Mi ≤ 4096Mi** |

`values-restricted.yaml` mẫu của sản phẩm (đi kèm mã nguồn) qua được PSA và quota rỗng, nhưng ở khách này trượt hai
chỗ: registry thiếu `/vendors/quillo`, và CPU: llm 500m + embed 250m ⇒ 1100m cho quillo + 200m của agent = 1300m >
1000m. Values mẫu là điểm xuất phát, không phải lời giải: số trong nó được tính cho một namespace trống.

`limits.memory` còn 128Mi: đủ cho lần nâng cấp api, **không** đủ để tăng replica api lên 2. Ghi điều này vào ghi chú
bàn giao cho IT.

## Registry

`image.registry: 10.0.2.101:5000/vendors/quillo`: helper `quillo.image` của chart bỏ host gốc (`ghcr.io`) và ghép
`<registry>/<đường dẫn>:<tag>`, nên một giá trị cho cả bốn image. Muốn chắc: `helm template … | grep image:`.

## Vì sao chấm bằng Pod dry-run

`kubectl apply --dry-run=server` một Deployment không chạy PSA `enforce` (chỉ `warn`) và không đụng quota: cả hai áp
cho **Pod**, do ReplicaSet tạo sau. Nên test vừa đòi không có `Warning:` khi apply, vừa tạo thử Pod từ template. Quota
cũng chỉ kiểm từng pod một với phần còn lại, không kiểm tổng của cả release, nên phần tổng (và pod thêm lúc rolling
update) phải tự tính như bảng trên.

## Chấp nhận khác

- Hạ `limits.cpu` (vd. llm 1500m) hay đặt `podSecurityContext` riêng từng thành phần thay vì phần chung: đạt, miễn đúng
  luật và đủ mức tối thiểu.
- Đặt `readOnlyRootFilesystem: true`: PSA restricted không đòi; chart mount emptyDir cho `/tmp` của api, worker và db,
  nhưng llama.cpp chưa được kiểm với root chỉ đọc, nên lời giải không đặt.
