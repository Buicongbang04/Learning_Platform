# Câu hỏi phỏng vấn: cài lên Kubernetes của khách

## Khách gửi một kubeconfig và nói "cluster của anh đây". Mười phút đầu bạn làm gì?

Chưa cài gì. `kubectl auth whoami` (mình là ai: ServiceAccount, user OIDC hay cert), namespace của context,
`kubectl auth can-i --list` trong namespace đó và vài câu hỏi cụ thể cho những gì chart cần (workload, Secret cho release
Helm, NetworkPolicy, `pods/exec`, `pods/portforward`). Rồi đọc luật: nhãn PSA của namespace, `resourcequota`,
`limitrange`, `networkpolicy` có sẵn. Kết quả thành một bảng "có/thiếu/phải hỏi IT" gửi lại trước buổi cài. Không đọc
được `nodes`, `storageclasses` thì hỏi bằng văn bản: node bao nhiêu CPU/RAM, StorageClass nào mặc định, RWO hay RWX.

## `kubectl auth can-i delete networkpolicy default-deny` trả `yes`, nhưng lệnh thật bị từ chối. Giải thích.

`can-i` gửi SelfSubjectAccessReview: chỉ hỏi bước authorization (RBAC). Request thật còn đi qua admission. RBAC không
loại trừ được một object theo tên trong khi cho phép phần còn lại, nên IT chặn bằng ValidatingAdmissionPolicy, webhook
hay Kyverno/Gatekeeper. Muốn biết admission nói gì mà không đổi gì: `kubectl delete … --dry-run=server`. Trong báo cáo
quyền, ghi rõ "RBAC cho phép" khác "cluster chấp nhận".

## `helm install` báo `STATUS: deployed` nhưng `kubectl get pods` trống. Bạn tìm lỗi ở đâu?

