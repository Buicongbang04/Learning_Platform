# Lời giải: kế hoạch nâng cấp 1.34 lên 1.37 không downtime

`UPGRADE-PLAN.md` và `manifests/` cạnh tệp này là **một** lời giải qua test; rubric dưới đây mới là thứ chấm nội dung.

## Hướng làm

**Manifest.** Mỗi object đi một đường riêng:

| Object | Từ | Sang | Phải sửa thêm |
| --- | --- | --- | --- |
| Ingress | `extensions/v1beta1` | `networking.k8s.io/v1` | `pathType` bắt buộc; `backend.serviceName`/`servicePort` thành `backend.service.name`/`port.number`; annotation `kubernetes.io/ingress.class` thành `spec.ingressClassName` |
| CronJob | `batch/v1beta1` | `batch/v1` | Không bắt buộc; nhân tiện dùng `timeZone: Asia/Ho_Chi_Minh` thay lịch UTC tự đổi (`0 19 * * *` UTC là 02:00 giờ Việt Nam) |
| PodDisruptionBudget | `policy/v1beta1` | `policy/v1` | Ở `policy/v1` selector rỗng chọn mọi pod của namespace (v1beta1 chọn không pod nào); kiểm selector không rỗng |
| HPA | `autoscaling/v2beta2` | `autoscaling/v2` | Cấu trúc `metrics[].resource.target` giữ nguyên |
| PodSecurityPolicy | `policy/v1beta1` | Không còn | Xoá tệp; thay bằng nhãn Pod Security Admission `restricted` trên namespace (cộng ValidatingAdmissionPolicy hay Kyverno nếu cần luật riêng), làm **trước** khi nâng lên 1.25+ |

Tìm trong repo thật: `pluto detect-files -d manifests/`, `pluto detect-helm` cho release đang chạy (Helm lưu manifest cũ trong lịch sử release,
`helm-mapkubeapis` sửa), metric `apiserver_requested_deprecated_apis` cho client còn gọi API cũ. `kubectl convert` (plugin cài riêng) làm phần
máy móc cho kind nó biết.

**Kế hoạch.** Bảy phần của bản mẫu: bối cảnh có con số (SLO, cửa sổ, phạm vi); trình tự 1.35, 1.36, 1.37 vì kubeadm không nhảy minor, worker
giữ 1.34 nhờ skew n-3 rồi thay một lần; chuẩn bị (quét API, release notes, ma trận addon, diễn tập staging, snapshot etcd, PDB và readiness
của ứng dụng, đóng băng deploy); control plane từng node với `kubeadm upgrade plan`, `apply`, `upgrade node`, kiểm etcd member và `/readyz`
sau mỗi node; worker theo kiểu surge rồi drain, PDB `maxUnavailable: 1`; tiêu chí dừng bằng số, đường lùi theo từng lớp (worker: uncordon và
dừng; control plane: sửa tiến, restore etcd chỉ khi API server không lên; cuối cùng: cluster mới); smoke test, dashboard SLO, kênh thông báo.

## Quyết định cần cân nhắc

- **Nâng tại chỗ hay dựng cluster mới (blue/green cluster).** Cluster mới 1.37, chuyển traffic dần qua DNS hay Gateway: lùi dễ nhất, không
  đụng etcd cũ, nhưng cần IaC cho mọi thứ (kể cả RBAC, secret, CRD), dữ liệu trong cluster (PV) phải di chuyển, tốn gấp đôi hạ tầng trong
  thời gian chuyển. Hợp khi nhảy nhiều minor hay đổi CNI cùng lúc.
- **Thay node hay nâng kubelet tại chỗ.** Thay node (image có sẵn bản mới) bất biến, ít trạng thái lạ, cần quota và thời gian join; nâng tại
  chỗ rẻ hơn ở on-prem.
- **Một đêm hay nhiều đêm.** Ba minor control plane trong một đêm giảm thời gian ở trạng thái trộn bản, nhưng mất điểm dừng tự nhiên để quan
  sát.
- **Cluster managed**: EKS, GKE, AKS nâng control plane bằng một lệnh (vẫn từng minor), node group nâng bằng surge; phần chuẩn bị, PDB, API
  deprecation, addon vẫn là của bạn.

## Rubric (10 điểm)

| Điểm | Tiêu chí |
| --- | --- |
| 1 | Bối cảnh có số liệu cụ thể: bản hiện tại và đích, cấu trúc cluster, SLO, cửa sổ, phạm vi và ngoài phạm vi |
| 1 | Trình tự từng minor đúng; giải thích skew của kubelet, kube-apiserver HA, controller-manager, kubectl tại mỗi bước |
| 1 | Chuẩn bị: quét API bị gỡ có tên công cụ và chỗ quét (Git, Helm release, metric của API server); manifest đã sửa |
| 1 | Chuẩn bị: snapshot etcd trước mỗi bước, lưu ngoài cluster, đã thử restore; ma trận hỗ trợ addon |
| 1 | Ứng dụng sẵn sàng chịu drain: nhiều replica, PDB không chặn cứng, readiness, spread, xử lý SIGTERM |
| 1 | Control plane từng node, đúng lệnh kubeadm, kiểm etcd và API server giữa các node |
| 1 | Worker không mất capacity: surge hay capacity dư, drain qua eviction, từng node, xen kẽ zone |
| 1 | Tiêu chí dừng bằng số cho từng bước |
| 1 | Đường lùi đúng sự thật: không hạ minor, lùi worker khác lùi control plane, restore etcd là phương án cuối, có phương án cluster mới |
| 1 | Kiểm chứng theo SLO và smoke test sau mỗi bước, kênh thông báo, cập nhật runbook sau cùng |

Trừ điểm: nâng thẳng nhiều minor bằng kubeadm, "rollback bằng cách cài lại kubeadm cũ", drain nhiều node cùng lúc, `--disable-eviction`,
không nhắc PodSecurityPolicy đã bị gỡ.

## Lab tay (không chấm tự động)

Dựng cluster kubeadm 1.34 trên VM theo mục 6 của module 10, nâng lên 1.35 theo đúng phần 4 và 5 của kế hoạch, ghi lại output của `kubeadm
upgrade plan`, thời gian mỗi bước, và một lần drain bị PDB chặn rồi gỡ. Cluster kind thì không nâng tại chỗ: tạo cluster mới với node image
mới.
