# Lời giải: CRD Storefront và operator nhỏ

`crd.yaml` và `operator/` cạnh tệp này là **một** lời giải qua test; rubric dưới đây chấm nội dung.

## Hướng làm

**CRD.** Schema structural: `spec` bắt buộc với `replicas` (integer, `minimum: 1`, `maximum: 5`), `message` (`minLength: 1`, `maxLength:
80`), `maintenance` (boolean, `default: false`); `x-kubernetes-validations` trên `spec` với `rule: "!self.maintenance || self.replicas == 1"`.
Lỗi bị chặn ở API server, trước khi controller thấy, và người dùng nhận thông báo ngay khi `kubectl apply`. `subresources.status: {}` tách
quyền: người dùng ghi spec, operator ghi status; ghi vào `/status` không làm tăng `metadata.generation`, nên `observedGeneration` cho biết
controller đã xử lý tới bản spec nào. `additionalPrinterColumns` cho `kubectl get` hữu ích như một kind dựng sẵn.

**Controller** (`operator/controller.py`, chỉ thư viện chuẩn): mỗi 3 giây list Storefront trong namespace, với từng cái:

1. Server-side apply ConfigMap `<tên>-web` và Deployment `<tên>-web`, cả hai mang `ownerReferences` (`controller: true`, `uid` của
   Storefront) và nhãn `app.kubernetes.io/managed-by: storefront-operator`. Apply là idempotent: chạy lại không đổi gì nếu đã khớp, tạo lại
   nếu bị xoá (level-triggered), đè trường bị sửa tay (`force=true`, trường do `fieldManager` này quản).
2. Đọc `status.readyReplicas` của Deployment vừa apply, merge patch `status` của Storefront nếu khác (tránh ghi thừa, mỗi lần ghi là một sự
   kiện cho mọi watcher).
3. Lỗi một Storefront không chặn các Storefront khác; in log JSON.

Xoá Storefront thì không cần code: garbage collector xoá object con có ownerReference trỏ tới nó. Operator thật dùng thêm finalizer khi phải
dọn thứ **ngoài** cluster (bản ghi DNS, bucket) trước khi object biến mất.

**RBAC.** Role trong namespace: get, list, watch `storefronts`; get, patch, update `storefronts/status`; get, list, watch, create, patch,
update `deployments`, `configmaps`. Không delete (GC xoá hộ), không Secret, không pod. Quyền chỉ trong namespace; operator cho nhiều
namespace dùng ClusterRole cộng RoleBinding ở đúng các namespace đó, hay một ClusterRoleBinding khi thật sự phục vụ cả cluster (và khi đó là
thành phần của platform, review như code hạ tầng).

**Triển khai.** `configMapGenerator` đóng `controller.py` vào ConfigMap có hậu tố hash: sửa code là đổi tên ConfigMap, Deployment rollout.
`strategy: Recreate` và một replica: không có leader election, hai bản chạy cùng lúc sẽ cùng apply (vô hại vì idempotent, nhưng ghi status
chồng nhau, và với logic không idempotent thì nguy hiểm). Operator thật dùng Lease cho leader election.

## Quyết định cần cân nhắc

- **Poll hay watch.** Bài poll 3 giây cho đơn giản. Production dùng informer (list một lần rồi watch, có cache cục bộ, resync định kỳ) và
  work queue có backoff: nhẹ cho API server, phản ứng ngay. controller-runtime (Go), kopf (Python) làm sẵn phần này.
- **Server-side apply hay get-then-update.** SSA tránh xung đột phiên bản và ghi rõ ai sở hữu trường nào (`managedFields`); get-then-update
  cần xử lý `409 Conflict`.
- **Schema hay webhook.** Schema cộng CEL đủ cho phần lớn ràng buộc, chạy trong API server, không thêm điểm hỏng. Validating webhook khi cần
  dữ liệu ngoài object (tra cứu hệ thống khác); webhook chết thì mọi lần tạo bị chặn (`failurePolicy: Fail`) hay lọt (`Ignore`).
- **Version.** Đổi schema không tương thích thì thêm `v2`, giữ `v1` served, conversion webhook, rồi mới bỏ `v1`.
- **Viết hay dùng sẵn.** Trang khuyến mãi thật thì một Helm chart hay ArgoCD ApplicationSet có lẽ đủ; operator đáng khi có vòng đời vận hành
  (backup, failover, nâng cấp có thứ tự).

## Rubric (10 điểm)

| Điểm | Tiêu chí |
| --- | --- |
| 2 | Schema chặn đủ input sai bằng kiểu, giới hạn, required, default và CEL; thông báo lỗi hiểu được |
| 1 | Subresource status, printer columns, `observedGeneration` dùng đúng nghĩa |
| 2 | Reconcile level-triggered và idempotent: chạy lại không đổi gì, tự sửa lệch, không phụ thuộc thứ tự sự kiện |
| 1 | ownerReferences đúng, xoá cha dọn con; biết khi nào cần finalizer |
| 1 | Status phản ánh trạng thái thật, không ghi thừa |
| 1 | RBAC tối thiểu, trong namespace, không delete, không Secret |
| 1 | Xử lý lỗi: một object lỗi không chặn object khác, log có cấu trúc, backoff hay chu kỳ hợp lý |
| 1 | Nêu được cách lên production: informer, leader election, metric, test, version CRD |
