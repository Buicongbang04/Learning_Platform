# Lời giải: trắc nghiệm Kubernetes production

| Câu | Đáp án | Giải thích ngắn |
| --- | --- | --- |
| role-scope | b | ClusterRole chỉ là bộ quy tắc; RoleBinding áp nó trong đúng namespace của binding. Muốn toàn cluster mới dùng ClusterRoleBinding. Mẫu ClusterRole dùng lại cộng RoleBinding mỗi namespace là cách chuẩn |
| ci-token | b | ServiceAccount riêng, Role tối thiểu trong namespace, token ngắn hạn. Kubeconfig admin hay ClusterRoleBinding `edit` cho `default` là cấp quá rộng; token Secret không hết hạn và `*` trên `apps` đi ngược least privilege |
| psa-levels | b | `restricted` đòi runAsNonRoot, allowPrivilegeEscalation false, drop ALL, seccomp RuntimeDefault; container không có securityContext vi phạm, và vì PSA chặn pod nên Deployment vẫn tạo được còn ReplicaSet báo FailedCreate. Các pod còn lại đạt restricted |
| netpol-dns | b | Deny egress chặn cả DNS; gọi theo tên chết, theo IP còn được. Selector chọn pod đứng sau Service bình thường; NetworkPolicy là stateful nên gói trả lời tự qua |
| netpol-union | c | NetworkPolicy cộng dồn: traffic qua nếu khớp bất kỳ policy nào chọn pod theo chiều đó |
| taint-noexecute | b | Drain gọi Eviction API, PDB được kiểm. Taint NoExecute và delete pod bỏ qua PDB; cordon không đuổi pod nào |
| spread-cordon | a | Mặc định `nodeTaintsPolicy: Ignore` nên node cordon (taint unschedulable) vẫn là một miền có 0 pod; `Honor` loại nó ra. Tăng maxSkew làm mất ý nghĩa ràng buộc; toleration rỗng làm pod bỏ qua cả cordon; xoá PDB không giúp pod Pending có chỗ |
| preemption | b | Scheduler đuổi pod ưu tiên thấp hơn để pod ưu tiên cao vào; PDB của nạn nhân chỉ được tôn trọng theo kiểu cố gắng. `preemptionPolicy: Never` để tắt hành vi này cho một PriorityClass |
| quota-limitrange | c | Quota trên một tài nguyên tính toán buộc mọi pod khai báo tài nguyên đó; pod thiếu bị admission từ chối, ReplicaSet báo FailedCreate. LimitRange với `defaultRequest` điền hộ |
| hpa-requests | a | Utilization là phần trăm của request; không có request thì không tính được dù metrics-server có số. `--kubelet-insecure-tls` là chuyện metrics-server lấy số từ kubelet |
| helm-or-kustomize | b | Vài môi trường của chính team: Kustomize đủ và đọc được. Helm đáng khi phân phối cho người khác, cần values, hook, release. Ba bản sao YAML sẽ lệch nhau; operator là quá tay |
| upgrade-order | c | Control plane trước, từng minor, từng node; kubelet được cũ hơn tới ba minor nên worker giữ bản cũ rồi nâng (hay thay node) sau. Nâng kubelet trước vi phạm skew (kubelet không được mới hơn API server) |
| autoscalers | a, b, d | Cluster Autoscaler dựa vào pod Pending và requests, không dựa vào CPU thật của node (c sai). VPA và HPA cùng theo CPU dễ dao động |
| managed-choice | a, b, d | Swarm không có NetworkPolicy, CRD, HPA dựng sẵn; chuyển từ Kubernetes sang Swarm phải viết lại (c sai) |
