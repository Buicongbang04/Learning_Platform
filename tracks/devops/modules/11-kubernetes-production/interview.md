# Câu hỏi phỏng vấn: Kubernetes production

## Một request `kubectl apply` bị từ chối. Làm sao biết nó bị chặn ở authentication, authorization hay admission?

Đọc nguyên văn lỗi, mỗi cửa có dạng riêng. `401 Unauthorized` hay `You must be logged in` là authentication: token hết hạn, chứng chỉ
sai CA, OIDC cấu hình lệch. `forbidden: User "x" cannot patch resource "deployments" in API group "apps" in the namespace "shop"` là RBAC:
câu lỗi đã nói đủ user, verb, resource, nhóm API, namespace; kiểm bằng `kubectl auth can-i patch deployments.apps -n shop --as=x`
(admin) hay `kubectl auth can-i --list` (chính mình), `kubectl auth whoami` để xem API server thấy mình thuộc nhóm nào. Lỗi có tên
policy, `violates PodSecurity`, `exceeded quota`, `maximum memory usage`, hay `admission webhook "..." denied` là admission. Riêng pod do
controller tạo thì `kubectl apply` thành công; lỗi admission chỉ hiện trong event `FailedCreate` của ReplicaSet, Job hay StatefulSet.

## Thiết kế quyền cho pipeline CI deploy vào namespace `shop`. Bạn cấp gì và không cấp gì?

Một ServiceAccount riêng (`ci-deployer`), không dùng `default`, `automountServiceAccountToken: false` vì không pod nào chạy bằng nó. Role
trong `shop` gồm đúng những gì `kubectl apply` và `rollout status` cần: get, list, watch, create, patch, update trên `deployments`,
`services`, `configmaps`; get, list, watch `replicasets`, `pods`, `events`; get `pods/log` để in log khi rollout lỗi. Không cấp: Secret
(nội dung bí mật đến từ External Secrets hay Vault, không đi qua CI), delete và deletecollection, `pods/exec`, tạo pod trực tiếp, Role,
RoleBinding (CI sửa được RBAC là tự nâng quyền được), không `*`. RoleBinding trong `shop`, không ClusterRoleBinding. Token: CI ngoài
cluster đổi OIDC token của nền tảng CI lấy token ngắn hạn, không lưu kubeconfig dài hạn. Kiểm bằng ma trận `kubectl auth can-i ... --as=
system:serviceaccount:shop:ci-deployer` chạy trong CI của chính repo hạ tầng, để ai nới quyền thì test đỏ (Basic 02 làm đúng việc này).

## Pod Security Admission khác PodSecurityPolicy thế nào? Bạn đưa một namespace lên `restricted` ra sao để không gây sự cố?

PSP là object gắn với user và ServiceAccount qua RBAC, rất khó đoán policy nào áp cho pod nào, và đã bị gỡ ở 1.25. PSA là plugin
dựng sẵn, cấu hình bằng nhãn namespace với ba mức cố định (privileged, baseline, restricted) và ba chế độ (enforce, audit, warn). Không
tuỳ biến từng trường; cần luật riêng thì thêm ValidatingAdmissionPolicy hay Kyverno. Lộ trình: đặt `warn=restricted` và
`audit=restricted` trước, `kubectl label --dry-run=server` để xem pod hiện có nào vi phạm, sửa `securityContext` (runAsNonRoot, drop ALL,
allowPrivilegeEscalation false, seccomp RuntimeDefault), sửa image chạy root, rồi mới `enforce`. Nhớ rằng PSA chặn pod chứ không chặn
Deployment: sau khi enforce phải kiểm Deployment có đủ replica, không chỉ kiểm `kubectl apply` không lỗi.

## Bạn vừa áp default-deny NetworkPolicy cho namespace production. Những gì có thể hỏng ngay hoặc hỏng sau?

Ngay: DNS (egress tới kube-dns ở `kube-system`, UDP và TCP 53) nên mọi lời gọi theo tên; lời gọi ra ngoài (API thanh toán, S3, SMTP);
probe nếu CNI không miễn trừ traffic từ node; Prometheus scrape từ namespace monitoring; Ingress controller ở namespace khác gọi vào pod;
webhook và controller cần gọi API server. Hỏng sau: kết nối đã mở trước khi áp policy (connection pool) có thể sống tiếp, ứng dụng chỉ
chết ở lần restart hay deploy kế tiếp, có khi là nửa đêm. Cách làm: liệt kê luồng thật (từ log, Hubble, flow log), viết allow trước, áp
deny sau, restart thử, kiểm cả hai chiều: luồng được phép phải thông và luồng bị cấm phải bị chặn. NetworkPolicy là L3/L4; lọc theo tên
miền ngoài hay HTTP path cần Cilium policy hay mesh.

