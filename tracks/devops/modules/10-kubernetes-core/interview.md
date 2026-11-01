# Câu hỏi phỏng vấn: Kubernetes core

## Điều gì xảy ra từ lúc bạn gõ `kubectl apply -f deployment.yaml` tới lúc pod nhận traffic?

kubectl gửi request tới kube-apiserver; API server xác thực, kiểm RBAC, chạy admission (mutating rồi validating: Pod Security, policy,
webhook), validate schema, ghi object vào etcd. Deployment controller (trong controller-manager) thấy qua watch, tạo ReplicaSet theo
hash của pod template; ReplicaSet controller tạo các Pod chưa có `nodeName`. Scheduler lọc node (tài nguyên, taint, affinity, ràng
buộc volume), chấm điểm, ghi binding. kubelet của node đó thấy pod của mình, gọi containerd qua CRI: tạo sandbox (CNI cấp IP), kéo
image, mount volume (CSI), khởi động init container, sidecar, container chính, chạy probe. Khi readiness đạt, kubelet cập nhật status;
EndpointSlice controller thêm IP pod vào slice của Service; kube-proxy trên mọi node cập nhật rule; CoreDNS đã có tên Service từ trước.
Mọi bước nói chuyện qua API server, không thành phần nào gọi thẳng thành phần khác.

## Control plane của một cluster ba control plane mất hai node. Cái gì còn chạy, cái gì không?

etcd ba member mất hai thì không còn đa số: không ghi được, API server trả lỗi cho mọi thay đổi (đọc có thể còn tuỳ cấu hình). Data
plane vẫn chạy: pod đang chạy tiếp tục, kubelet vẫn restart container lỗi theo spec đã có, kube-proxy giữ rule cũ, traffic vẫn đi.
Mất là mọi thứ cần thay đổi: deploy, scale, lên lịch pod mới, thay pod của node chết, xoay chứng chỉ, HPA. Khôi phục: đưa member về
(hay dựng lại từ snapshot với `--force-new-cluster` hoặc restore). Bài học thiết kế: 3 member chịu được 1 hỏng, 5 chịu được 2; đặt
member ở các zone khác nhau; số chẵn không thêm khả năng chịu lỗi.

## Liveness, readiness, startup probe khác nhau thế nào? Kể một sự cố do đặt sai probe.

Readiness quyết định pod có nằm trong EndpointSlice (nhận traffic) không, fail thì chỉ bị bỏ ra, không restart. Liveness quyết định
container có bị restart không. Startup hoãn hai cái kia tới khi app khởi động xong.

Sự cố điển hình: liveness của API gọi `/readyz` (kiểm Postgres). Postgres chậm 90 giây vì vacuum, liveness của **mọi** pod API fail
cùng lúc, kubelet restart cả đội, pod mới khởi động lại đập vào Postgres đang chậm: sự cố DB thành sự cố toàn hệ thống. Sửa: liveness
chỉ kiểm tiến trình (`/healthz`), readiness kiểm dependency, startupProbe cho app khởi động chậm, `timeoutSeconds` hợp lý (mặc định 1
giây hay gây fail giả). Ngược lại cũng nguy hiểm: readiness nhạy với một dependency chung thì mọi pod cùng rời Service, client nhận
lỗi kết nối thay vì một trang lỗi có kiểm soát.

## Một Service không phục vụ. Bạn gỡ lỗi theo thứ tự nào?

Đi theo đường gói tin. `kubectl get endpointslices -l kubernetes.io/service-name=<svc>`: rỗng hoàn toàn là selector không khớp nhãn
pod (`kubectl get pods --show-labels`); có endpoint `ready: false` là readiness đang fail (`kubectl describe pod`, log). Có endpoint
ready: gọi thẳng IP pod và `targetPort` từ một pod debug, nếu fail thì app nghe sai địa chỉ (`127.0.0.1`) hay sai cổng; gọi được IP pod
mà không gọi được ClusterIP thì xem kube-proxy và NetworkPolicy; gọi được ClusterIP mà không gọi được tên thì xem DNS (`nslookup` từ
pod, CoreDNS log, `ndots`). Từ ngoài vào thêm lớp Ingress, Gateway, load balancer. Ở Intermediate 03 của module, `Connection refused`
ngay cả với `/healthz` là dấu hiệu Service không có endpoint chứ không phải app lỗi.

## Khi nào dùng StatefulSet thay Deployment? StatefulSet có làm database của bạn "sẵn sàng cao" không?

