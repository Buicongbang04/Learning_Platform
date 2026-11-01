---
title: CRD Storefront có schema và CEL, cộng một operator nhỏ reconcile Deployment theo spec
level: advanced
services: []
files:
  - path: starter/crd.yaml
    note: CRD chưa có schema, status, cột in ra
  - path: starter/operator/controller.py
    note: Vòng lặp của controller, chưa reconcile
  - path: starter/operator/rbac.yaml
    note: ServiceAccount, Role, RoleBinding của operator
  - path: starter/operator/deployment.yaml
    note: Deployment chạy controller
  - path: starter/operator/kustomization.yaml
    note: configMapGenerator đóng controller.py vào ConfigMap
  - path: tests/test_crd_operator.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/11-kubernetes-production/exercises/advanced/02-crd-operator -q -rs
---

## Mục tiêu

Mở rộng API của Kubernetes bằng một CustomResourceDefinition chặn input sai ngay ở API server, rồi viết một controller theo đúng mẫu
operator: reconcile theo trạng thái, idempotent, sở hữu object con bằng `ownerReferences`, báo `status`, chạy bằng ServiceAccount chỉ có
quyền trong namespace của nó.

## Đề bài

Team marketing muốn tự bật trang khuyến mãi bằng một object:

```yaml
apiVersion: lab.olist.test/v1
kind: Storefront
metadata:
  name: spring-sale
spec:
  replicas: 2
  message: Olist Spring Sale
```

Operator biến mỗi Storefront thành ConfigMap `<tên>-web` (khoá `index.html` chứa `spec.message`) và Deployment `<tên>-web` chạy
`nginx:1.30.6-alpine` với `spec.replicas` pod, mount ConfigMap vào `/usr/share/nginx/html`.

| Phần | Yêu cầu |
| --- | --- |
| CRD | `storefronts.lab.olist.test`, nhóm `lab.olist.test`, kind `Storefront`, Namespaced, bản `v1` |
| Schema | `spec` bắt buộc; `spec.replicas` số nguyên 1 tới 5, bắt buộc; `spec.message` chuỗi 1 tới 80 ký tự, bắt buộc; `spec.maintenance` boolean mặc định `false`; luật CEL: `maintenance` là true thì `replicas` phải là 1, thông báo chứa chữ `maintenance` |
| Status | Subresource `status` với `readyReplicas`, `phase` (`Ready` khi readyReplicas bằng spec.replicas, ngược lại `Progressing`), `observedGeneration` |
| Cột | `kubectl get storefronts` in `NAME REPLICAS READY PHASE AGE` |
| Controller | Mỗi vòng: tạo hay cập nhật ConfigMap và Deployment con khớp spec, có `ownerReferences` (`controller: true`) trỏ Storefront; ghi status qua subresource; Deployment con bị xoá tay thì tạo lại |
| RBAC | Role của ServiceAccount `storefront-operator`: đọc Storefront, ghi `storefronts/status`, ghi Deployment và ConfigMap; không Secret, không tạo pod trực tiếp, không xoá Storefront, không gì ngoài namespace |

Tệp dùng chuỗi `lab.olist.test` cho nhóm API ở mọi chỗ (CRD, Role, biến `STOREFRONT_GROUP` của Deployment). Tên CRD là duy nhất trên cả
cluster, nên test thay chuỗi đó bằng nhóm riêng của lab (`<namespace>.olist.test`) và gắn nhãn của lab vào CRD trước khi apply.
`controller.py` chỉ dùng thư viện chuẩn của Python (image Olist Shop), đọc token ServiceAccount mount sẵn; starter có sẵn hàm gọi API.

**Cách test chấm.** `KubeLab(allow=("CustomResourceDefinition",))`: lab chỉ cho tạo CRD thuộc nhóm riêng, và cho Role của lab ghi resource
của nhóm đó.

| Kiểm | Cách |
| --- | --- |
| Apply | CRD apply được, `Established`; `operator/` (Kustomize) apply được, operator rollout xong trong 120 giây |
| Schema từ chối | `kubectl apply --dry-run=server` bị từ chối, lỗi nhắc đúng trường, với: replicas 0, 6, `"two"`; message rỗng, 81 ký tự, thiếu; maintenance true với replicas 2 |
| Schema nhận | maintenance true với replicas 1 được nhận; không ghi maintenance thì server điền `false` |
| Reconcile | Tạo Storefront `spring-sale` (2, `Olist Spring Sale`): trong 90 giây Deployment `spring-sale-web` có 2 pod ready, có ownerReference controller trỏ đúng uid; `wget` trong pod trả trang có message |
| Status, cột | Trong 90 giây `phase: Ready`, `readyReplicas: 2`, `observedGeneration` bằng `metadata.generation`; tiêu đề `kubectl get storefronts` đúng như trên |
| Đổi spec | Patch replicas 3, message mới: Deployment lên 3, ConfigMap đổi nội dung, status lên 3, mỗi việc trong 90 giây |
| Lệch | Xoá tay Deployment con: operator tạo lại trong 90 giây |
| Xoá | Xoá Storefront: Deployment và ConfigMap con biến mất trong 90 giây (garbage collector) |
| Quyền | `lab.can_i` cho `storefront-operator`: list storefronts, patch storefronts/status, patch deployments là yes; list storefronts mọi namespace, get secrets, create pods, delete storefronts là no |

Khoảng 40 giây khi đúng, 2 phút trên starter.

## Tiêu chí đạt

- Test pass.
- Rubric trong `SOLUTION.md` đạt từ 7/10.
- Giải thích được vì sao controller đọc lại toàn bộ trạng thái mỗi vòng thay vì phản ứng theo từng sự kiện, và điều gì xảy ra nếu chạy hai
  bản operator cùng lúc.

## Gợi ý

### Gợi ý 1

`kubectl explain customresourcedefinition.spec.versions.schema.openAPIV3Schema` và mục "Validation rules" trong tài liệu CRD cho
`x-kubernetes-validations`. Luật CEL đặt trên object `spec` dùng `self.maintenance`, `self.replicas`. Thử schema bằng `kubectl apply
--dry-run=server` một object sai trước khi viết controller.

### Gợi ý 2

Server-side apply (`PATCH` với `Content-Type: application/apply-patch+yaml`, tham số `fieldManager`, `force=true`) tạo nếu chưa có, cập
nhật nếu đã có, trong một lời gọi: đúng tính idempotent mà controller cần. Status đi qua đường `.../storefronts/<tên>/status` với merge patch.
ownerReference cần `uid` của Storefront; không đặt `blockOwnerDeletion` (cần quyền mà operator không có).