## Drain một node để bảo trì thì treo. Bạn chẩn đoán thế nào?

Đọc output của drain: `Cannot evict pod as it would violate the pod's disruption budget` là PDB. `kubectl get pdb -A` xem
`ALLOWED DISRUPTIONS` bằng 0: hoặc PDB đặt `minAvailable` bằng đúng số replica (không bao giờ drain được), hoặc ứng dụng đang thiếu pod
Ready nên ngân sách đã hết, mà pod thay thế lại `Pending`. Pod thay thế `Pending` thì đọc `FailedScheduling`: node còn lại có taint mà pod
không tolerate, topology spread `DoNotSchedule` vẫn đếm node đang cordon (mặc định `nodeTaintsPolicy: Ignore`), hết tài nguyên theo
requests, PVC local giữ pod ở đúng node đó. Ngoài PDB: pod kẹt `Terminating` vì preStop dài hay finalizer, pod không có controller
(drain cần `--force`). Không dùng `--disable-eviction` để "cho xong": đó là tắt đúng cơ chế bảo vệ capacity.

## Taint, nodeSelector và nodeAffinity khác nhau thế nào? Thiết kế một pool node dành riêng cho GPU.

nodeSelector và nodeAffinity là pod **chọn** node (affinity có toán tử và mức mềm, cứng); taint là node **từ chối** pod không có
toleration. Một pool dành riêng cần cả hai: taint `nvidia.com/gpu=true:NoSchedule` để pod thường không lấn vào node đắt tiền, cộng nhãn
node `pool=gpu` và nodeAffinity bắt buộc trên workload GPU để chúng không chạy ra node thường. Thêm request `nvidia.com/gpu: 1` (device
plugin) để scheduler đếm GPU, PriorityClass cho job huấn luyện quan trọng, và Cluster Autoscaler hay Karpenter với node group GPU co về 0
khi không có job. Toleration rỗng với `operator: Exists` chỉ dành cho DaemonSet hệ thống; đặt nó cho workload là bỏ qua cả cordon.

## HPA của bạn không scale dù CPU cao. Kiểm những gì?

`kubectl describe hpa`: điều kiện `ScalingActive=False` kèm lý do. `FailedGetResourceMetric: missing request for cpu` là container thiếu
`requests.cpu` (Utilization là phần trăm của request). `unable to fetch metrics` là metrics-server chưa chạy hay APIService
`v1beta1.metrics.k8s.io` không Available (kubectl top cũng lỗi). `scaleTargetRef` trỏ sai tên. Đã chạm `maxReplicas`. Pod chưa Ready bị
HPA tính thận trọng. Behavior scaleUp quá chậm. Ngược lại, scale rồi lại tụt ngay: manifest còn `spec.replicas` nên mỗi lần deploy kéo
về, hay VPA cùng điều khiển request theo CPU. Và câu hỏi lớn hơn: CPU có phải tín hiệu đúng không; worker hàng đợi nên scale theo độ dài
hàng đợi (KEDA).

## Vì sao chọn Helm cho phần mềm bên thứ ba nhưng Kustomize cho ứng dụng của mình?

Helm là trình đóng gói: chart có version, values là giao diện cho người cài, có dependency, hook trước và sau cài, `helm rollback`, phân
phối qua registry OCI. Đó đúng là thứ cần khi người viết và người cài là hai bên: cài cert-manager, ingress controller, Prometheus. Cái giá
là template Go trên YAML khó đọc, khó review diff, và values dễ thành một ngôn ngữ cấu hình thứ hai. Kustomize là YAML thuần cộng patch
khai báo, có sẵn trong kubectl, diff giữa các overlay đọc ngay được; đủ cho vài môi trường của chính team, nơi người viết và người cài là
một. Không phải tuyệt đối: chart nội bộ đáng giá khi nhiều team cài cùng một mẫu service. ArgoCD, Flux chạy được cả hai.

## Viết một Helm chart tốt: những điểm bạn kiểm trong review?

Selector chỉ gồm `name` và `instance` (selector bất biến, gắn version vào là upgrade lần sau lỗi); nhãn chuẩn `app.kubernetes.io/*` và
`helm.sh/chart` qua helper; tên qua `fullname` để hai release cùng namespace không đụng nhau; không hard-code replicas, image, tài nguyên;
không nhận mật khẩu trong values mà nhận tên Secret có sẵn (values được lưu trong Secret của release, ai đọc được Secret của namespace là
đọc được); annotation checksum của ConfigMap để đổi cấu hình là rollout; `securityContext` mặc định đạt restricted; probe; hook test chạy
được trong namespace restricted; `helm lint --strict`, `helm template` qua kubeconform hay `--dry-run=server` trong CI; `values.schema.json`
cho trường quan trọng; không `lookup` hay giá trị ngẫu nhiên làm `helm template` khác bản cài thật.