Helm chỉ báo API server đã nhận các object (Deployment, StatefulSet…). Pod do controller tạo sau đó và bị admission từ
chối lúc đó, nên lỗi nằm ở event của ReplicaSet/StatefulSet: `kubectl get events --sort-by=.lastTimestamp`,
`kubectl describe rs`. Thủ phạm thường gặp: PodSecurity, ResourceQuota ("must specify"), LimitRange ("No limit is
specified"), webhook policy. Về sau dùng `helm upgrade --install --wait --timeout` để Helm thất bại có lý do thay vì
"deployed" giả.

## Vì sao `kubectl apply --dry-run=server` một Deployment vi phạm PSA lại thành công?

PSA `enforce` áp cho Pod. Với workload resource (Deployment, StatefulSet, Job), PSA chỉ chạy chế độ `warn`/`audit` trên
pod template: bạn nhận dòng `Warning: would violate PodSecurity …`, object vẫn được tạo, và ReplicaSet bị từ chối khi tạo
pod. Kiểm trước thì coi cảnh báo đó là lỗi, hoặc dry-run một Pod dựng từ template.

## Namespace có PSA `restricted`. Đặt `runAsNonRoot: true` xong, pod vẫn không chạy. Vì sao?

PSA chỉ đọc manifest; nó không biết image chạy user nào. Image có `USER root` (hay không khai `USER`) cộng
`runAsNonRoot: true` mà không có `runAsUser` ⇒ kubelet từ chối container: `CreateContainerConfigError: container has
runAsNonRoot and image will run as root`. Đặt `runAsUser` theo user mà image được dựng cho, và kiểm quyền ghi của các
đường dẫn ứng dụng cần ghi (volume + `fsGroup`, emptyDir cho `/tmp`).

## Quota namespace còn rộng nhưng pod `Pending` với `Insufficient cpu`. Chuyện gì xảy ra, bạn nói gì với khách?

Quota là giới hạn hành chính của namespace; scheduler xếp theo allocatable của node trừ requests của mọi pod trên node,
kể cả pod hệ thống và pod của namespace khác. Node nhỏ thì hết chỗ trước quota. Hướng xử lý: hạ `requests.cpu` về mức đo
thật (không đụng `limits.memory` dưới nhu cầu), hoặc xin IT thêm node. Nói với khách bằng số: tổng requests của bản cài,
allocatable của node (nhờ IT đọc), phần chênh.

## Tính tài nguyên của một release để xin quota: bạn cộng những gì?

Mỗi pod: theo từng loại, max(tổng container, initContainer lớn nhất). Nhân số replica. Cộng pod thêm lúc rolling update
(`maxSurge`), pod của Job migration/hook nếu có, và phần người khác đã dùng (`status.used`). Kiểm cả ba con số quota hay
đếm: `requests.cpu`, `requests.memory`, `limits.memory`, cùng số pod. Quên pod rolling update là lỗi kinh điển: cài lần
đầu được, nâng cấp lần đầu kẹt.

## Cluster air-gapped, không Docker, không root. Bạn đưa image vào registry nội bộ thế nào?

Image trong bundle ở dạng OCI layout/`docker save`. Đẩy thẳng lên registry bằng công cụ đọc OCI layout: `skopeo copy
oci-archive:…`, `crane push`, `regctl image import` (binary tĩnh, ghim sha256, mang theo bundle), hoặc vài chục dòng
Python gọi Registry HTTP API v2 (upload blob, rồi PUT manifest). Đặt tên đúng như chart sẽ render. Kiểm bằng
`/v2/<repo>/tags/list` trên registry, không bằng "pod đã chạy" (`IfNotPresent` có thể đang dùng cache của node).

## Khách nói: "Mở hết network cho namespace của anh cho nhanh". Bạn trả lời sao?

Cảm ơn, nhưng đề nghị viết đúng bảng luồng: ai gọi ai, cổng nào, vì sao. Allow-all trong namespace nghĩa là mọi pod khác
(kể cả của team khác) nói chuyện thẳng với database của sản phẩm; đội bảo mật sẽ hỏi lại lúc audit và người chịu trách
nhiệm là vendor. Gửi bảng luồng + NetworkPolicy + kết quả thử bằng pod thử (luồng được mở thông, luồng khác tắc). Làm
đúng từ đầu tốn thêm một giờ, sửa sau một sự cố tốn cả hợp đồng.

## NetworkPolicy `default-deny` có sẵn. Bạn đã mở ingress cho service của mình mà client vẫn không gọi được. Kiểm gì?

Kết nối cần hai cửa: egress của pod nguồn và ingress của pod đích. Client nằm trong namespace bị `default-deny` thì egress
của nó cũng đang đóng. Kiểm thêm: selector khớp đúng nhãn pod (không phải nhãn Deployment), cổng là `targetPort` của
container chứ không phải `port` của Service, DNS còn được mở, `from`/`to` không bị viết thành "hoặc" ngoài ý muốn. Và CNI
có thực thi NetworkPolicy không. Thử bằng pod mang đúng nhãn và `nc -z`.

## Khách chưa có Kubernetes, máy không ra internet. Bạn dựng k3s thế nào, và giao lại cho khách những gì?

Mang binary, tarball image air-gap và `install.sh` của đúng một bản, ghim và kiểm sha256 ở cả hai đầu. Đặt image vào thư
mục image của agent và viết `registries.yaml` cho registry nội bộ **trước** khi khởi động; cài bằng
`INSTALL_K3S_SKIP_DOWNLOAD=true`. Đọc phần điều kiện của tài liệu air-gap (mạng của node, cổng) và kiểm sau khi cài:
node `Ready`, pod hệ thống chạy, `INTERNAL-IP` đúng mạng, một ứng dụng thử kéo từ registry nội bộ và gọi được qua
Service. Giao lại: script cài chạy lại được, phiên bản, cách backup dữ liệu cluster, cách nâng cấp (cùng quy trình với
bản mới), và nói rõ một node là không HA.

## Khách chuyển từ k3s sang OpenShift. Những gì có khả năng gãy?

Danh tính pod: SCC `restricted-v2` gán UID ngẫu nhiên trong dải của namespace và GID 0, nên `runAsUser`/`fsGroup` cố
định bị từ chối, và image phải ghi được bằng nhóm 0 hoặc chỉ ghi vào volume. Đường vào: `Route` với TLS thay vì Ingress
tuỳ ý; NetworkPolicy phải cho router vào. Image: internal registry hoặc registry tập đoàn, pull secret. DNS ở
`openshift-dns` (cổng 5353), egress ra ngoài qua `EgressFirewall`. Cách làm: thử từng image với SCC mặc định trước khi
cài cả chart; image không chạy được với UID tuỳ ý là việc của vendor, không phải lý do xin `anyuid`.

## Platform team hỏi: "Vendor cần quyền gì?". Bạn soạn câu trả lời thế nào?

Từ lệnh tới API: liệt kê mọi bước vòng đời (cài, nâng cấp, rollback, backup, gỡ lỗi, gỡ cài đặt) và object/verb mỗi bước
gọi. Một Role trong namespace, không `*`, không quyền sửa RBAC hay impersonate, mỗi cặp resource+verb một dòng lý do và
rủi ro, mục "không xin" với đường thay thế, token có thời hạn, cách thu hồi, và cách tự kiểm sau khi cấp. Nhắc rằng RBAC
không thay admission: values đã qua `--dry-run=server` gửi kèm.

## Bạn đang screen-share với IT, `helm upgrade` của bản mới treo ở "pending-upgrade" và họ muốn xoá Secret của Helm cho xong. Bạn làm gì?

Dừng tay họ. Secret `sh.helm.release.v1.<tên>.v<n>` là lịch sử release; xoá sai thì mất đường rollback và Helm có thể
"quên" object đang chạy. Trước hết xem chuyện gì đang treo (`helm history`, event, pod mới có lên không, quota có chỗ cho
pod rolling update không). Nếu tiến trình Helm đã chết và release kẹt `pending-*`, `helm rollback <tên> <revision cuối
deployed>` là đường chuẩn. Ghi lại lệnh đã chạy và trạng thái trước/sau vào ticket.
