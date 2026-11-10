---
title: RBAC least privilege cho pipeline CI, nhóm on-call và trưởng nhóm
level: basic
services: []
files:
  - path: starter/k8s/ci-deployer.yaml
    note: ServiceAccount, Role, RoleBinding của CI, quyền quá rộng
  - path: starter/k8s/people.yaml
    note: Quyền cho người, chưa đúng
  - path: tests/test_rbac_ci.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/11-kubernetes-production/exercises/basic/02-rbac-ci-least-privilege -q -rs
---

## Mục tiêu

Thu hẹp một bộ quyền "cho chạy được trước đã" về đúng những gì pipeline CI cần để deploy và theo dõi rollout; cấp quyền xem cho nhóm
on-call và quyền exec cho đúng một người; chứng minh bằng ma trận `kubectl auth can-i` chứ không bằng cảm giác.

## Đề bài

Sửa `starter/k8s/` (test apply cả thư mục vào namespace của lab). Pipeline CI chạy `kubectl apply -f k8s/`, `kubectl rollout status`, và khi
rollout lỗi thì in log pod. Bí mật đến từ hệ thống khác (module 12), CI không đọc hay ghi Secret.

| Danh tính | Phải làm được | Không được |
| --- | --- | --- |
| ServiceAccount `ci-deployer` | get, list, watch, create, update, patch `deployments.apps`; get, list, watch `replicasets.apps`; create, patch `services`, `configmaps` (cộng get, list, watch); get, list, watch `pods`, `events`; get `pods/log` | Mọi thao tác trên `secrets`; delete, deletecollection bất cứ thứ gì; tạo pod trực tiếp, `pods/exec`; `jobs`, `cronjobs`; `serviceaccounts`; Role, RoleBinding; patch `replicasets`; mọi quyền ngoài namespace |
| Nhóm `olist-oncall` (user bất kỳ trong nhóm) | Xem workload, pod, log trong namespace | Đọc Secret, sửa gì, exec |
| User `lead@olist.example` | get, list `pods`; create `pods/exec` | Secret, xoá pod, sửa Deployment; user khác không được exec |

Exec là quyền mạnh, và đã có một lỗ ở chỗ này: tới Kubernetes 1.34 (bản của `devops-lab`), `kubectl exec` qua WebSocket (mặc định của
kubectl mới) chỉ bị kiểm verb `get` trên `pods/exec`, nên ai có `get pods/exec` là exec được; từ 1.35 API server đòi `create` cho cả
WebSocket (feature gate `AuthorizePodWebsocketUpgradeCreatePermission`, bật mặc định). Vì vậy không bao giờ cấp `get` trên `pods/exec`,
`pods/attach`, `pods/portforward` cho người chỉ được xem, và cấp exec bằng verb `create`.

Ràng buộc thêm: ServiceAccount `ci-deployer` có `automountServiceAccountToken: false` (không pod nào chạy bằng nó; CI lấy token ngắn hạn
từ bên ngoài); Role nào cũng không có `*` trong `apiGroups`, `resources` hay `verbs`; không ClusterRoleBinding. Nhóm on-call dùng
ClusterRole `view` có sẵn qua RoleBinding, không tự viết lại.

**Cách test chấm.** `KubeLab` apply `k8s/`, rồi hỏi API server từng ô trong bảng bằng `lab.can_i(...)`: testkit chạy `kubectl auth can-i
<verb> <resource> -n <namespace của lab> --as=system:serviceaccount:<namespace>:ci-deployer` (hay `--as=<user> --as-group=<nhóm>`) bằng
kubeconfig admin, chỉ đọc, vì token của lab không có quyền `impersonate`.

| Kiểm | Cách |
| --- | --- |
| Apply | Thư mục `k8s/` apply được bằng quyền của lab |
| ServiceAccount | `automountServiceAccountToken: false` |
| CI được phép | 15 cặp verb, resource ở cột giữa, cộng `get pods --subresource=log` trả `yes` |
| CI bị cấm | 15 cặp ở cột phải trả `no`; `create pods/exec` và `list deployments --all-namespaces` trả `no` |
| Không wildcard | Đọc tệp: không có `*` trong Role |
| On-call | Với `--as-group=olist-oncall`: list pods, get pods/log, list deployments là `yes`; get secrets, patch deployments, create pods/exec là `no`; user không trong nhóm thì list pods là `no` |
| Lead | `lead@olist.example`: create pods/exec, get pods là `yes`; get secrets, delete pods, patch deployments là `no`; user khác create pods/exec là `no` |

Khoảng 20 giây. Thử tay (admin có `impersonate` nên `--as` chạy được):

```bash
export KUBECONFIG=~/.kube/devops-lab.yaml &&
kubectl create namespace rbac-b02 &&
kubectl -n rbac-b02 apply -f tracks/devops/modules/11-kubernetes-production/exercises/basic/02-rbac-ci-least-privilege/starter/k8s/ &&
kubectl -n rbac-b02 auth can-i --list --as=system:serviceaccount:rbac-b02:ci-deployer &&
kubectl -n rbac-b02 auth can-i get secrets --as=system:serviceaccount:rbac-b02:ci-deployer
```

Xong thì `kubectl delete namespace rbac-b02`.

## Tiêu chí đạt

- Mọi test pass.
- Giải thích được vì sao `list secrets` nguy hiểm ngang `get secrets`, và vì sao quyền `patch deployments` đã là quyền mạnh.
- Viết được bằng lệnh imperative (`kubectl create role`, `kubectl create rolebinding --group/--user/--serviceaccount`) cùng bộ quyền.

## Gợi ý

### Gợi ý 1

`kubectl api-resources -o wide` cho biết nhóm API và verb của từng resource; `replicasets` thuộc `apps`, `events` và `pods` thuộc nhóm
rỗng `""`. Subresource là một chuỗi riêng trong `resources`: `pods/log`, `pods/exec`.

### Gợi ý 2

`kubectl rollout status` đọc Deployment và ReplicaSet; `kubectl apply` cần get để so sánh rồi create hay patch. RoleBinding có thể trỏ
`roleRef` tới một ClusterRole (`kind: ClusterRole`): quyền vẫn chỉ trong namespace của binding. Subject là nhóm hay user thì
`apiGroup: rbac.authorization.k8s.io`.