Khi mỗi replica cần danh tính ổn định: tên `x-0`, DNS riêng qua Service headless, volume riêng đi theo tên qua mọi lần tạo lại, thứ tự
khởi động và cập nhật có kiểm soát (`partition`, `OnDelete`). Ví dụ: database, broker, hệ thống bầu leader.

StatefulSet không làm replication hay failover: ba pod Postgres là ba Postgres độc lập. HA là việc của ứng dụng (streaming
replication, Raft) hay operator (CloudNativePG, Patroni, Strimzi). Còn một giới hạn: node chết thì pod của StatefulSet không được tạo
lại ở node khác cho tới khi chắc chắn pod cũ đã chết (tránh hai writer), volume RWO theo zone phải detach; RTO có thể là phút tới
giờ. Với đội nhỏ, database quan trọng trên cloud, dịch vụ managed thường rẻ hơn tính theo công sức.

## Rollout bản mới làm lỗi production. Bạn làm gì trong năm phút đầu, và cấu hình gì để lần sau không mất capacity?

Năm phút đầu: `kubectl rollout status` và `kubectl get rs` để biết đang ở đâu; nếu bản mới đã nhận traffic và lỗi thì `kubectl rollout
undo deployment/<tên>` (ReplicaSet cũ được scale lên lại, nhanh vì image đã có trên node), rồi mới điều tra bằng log của pod mới. Nếu
bản mới kẹt chưa ready thì không vội: với cấu hình đúng, bản cũ vẫn phục vụ đủ.

Cấu hình: readinessProbe phản ánh thật khả năng phục vụ; `maxUnavailable: 0`, `maxSurge` ≥ 1; `minReadySeconds` để bản chết sau vài
giây không được tính là available; `progressDeadlineSeconds` ngắn để pipeline biết sớm; `revisionHistoryLimit` đủ để lùi; change-cause
để biết lùi về bản nào; PDB để drain node không cắt capacity. Migration schema tương thích ngược (expand rồi contract) để rollback
không vỡ dữ liệu.

## ConfigMap đổi mà app vẫn dùng giá trị cũ. Vì sao, và bạn thiết kế thế nào để đổi cấu hình là một rollout?

Biến môi trường từ ConfigMap chỉ đọc lúc tạo container; mount dạng tệp thì kubelet cập nhật sau khoảng một phút, trừ mount bằng
`subPath` không bao giờ cập nhật; và app phải tự đọc lại tệp. Đổi ConfigMap không đổi pod template nên Deployment không rollout.

Thiết kế: tên ConfigMap có hậu tố hash nội dung (Kustomize `configMapGenerator`, hay Helm annotation checksum trong template), đổi
cấu hình là đổi tên, template đổi, Deployment rollout với đủ strategy và readiness, và `rollout undo` đưa cả cấu hình cũ về.
`immutable: true` cho ConfigMap đã phát hành để không ai sửa tại chỗ.

## Secret trong Kubernetes có an toàn không? Bạn bảo vệ chúng thế nào?

Mặc định chỉ là base64 trong etcd. Ai đọc được Secret qua API, ai có snapshot etcd (đã kiểm ở mục 6: `grep -a` thấy nguyên giá trị),
ai tạo được pod mount Secret trong namespace, đều có giá trị đó. Lớp bảo vệ: RBAC chặt (role `view` không có Secret; cẩn thận quyền
`create pods` vì nó gián tiếp đọc được Secret); encryption at rest bằng KMS v2; mã hoá và giới hạn quyền đọc backup etcd; không đưa
bí mật vào Git mà dùng External Secrets Operator, Vault hay SOPS; token ServiceAccount có hạn (projected) thay vì Secret token vĩnh
viễn; audit log cho thao tác đọc Secret.

## Vì sao bạn chọn kind cho môi trường dev và CI, mà không chọn nó cho production? So với minikube, k3s, managed?

kind chạy mỗi node là một container Docker: dựng cluster nhiều node trong 30 giây, đúng bản Kubernetes upstream, xoá sạch trong vài
giây, chạy được trong CI. Đó chính là thứ cần cho test manifest, operator, chart. Nhưng node là container privileged, không có
LoadBalancer thật, storage là thư mục trong node, hiệu năng mạng không giống thật: không dùng cho workload thật.