## Khi nào nên viết operator, và một controller tốt cần những tính chất gì?

Khi có một quy trình vận hành lặp lại, có trạng thái, mà con người đang làm bằng runbook: tạo cụm database có replica và backup, xoay
chứng chỉ, provisioning tenant. Không viết operator cho thứ một Helm chart hay Kustomize làm được, và ưu tiên operator cộng đồng đã chín
(CloudNativePG, Strimzi, cert-manager). Controller tốt: level-triggered (đọc trạng thái thật mỗi lần reconcile, không dựa vào việc nhận đủ
sự kiện), idempotent (server-side apply), `ownerReferences` để GC dọn object con, ghi `status` qua subresource kèm `observedGeneration`,
CRD có schema và CEL chặn input sai ở API server, RBAC tối thiểu (namespace nào cần thì quyền ở đó), một bản chạy hay có leader election,
backoff khi lỗi, metric và event cho người vận hành, và kế hoạch version CRD (conversion) trước khi đổi schema.

## Lập kế hoạch nâng cluster kubeadm từ 1.34 lên 1.37 không downtime.

Ba bước minor vì kubeadm không nhảy bản; Kubernetes không hạ minor nên lùi là restore etcd, cần snapshot trước mỗi bước. Chuẩn bị: quét
API bị gỡ bằng pluto, kubent và metric `apiserver_requested_deprecated_apis`; đọc release notes và ma trận hỗ trợ addon (CNI, ingress,
CSI); diễn tập trên staging; mọi ứng dụng phục vụ khách có nhiều replica, PDB `maxUnavailable: 1`, readiness đúng, spread theo zone. Control
plane từng node một: `kubeadm upgrade plan`, `apply` ở node đầu, `upgrade node` ở node sau, rồi kubelet. Worker: nhờ skew n-3 giữ 1.34 trong
lúc control plane đi 1.35, 1.36, 1.37, rồi thay node (thêm node 1.37, drain node cũ, xoá) để mỗi worker chỉ bị drain một lần. Tiêu chí
dừng theo SLO, smoke test sau mỗi bước, thông báo trước. Advanced 01 chấm kế hoạch theo đúng khung này.

## Sự cố: sáng thứ hai mọi `kubectl` của cả team báo lỗi chứng chỉ, nhưng ứng dụng vẫn phục vụ khách. Bạn xử lý thế nào?

Ứng dụng còn chạy vì data plane không cần control plane (pod, kube-proxy, rule mạng giữ nguyên); thứ mất là mọi thay đổi: deploy, scale,
HPA, thay pod chết. Đọc nguyên lỗi: `x509: certificate has expired or is not yet valid` là chứng chỉ; kiểm giờ của máy mình trước. Trên
node control plane (SSH, vì `kubectl` không vào được): `kubeadm certs check-expiration`; chứng chỉ kubeadm sống một năm và chỉ được gia
hạn tự động khi `kubeadm upgrade`, nên cluster không nâng cấp cả năm hết hạn đúng ngày tạo. `crictl ps -a` xem static pod
kube-apiserver, controller-manager, scheduler; `crictl logs` của chúng và `journalctl -u kubelet` (chứng chỉ client của kubelet tự xoay
nếu bật rotation, nếu không node cũng NotReady). Sửa: `kubeadm certs renew all` trên từng control plane, restart static pod (dời manifest
ra rồi vào lại), cập nhật `admin.conf` cho người cần. Postmortem: alert theo ngày hết hạn chứng chỉ (metric
`apiserver_client_certificate_expiration_seconds`, hay blackbox kiểm TLS của API server), lịch nâng cấp đều đặn, runbook gia hạn đã diễn
tập.

## Chọn giữa EKS, GKE Autopilot, ECS trên Fargate và Docker Swarm cho một startup 6 kỹ sư, 12 service HTTP.

Câu hỏi quyết định không phải công nghệ mà là ai vận hành. Đã ở AWS, không có người chuyên platform, 12 service HTTP không cần CRD hay
operator: ECS trên Fargate ít việc nhất (không node, không nâng Kubernetes), đổi lại khoá vào AWS và không dùng được hệ sinh thái Helm,
operator. Muốn chuẩn Kubernetes để sau này mang đi được, dùng thêm Argo, operator: GKE Autopilot (không quản node, tính tiền theo requests)
hay EKS với Karpenter, chấp nhận lịch nâng cấp ba lần mỗi năm và việc quản addon. Swarm chỉ hợp vài host và ứng dụng đơn giản; thiếu
NetworkPolicy, autoscaling, hệ sinh thái, và tuyển người khó hơn. Kubeadm tự quản chỉ khi có lý do on-prem. Ghi quyết định vào ADR kèm
điều kiện xem lại (số service, yêu cầu đa cloud).
