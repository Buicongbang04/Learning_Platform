---
title: Kế hoạch nâng cluster production 1.34 lên 1.37 không downtime, chuyển manifest khỏi API đã bị gỡ
level: advanced
services: []
files:
  - path: starter/UPGRADE-PLAN.md
    note: Khung kế hoạch
  - path: starter/manifests/ingress.yaml
    note: Manifest từ chart cũ (cả thư mục manifests)
  - path: tests/test_upgrade_plan.py
    note: Kiểm cấu trúc, từ khoá, bảng API đã gỡ; không sửa
  - path: tests/fixtures/UPGRADE-PLAN.good.md
    note: Ví dụ đạt (hệ thống khác, chặng khác)
run:
  - uv run pytest tracks/devops/modules/11-kubernetes-production/exercises/advanced/01-zero-downtime-upgrade-plan -q -rs
---

## Mục tiêu

Lập kế hoạch nâng cấp một cluster production qua nhiều minor mà khách không thấy lỗi: trình tự đúng chính sách version skew, chuẩn bị
đủ, control plane và worker theo đúng cách, tiêu chí dừng và đường lùi thật (không có "hạ bản"), kiểm chứng theo SLO. Kèm theo, dọn
manifest còn dùng API đã bị gỡ, vì đó là thứ làm hỏng deploy ngay sau khi nâng.

## Đề bài

Olist Shop chạy cluster kubeadm 1.34 tự quản: ba control plane (etcd stacked), sáu worker trong hai zone. 1.34 hết hỗ trợ bản vá; đích là
1.37. Trên cluster có API (HPA 6 tới 20 pod), worker hàng đợi, Redis, CronJob báo cáo; Postgres là dịch vụ managed. SLO của API 99,9% mỗi
tháng. Cửa sổ bảo trì: hai đêm, mỗi đêm 4 giờ, lưu lượng thấp nhất tuần.

**Phần 1, manifest.** `starter/manifests/` là manifest lấy từ một chart cũ thời 1.21. Chuyển chúng sang API hiện hành mà giữ đúng các object
(`Deployment api`, `Service api`, `Ingress shop`, `CronJob revenue-report`, `PodDisruptionBudget api`, `HorizontalPodAutoscaler api`),
bỏ PodSecurityPolicy (đã bị gỡ hẳn; thay bằng gì thì nói trong kế hoạch). Ingress dùng `ingressClassName: devops-traefik` và host
`shop.lab.olist.test` (test thay `lab.olist.test` bằng tên miền của lab khi thử trên cluster).

**Phần 2, kế hoạch.** Điền `starter/UPGRADE-PLAN.md`, giữ đúng bảy tiêu đề `## 1.` tới `## 7.`. Nâng cấp kubeadm thật trên VM là lab tay
(không chấm tự động); test kiểm cấu trúc, rubric trong `SOLUTION.md` chấm nội dung.

**Cách test chấm.**

| Phần | Test kiểm |
| --- | --- |
| API đã gỡ | Không tài liệu nào trong `manifests/*.yaml` dùng cặp `apiVersion`, `kind` trong bảng của test: `extensions/v1beta1` (Ingress, Deployment, DaemonSet, NetworkPolicy), `apps/v1beta1`, `apps/v1beta2` (Deployment), `networking.k8s.io/v1beta1` (Ingress, IngressClass), `rbac.authorization.k8s.io/v1beta1` (Role, ClusterRole, RoleBinding, ClusterRoleBinding), `apiextensions.k8s.io/v1beta1` CRD, `scheduling.k8s.io/v1beta1` PriorityClass, `coordination.k8s.io/v1beta1` Lease, `batch/v1beta1` CronJob, `policy/v1beta1` (PodDisruptionBudget, PodSecurityPolicy), `discovery.k8s.io/v1beta1` EndpointSlice, `autoscaling/v2beta1`, `autoscaling/v2beta2` HPA, `node.k8s.io/v1beta1` RuntimeClass, `storage.k8s.io/v1beta1` CSIStorageCapacity; không còn kind PodSecurityPolicy. Test cũng chạy bảng này trên manifest gốc để chứng minh nó bắt được |
| Ingress | `spec.ingressClassName: devops-traefik`, không annotation `kubernetes.io/ingress.class`, mọi path có `pathType`, backend dạng `service` |
| Object giữ nguyên | Đúng sáu object kể trên |
| Hợp lệ trên cluster | Mỗi object (sau khi thay tên miền) qua `kube_manifest_problems` và `kubectl apply --dry-run=server` trên `devops-lab` 1.34 (cần cluster, thiếu thì riêng test này skip) |
| Kế hoạch | Đủ `## 1.` tới `## 7.`, không còn `TODO`; phần 1 ít nhất 300 ký tự văn xuôi; phần 2 nêu `1.35`, `1.36`, `1.37` theo thứ tự xuất hiện và nhắc `skew`; phần 5 có khối mermaid |
| Gạch đầu dòng | Phần 3 ít nhất 5, phần 4 ít nhất 4, phần 5 ít nhất 4, phần 6 ít nhất 3, phần 7 ít nhất 4 |
| Từ khoá (không phân biệt hoa thường, một từ trong mỗi nhóm) | Phần 3: deprecated/removed/gỡ; pluto/kubent/kubectl convert/deprecated api; etcd; snapshot/backup; pdb/poddisruptionbudget; release notes/changelog; staging. Phần 4: kubeadm upgrade plan; kubeadm upgrade apply; kubeadm upgrade node. Phần 5: drain; uncordon; pdb/poddisruptionbudget; surge/node mới/thay node/node pool. Phần 6: etcd; restore; downgrade/không hạ/không lùi. Phần 7: smoke; slo/error budget/tỉ lệ lỗi; thông báo/status page/kênh |
| Bộ kiểm | Chạy trên ba fixture (khung, bản yếu, bản đạt của hệ thống khác đi 1.33 lên 1.36) để chứng minh bắt được lỗi |

Không cần cluster cho phần kế hoạch.

## Tiêu chí đạt

- Test pass.
- Rubric trong `SOLUTION.md` đạt từ 7/10.
- Bảo vệ được kế hoạch trước hai câu hỏi: "Sao không nâng thẳng 1.34 lên 1.37 cho nhanh?" và "Bước 2 hỏng giữa đêm, bạn lùi bằng cách nào khi
  Kubernetes không hạ bản được?".

## Gợi ý

### Gợi ý 1

Đọc chính sách version skew (mục 7 của module): thành phần nào phải nâng trước, thành phần nào được cũ hơn bao nhiêu minor. Từ đó tính
số lần mỗi worker phải drain. `kubectl explain ingress.spec.rules.http.paths --api-version=networking.k8s.io/v1` cho dạng mới của
backend.

### Gợi ý 2

Đọc `tests/fixtures/UPGRADE-PLAN.good.md` để thấy độ chi tiết mong đợi (hệ thống khác, đừng chép). Một kế hoạch tốt có tiêu chí dừng
bằng con số cho mỗi bước, không chỉ "nếu có lỗi thì dừng".