minikube hợp học và dev một node với addon tiện. k3s cho edge, VM nhỏ, nhiều cluster nhỏ (một binary, ít RAM). Managed (EKS, GKE,
AKS) cho production trên cloud: không trực control plane, etcd, chứng chỉ. kubeadm khi on-prem và đội đủ người trực. Câu hỏi quyết
định là ai trực control plane lúc 3 giờ sáng, không phải công cụ nào "mạnh" hơn.

## Kể cách bạn backup và restore etcd, và những gì backup đó không bảo vệ.

Backup: `etcdctl snapshot save` với endpoint và chứng chỉ client của etcd (đọc từ manifest static pod), chạy theo lịch, kiểm bằng
`etcdutl snapshot status`, mã hoá, đẩy ra khỏi cluster, giữ nhiều bản, và diễn tập restore định kỳ. Restore: dừng API server, `etcdutl
snapshot restore` ra data dir mới trên mọi member với cùng snapshot và tham số cluster mới, trỏ static pod etcd vào đó, bật lại.

Không bảo vệ: dữ liệu trong volume (Postgres trong PV cần backup ứng dụng); mọi thay đổi sau thời điểm snapshot; trạng thái bên ngoài
cluster mà object trỏ tới (load balancer cloud, DNS). Và restore đưa cả cluster về quá khứ, kể cả những thứ đúng; nhiều đội dùng
GitOps (module 12) để dựng lại object từ Git, chỉ dùng etcd backup cho thứ không có trong Git.

## Thiết kế: đưa Olist Shop (API, worker, Postgres, Redis, báo cáo hằng đêm, agent log) lên Kubernetes cho production. Bạn chọn gì cho từng phần?

API: Deployment nhiều replica, readiness `/readyz`, liveness `/healthz`, startupProbe, requests và limit memory, `maxUnavailable: 0`,
PDB, HPA (module 11), Service ClusterIP sau Gateway API. Worker: Deployment, không Service, liveness trên metrics, scale theo độ dài
hàng đợi. Postgres: dịch vụ managed với PITR nếu có cloud (Service ExternalName cho tên nội bộ), hoặc StatefulSet với operator nếu
on-prem; backup ứng dụng ra ngoài cluster. Redis: Deployment nếu chỉ là hàng đợi mất được, managed nếu không. Báo cáo: CronJob
`timeZone`, `concurrencyPolicy: Forbid`, `startingDeadlineSeconds`. Agent log: DaemonSet có toleration. Migration: Job trước rollout,
schema expand-contract. Cấu hình bằng ConfigMap có hash, bí mật từ External Secrets. Mọi image ghim tag, chạy non-root, namespace có
Pod Security `restricted`. Advanced 01 của module là phiên bản viết ra của câu trả lời này.

## Sự cố: sau khi nâng cấp node, nhiều pod kẹt `Pending` và một StatefulSet không lên lại. Bạn điều tra thế nào?

`kubectl describe pod` xem Events của scheduler: `Insufficient memory` (requests vượt allocatable sau khi mất node), `node(s) had
untolerated taint` (node vẫn cordon hay còn taint của quá trình nâng cấp: `kubectl uncordon`), `node(s) didn't match Pod's node
affinity`, hay `volume node affinity conflict` / `pod has unbound immediate PersistentVolumeClaims`. Với StatefulSet: PV local hay PV
theo zone gắn với node hoặc zone cụ thể; node đó bị thay thì pod chỉ lên được khi có node khớp, hay khi bạn restore dữ liệu sang PV
mới. PVC `Pending` vì StorageClass không tồn tại hay provisioner lỗi xem bằng `kubectl describe pvc` và log của CSI controller. Rút
kinh nghiệm: drain từng node một có PDB, kiểm capacity trước khi nâng cấp, tránh volume gắn node cho dữ liệu không dựng lại được.

## Ingress và Gateway API khác nhau thế nào, và bạn chọn cái nào cho cluster mới?

Ingress là một object L7 đơn giản (host, path, TLS), mọi thứ khác nằm trong annotation riêng của từng controller, và một object trộn
việc của đội hạ tầng với đội app. Gateway API tách vai trò: GatewayClass (implementation), Gateway (listener, TLS, ai được gắn route,
của đội platform), HTTPRoute, GRPCRoute, TCPRoute (của đội app), với trọng số, match header, rewrite, mirror là trường chuẩn, mang
được giữa các implementation, và `ReferenceGrant` cho tham chiếu chéo namespace tường minh. Cluster mới chọn Gateway API; dự án
ingress-nginx của cộng đồng đã ngừng bảo trì từ tháng 3/2026, cluster cũ lên kế hoạch chuyển bằng `ingress2gateway`.
