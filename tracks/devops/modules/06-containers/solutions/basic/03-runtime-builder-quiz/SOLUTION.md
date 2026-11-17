# Lời giải: chọn runtime, builder và cách tham chiếu image

| Câu | Đáp án | Ràng buộc quyết định |
| --- | --- | --- |
| `prod-image-reference` | c. tag kèm digest | Mọi node phải chạy đúng bản đã quét và duyệt |
| `tag-rebuilt` | b. Tag được build lại | Image chính thức build lại cùng tag khi distro vá lỗ hổng |
| `ci-without-daemon` | c. BuildKit hoặc Buildah rootless | Cấm privileged và cấm docker.sock |
| `dev-laptop-no-root-daemon` | a. Podman rootless | Không daemon root, cần CLI giống docker và khái niệm pod |
| `kubernetes-node-runtime` | b. CRI runtime (containerd, CRI-O) | dockershim bị bỏ từ 1.24 |
| `system-container` | b. LXD/Incus | Cần systemd và nhiều service như một máy thật |
| `debug-distroless` | b. Container debug dùng chung namespace | Không sửa image production để điều tra |
| `exit-137` | c. Vượt giới hạn RAM của cgroup | `OOMKilled: true` |
| `reduce-attack-surface` | a, b, c | Non-root, rootfs chỉ đọc, bỏ capability |

## Giải thích từng câu

### `prod-image-reference`: tag kèm digest

`olist-api:1.8.2@sha256:...` cho người đọc biết phiên bản, còn runtime kéo theo digest: nếu ai đó đẩy đè tag `1.8.2` (vô tình,
hay do registry cho phép tag mutable), node vẫn kéo đúng bản đã quét. `latest` (a) và `main` (d) là con trỏ dời liên tục: hai
node kéo cách nhau một giờ có thể chạy hai bản khác nhau, rollback không biết quay về đâu. Tag semver (b) "không bao giờ đổi"
chỉ là quy ước; chỉ registry bật tag immutability (ECR, Harbor, Artifact Registry có tuỳ chọn này) mới đảm bảo được.

### `tag-rebuilt`: tag được build lại

Image chính thức trên Docker Hub (`python`, `nginx`, `postgres`) được build lại định kỳ dưới cùng tag khi Debian hay Alpine phát
hành bản vá. Digest đổi vì nội dung đổi; đó là hành vi bình thường. Docker không nén lại layer theo cách làm đổi digest (c), và
digest là hàm của nội dung, không phụ thuộc máy hay thời điểm pull (d). Bài học: ghim digest để build tái lập được, và để công
cụ như Renovate mở PR khi digest mới xuất hiện.

### `ci-without-daemon`: BuildKit rootless hoặc Buildah rootless

BuildKit có chế độ rootless (`moby/buildkit:rootless`, `buildctl-daemonless.sh`) chạy trong pod không privileged (cần user
namespace và thường cần tắt seccomp/AppArmor cho pod hoặc dùng `--oci-worker-no-process-sandbox`). Buildah rootless build từ
Dockerfile mà không cần daemon. Mount docker.sock (a) là trao quyền root của node cho job; DinD (b) cần privileged. Kaniko (d)
từng là lựa chọn phổ biến nhưng repo gốc `GoogleContainerTools/kaniko` đã được lưu trữ (archived) năm 2025; các fork như của
Chainguard vẫn duy trì, nhưng "bản gốc của Google được bảo trì" là sai.

### `dev-laptop-no-root-daemon`: Podman rootless

Podman không có daemon: mỗi lệnh `podman run` là tiến trình con của user, chạy trong user namespace. CLI gần như trùng docker
(`alias docker=podman` chạy được phần lớn script), có `podman pod` và `podman kube generate` sinh YAML Kubernetes. `ctr` (b) là
CLI debug của containerd, không thân thiện và không tương thích docker. LXD (c) chạy system container, không thay `docker run`.
Buildah (d) chỉ build image.

### `kubernetes-node-runtime`: CRI runtime

kubelet gọi runtime qua CRI (gRPC). Docker Engine không nói CRI; trước 1.24 kubelet dùng dockershim để dịch, từ 1.24 shim bị bỏ.
kind và đa số cluster managed (EKS, GKE, AKS) dùng containerd; OpenShift dùng CRI-O. Dưới containerd là shim và runc tạo
container thật. nerdctl (c) là CLI giống docker cho containerd, hữu ích để debug trên node, kubelet không gọi nó. Podman (d) có
khái niệm pod nhưng không phải CRI runtime.

### `system-container`: LXD hoặc Incus

LXD (và fork cộng đồng Incus) chạy system container: một hệ điều hành đầy đủ với systemd làm init, nhiều service, khởi động vài
giây, dùng chung kernel host nên nhẹ hơn VM nhiều. Rất hợp để thử playbook Ansible (module 09). Docker container chạy sshd làm
PID 1 (a) không có systemd, cron, journal. Distroless (c) là image tối giản cho một ứng dụng. Kaniko (d) chỉ build image.

### `debug-distroless`: container debug dùng chung namespace

`docker debug <container>` (có trong Docker Desktop), hoặc với Docker Engine tự chạy `docker run -it --pid=container:<id>
--network=container:<id> busybox` cho một container debug nhìn thấy tiến trình và mạng của container lỗi. Trên Kubernetes là
`kubectl debug -it <pod> --image=busybox --target=<container>` (ephemeral container). Build lại image có bash (a) là đổi thứ
đang chạy, có khi làm mất chính lỗi cần tìm, và mở lại bề mặt tấn công. `--privileged` (c) không thêm shell vào image và là quyền
root trên host. Đổi image nền (d) là bỏ mục đích của distroless.

### `exit-137`: vượt giới hạn RAM

137 = 128 + 9: tiến trình chết vì SIGKILL. `OOMKilled: true` khẳng định kernel OOM killer của cgroup đã giết nó vì vượt
`--memory`. Không có traceback vì SIGKILL không bắt được. Đo bằng `docker stats` hoặc metric `container_memory_working_set_bytes`,
rồi sửa rò rỉ hoặc đặt limit hợp lý (và với Python, giới hạn kích thước batch). Nếu `OOMKilled` là `false` mà vẫn 137, thường là
`docker stop` hết grace period rồi SIGKILL (xem Intermediate 01). Healthcheck fail (d) chỉ đánh dấu unhealthy; Docker Engine
không tự kill container unhealthy (Swarm và Kubernetes thì có).

### `reduce-attack-surface`: a, b, c

User không phải root (a) giới hạn thiệt hại khi bị chiếm tiến trình. Rootfs chỉ đọc (b) chặn kẻ tấn công ghi binary hay sửa
code; `/tmp` là tmpfs cho chỗ ghi tạm. `cap_drop: [ALL]` cộng `no-new-privileges` (c) bỏ các quyền đặc biệt của root trong
container và chặn leo quyền qua binary setuid. `privileged` (d) ngược hẳn: gần như toàn quyền trên host. Tag `latest` (e) không
đảm bảo bản vá và phá tính tái lập; cập nhật bản vá bằng rebuild có chủ đích và ghim digest mới.
