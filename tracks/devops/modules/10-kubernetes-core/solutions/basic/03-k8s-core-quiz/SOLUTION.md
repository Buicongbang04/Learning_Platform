# Lời giải: trắc nghiệm Kubernetes core

| Câu | Đáp án | Giải thích ngắn |
| --- | --- | --- |
| who-schedules | c | Scheduler watch pod chưa có `nodeName`, lọc rồi chấm điểm node, ghi binding qua API server; kubelet của node đó thấy pod của mình qua watch và gọi CRI. ReplicaSet controller chỉ tạo object Pod |
| api-down | a | Data plane không cần control plane để tiếp tục chạy: kubelet giữ pod spec đã nhận, kube-proxy giữ rule đã lập. Mất API server là mất khả năng **thay đổi**: không scale, không rollout, không lên lịch, node chết thì không ai dời pod |
| cri-cni-csi | b | CRI là giao diện kubelet gọi runtime (containerd, CRI-O); CNI plugin cấp IP và đường mạng cho pod; CSI driver attach, mount volume. kube-proxy lo Service, CoreDNS lo tên |
| liveness-readyz | c | Liveness gọi dependency biến sự cố của dependency thành restart hàng loạt. Readiness `/readyz`, liveness `/healthz` (chỉ tiến trình) |
| startup-probe | a | startupProbe hoãn liveness và readiness tới khi nó đạt; tổng thời gian cho phép là `failureThreshold × periodSeconds`. Bỏ liveness thì mất khả năng tự chữa khi tiến trình treo |
| qos-oom | d | Khi node thiếu RAM, kubelet evict BestEffort trước, rồi Burstable đang dùng vượt request, Guaranteed sau cùng; OOM killer của kernel cũng ưu tiên theo `oom_score_adj` cùng thứ tự |
| rollout-capacity | b | 25% của 4 là 1 (maxUnavailable làm tròn xuống, maxSurge làm tròn lên). Bản lỗi giữ lại 3 pod cũ. Muốn đủ capacity: `maxUnavailable: 0` |
| rollback-rs | c | Undo chép template cũ vào Deployment; ReplicaSet có cùng `pod-template-hash` được dùng lại; revision nhận số mới; `revisionHistoryLimit` quyết định còn bao nhiêu bản để lùi |
| workload-choice | a, b, d | Báo cáo theo lịch là CronJob; Deployment có vòng lặp sleep giữ pod chạy cả ngày, không có lịch sử chạy hay retry |
| selector-mismatch | b | EndpointSlice rỗng hoàn toàn là dấu hiệu selector không chọn được pod nào. CoreDNS lỗi thì báo không phân giải được tên, không phải refused |
| headless-dns | d | Pod của StatefulSet có bản ghi `<pod>.<service>.<ns>.svc.<cluster-domain>` nhờ Service headless trong `serviceName` |
| pvc-pending | a | `storageClassName` của PVC bất biến sau khi tạo; volumeClaimTemplates của StatefulSet cũng không sửa được, phải xoá StatefulSet (`--cascade=orphan` nếu cần giữ pod) rồi tạo lại. hostPath bị chặn ở cluster của khoá, và cũng là cách sai ở production |
| etcd-backup | a, b, c | Backup etcd khôi phục **object** Kubernetes (gồm cả object PV và PVC), không khôi phục dữ liệu bên trong volume; Postgres cần backup riêng |
| distro-choice | c | k3s (hay MicroK8s, k0s) cho edge: một binary, nhẹ, datastore nhúng. kind chỉ để dev và CI; kubeadm ba control plane mỗi cửa hàng là quá nặng |
