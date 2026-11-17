# Lời giải: yêu cầu quyền tối thiểu gửi platform team

## Hướng làm

Đi từ lệnh tới API: liệt kê mọi lệnh của vòng đời, với mỗi lệnh ghi object và verb nó gọi (`helm template` cho biết chart
tạo kind gì; Helm 3 lưu release trong Secret; `kubectl exec`/`port-forward` là subresource `create`). Gộp lại thành Role,
rồi viết lý do theo đúng các dòng đó. Thứ không có trong danh sách thì không xin.

## Bài mẫu

### 1. Email

> Chào anh/chị platform team,
>
> Để cài và vận hành quillo 1.0.0 trong namespace `quillo` (ngày cài dự kiến 20/11), vendor đề nghị một ServiceAccount
> `quillo/quillo-deployer` gắn Role `quillo-deployer` đính kèm. Quyền chỉ trong namespace `quillo`, không có quyền cấp
> cluster, không có `*`, không sửa RBAC, quota, LimitRange hay NetworkPolicy của IT. Bảng lý do từng verb ở mục 3.
> Người dùng: 2 kỹ sư FDE (tên trong ticket), token có hạn 8 giờ (`kubectl create token --duration=8h`) do anh/chị cấp
> mỗi phiên, không cấp token vĩnh viễn. Thu hồi: xoá RoleBinding `quillo-deployer`. Trước ngày cài chúng tôi chạy script
> kiểm quyền (mục 5) và gửi lại kết quả.

### 2. Role YAML

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata: {name: quillo-deployer, namespace: quillo}
rules:
  - apiGroups: [apps]
    resources: [deployments, statefulsets]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [apps]
    resources: [replicasets]
    verbs: [get, list, watch]
  - apiGroups: [""]
    resources: [services, configmaps, persistentvolumeclaims]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [""]
    resources: [secrets]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [""]
    resources: [pods, pods/log, events]
    verbs: [get, list, watch]
  - apiGroups: [""]
    resources: [pods]
    verbs: [delete]
  - apiGroups: [""]
    resources: [pods/exec, pods/portforward]
    verbs: [get, create]
  - apiGroups: [networking.k8s.io]
    resources: [networkpolicies]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [""]
    resources: [resourcequotas, limitranges]
    verbs: [get, list]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata: {name: quillo-deployer, namespace: quillo}
roleRef: {apiGroup: rbac.authorization.k8s.io, kind: Role, name: quillo-deployer}
subjects:
  - {kind: ServiceAccount, name: quillo-deployer, namespace: quillo}
