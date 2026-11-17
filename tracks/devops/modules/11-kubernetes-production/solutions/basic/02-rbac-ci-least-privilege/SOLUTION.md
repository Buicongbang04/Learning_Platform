# Lời giải: RBAC least privilege cho CI, on-call và trưởng nhóm

Lời giải nằm trong `k8s/ci-deployer.yaml` và `k8s/people.yaml`.

## CI

Starter cấp mọi verb trên Deployment, ReplicaSet, StatefulSet, DaemonSet, và cả `secrets`, `pods/exec`, delete: một token CI bị lộ (log
CI, cache, dependency độc hại trong pipeline) là xoá được cả namespace và đọc được mọi bí mật. Bản sửa:

| Rule | Vì sao |
| --- | --- |
| `deployments` get, list, watch, create, update, patch | `kubectl apply` đọc bản hiện có rồi tạo hay patch; `rollout status` watch Deployment |
| `replicasets` get, list, watch | `rollout status` và `rollout history` đọc ReplicaSet; CI không sửa ReplicaSet (Deployment controller làm) |
| `services`, `configmaps` get, list, watch, create, update, patch | Manifest của service gồm chúng |
| `pods`, `events` get, list, watch | In trạng thái và lý do khi rollout lỗi |
| `pods/log` get | In log pod lỗi trong output của CI |

Không có delete: xoá là thao tác hiếm, làm bằng người có quyền cao hơn hay GitOps prune (module 12). Không có Secret: `list secrets` trả về
**nội dung** mọi Secret, nên chỉ cấp list mà không cấp get vẫn là đọc được hết. `automountServiceAccountToken: false`: không pod nào chạy
bằng `ci-deployer`, nên không pod nào cần token của nó. Token cho CI ngoài cluster: GitHub Actions OIDC đổi lấy token ngắn hạn
(EKS, GKE, AKS hỗ trợ), hoặc tối thiểu `kubectl create token ci-deployer --duration=1h` mỗi lần chạy, không Secret token vĩnh viễn.

`patch deployments` vẫn là quyền mạnh: ai patch được Deployment là chạy được image bất kỳ với ServiceAccount bất kỳ trong namespace (đổi
`serviceAccountName` sang một account mạnh hơn). Lớp chặn tiếp theo: admission policy chỉ cho image từ registry của công ty, cấm đổi
`serviceAccountName`, Pod Security `restricted`.

## Người

- Nhóm `olist-oncall`: RoleBinding tới ClusterRole `view` có sẵn. `view` cố ý không đọc Secret, không exec; quyền theo nhóm (đến từ OIDC
  của công ty) nên vào hay rời team on-call chỉ là đổi nhóm ở IdP, không sửa cluster. Starter dùng `edit`: on-call sửa được workload và
  đọc Secret.
- `lead@olist.example`: Role `debugger` chỉ get, list `pods` và create `pods/exec`. Exec là quyền rất mạnh (chạy lệnh trong container,
  đọc biến môi trường có bí mật), nên cấp cho đúng người, có audit log; thay dần bằng `kubectl debug` với ephemeral container hay quy trình
  "break glass" có thời hạn.

## Lệnh imperative tương đương

```bash
kubectl create serviceaccount ci-deployer
kubectl create role ci-deployer --verb=get,list,watch,create,update,patch --resource=deployments.apps,services,configmaps
kubectl create role ci-reader --verb=get,list,watch --resource=replicasets.apps,pods,events
kubectl create role ci-logs --verb=get --resource=pods/log
kubectl create rolebinding ci-deployer --role=ci-deployer --serviceaccount=rbac-b02:ci-deployer
kubectl create rolebinding ci-reader --role=ci-reader --serviceaccount=rbac-b02:ci-deployer
kubectl create rolebinding ci-logs --role=ci-logs --serviceaccount=rbac-b02:ci-deployer
kubectl create rolebinding oncall-view --clusterrole=view --group=olist-oncall
kubectl create role debugger --verb=get,list --resource=pods
kubectl create rolebinding lead-debugger --role=debugger --user=lead@olist.example
```

`kubectl create role` không gộp nhiều nhóm verb khác nhau trong một lệnh, nên bản imperative tách thành nhiều Role; bản YAML gọn hơn. Kiểm
cả ma trận trong CI của repo hạ tầng để không ai lặng lẽ nới quyền.