```

### 3. Bảng lý do

| Resource | Verb | Cần cho | Rủi ro | Bỏ được không |
| --- | --- | --- | --- | --- |
| deployments, statefulsets | get…delete | `helm upgrade --install/rollback/uninstall` tạo, sửa, xoá api, worker, llm, embed, db | Chạy workload tuỳ ý trong namespace (vẫn dưới PSA, quota) | Không |
| replicasets | get, list, watch | `helm --wait` và `kubectl rollout status` theo dõi rollout | Chỉ đọc | Bỏ thì `--wait` không biết khi nào xong |
| services, configmaps, PVC | get…delete | Chart tạo Service, PVC inbox/db (qua StatefulSet), ConfigMap extension | Xoá PVC = mất dữ liệu | `delete` PVC bỏ được: uninstall để lại PVC, nhờ IT xoá |
| secrets | get…delete | Chart tạo Secret `quillo-auth`; **Helm 3 lưu mỗi revision trong Secret `sh.helm.release.v1.quillo.vN`**; `lookup` đọc Secret cũ | Đọc mọi Secret trong namespace | Không: thiếu là `helm install` lỗi ngay |
| pods, pods/log, events | get, list, watch | Gỡ lỗi: trạng thái, log, sự kiện | Log có thể chứa dữ liệu nghiệp vụ | Không |
| pods | delete | Khởi động lại pod treo | Gián đoạn dịch vụ | Được (dùng `rollout restart` = patch deployment) |
| pods/exec | get, create | `ops/backup.sh --kubectl` chạy `pg_dump` trong pod db; gỡ lỗi | Shell trong container, đọc được dữ liệu DB | Không, trừ khi platform team chạy backup hộ |
| pods/portforward | get, create | Kiểm `/healthz`, `/api/ask` sau cài khi chưa có Route/Ingress | Mở đường vào pod từ máy FDE | Được sau khi có Ingress |
| networkpolicies | get…delete | Chart tạo policy cho đúng luồng quillo (default-deny có sẵn) | Mở luồng ngoài ý muốn | Không; đề nghị IT giữ admission chặn sửa `default-deny` |
| resourcequotas, limitranges | get, list | Kiểm values vừa quota trước khi cài | Chỉ đọc | Được, nhưng mất bước kiểm trước |

Vì sao `get` **và** `create` cho `pods/exec`, `pods/portforward`: kubectl đời mới mở hai kênh này qua WebSocket (request
HTTP GET), còn kiểu cũ là POST; tuỳ phiên bản API server và feature gate mà verb được kiểm là `get` hay `create`. Cấp cả
hai để không phụ thuộc phiên bản kubectl của người dùng; rủi ro không đổi vì cả hai đều mở cùng một kênh.

### 4. Không xin

- **Quyền cluster** (`nodes`, `namespaces`, `storageclasses`, `persistentvolumes`, CRD, ClusterRole): chart không tạo
  object cluster-scoped (`helm template … | grep '^kind:'` chỉ ra Deployment, StatefulSet, Service, Secret, PVC,
  NetworkPolicy). Cần biết node có bao nhiêu CPU, StorageClass mặc định: hỏi bằng ticket.
- **`roles`, `rolebindings`, `escalate`, `bind`, `impersonate`**: ai sửa được RBAC là tự cấp được mọi quyền.
- **`*`** ở bất kỳ đâu, `serviceaccounts/token` (tự tạo token), `resourcequotas` ghi.
- **`deletecollection`**: không lệnh nào của vòng đời cần.
- Namespace: platform team tạo, gắn nhãn PSA. Nâng cấp cần CRD (bản sau) sẽ gửi yêu cầu riêng.

RBAC cho phép không có nghĩa admission cho phép: PSA, quota, ValidatingAdmissionPolicy vẫn chặn sau RBAC. Vì thế email
không xin "quyền sửa PSA" mà gửi values đã qua `--dry-run=server`.

### 5. Cách kiểm sau khi cấp

```sh
kubectl auth whoami                                   # đúng system:serviceaccount:quillo:quillo-deployer
sh can_i.sh checks.txt                                # script bài basic 01: can_install true, mọi need = true
kubectl auth can-i get nodes                          # no (mong đợi)
kubectl auth can-i create rolebindings -n quillo      # no (mong đợi)
helm upgrade --install quillo quillo-1.0.0.tgz -n quillo -f values.yaml --dry-run=server
```

Platform team kiểm trước khi cấp: `kubectl auth can-i --list -n quillo --as=system:serviceaccount:quillo:quillo-deployer`.

## Rubric (10 điểm, đạt từ 7)

| Tiêu chí | Điểm |
| --- | --- |
| Role/RoleBinding hợp lệ, chỉ trong namespace, không `*`, không quyền RBAC/impersonate | 2 |
| Đủ cho vòng đời: Secret cho release Helm, `pods/exec` cho backup, `pods/portforward`, NetworkPolicy, đọc pod/log/event | 2 |
| Bảng lý do có lệnh cụ thể và rủi ro cho từng cặp resource+verb | 2 |
| Mục "không xin" có lý do và đường thay thế | 1 |
| Phân biệt RBAC với admission (PSA, quota, policy) | 1 |
| Email: phạm vi, người dùng, thời hạn token, cách thu hồi | 1 |
| Cách kiểm sau khi cấp, có kết quả mong đợi cả "yes" lẫn "no" | 1 |

Trừ điểm: xin `cluster-admin`/`admin` ClusterRole qua RoleBinding mà không giải thích vì sao Role hẹp không đủ (−2);
thiếu `secrets` (Helm không cài được) (−1).
