# Câu hỏi phỏng vấn: Containers

## Container khác VM thế nào? Kernel cung cấp những gì để có "container"?

VM ảo hoá phần cứng: mỗi VM có kernel riêng chạy trên hypervisor, ranh giới cô lập là phần cứng ảo. Container là tiến trình bình
thường của host, dùng chung kernel, được kernel giới hạn bằng: **namespace** (PID, mount, network, UTS, IPC, user, cgroup: thấy gì),
**cgroup v2** (dùng bao nhiêu CPU, RAM, PID, I/O), **capability** (được làm phần nào của root), **seccomp** (gọi được syscall nào),
**LSM** AppArmor/SELinux (truy cập tệp và tài nguyên nào), cộng **overlayfs** để ghép layer image chỉ đọc với một layer ghi.

Hệ quả: container khởi động dưới một giây và nhẹ, nhưng lỗ hổng kernel hay cấu hình nới lỏng (`--privileged`, `--pid=host`, mount
`docker.sock`) là đường ra host. Workload không tin cậy (đa thuê bao, code người dùng) nên dùng sandbox như gVisor hay micro VM như
Firecracker và Kata Containers.

## Gõ `docker run nginx` thì những thành phần nào tham gia?

CLI gọi REST API của `dockerd` qua `/var/run/docker.sock`. dockerd kiểm image (thiếu thì kéo từ registry theo distribution spec),
chuẩn bị network và mount, rồi gọi `containerd` qua gRPC. containerd chuẩn bị snapshot rootfs từ các layer, sinh `config.json`
theo OCI runtime spec và khởi động `containerd-shim-runc-v2`. Shim gọi `runc`: runc tạo namespace, cgroup, áp seccomp, AppArmor,
capability, `pivot_root` vào rootfs, rồi `exec` tiến trình nginx và thoát. Shim ở lại làm cha của container, giữ stdio và mã thoát,
nên dockerd hay containerd khởi động lại không giết container.

Trên Kubernetes, kubelet gọi thẳng containerd (hoặc CRI-O) qua CRI; Docker không còn trong đường đi từ 1.24.

## Vì sao container thoát với mã 137? Bạn điều tra thế nào?

137 = 128 + 9: tiến trình chết vì SIGKILL. Có hai nguồn phổ biến:

1. **OOM kill**: vượt giới hạn RAM của cgroup. `docker inspect -f '{{.State.OOMKilled}}'` là `true`, `dmesg` hay `journalctl -k`
   có dòng `Memory cgroup out of memory: Killed process`. Không có traceback vì SIGKILL không bắt được. Xem đồ thị bộ nhớ
   (`docker stats`, `container_memory_working_set_bytes`), tìm rò rỉ hay batch quá lớn, rồi mới quyết tăng limit.
2. **Hết grace period**: `docker stop` hay Kubernetes gửi SIGTERM, tiến trình không dừng trong thời hạn (10 giây Docker, 30 giây
   Kubernetes) nên bị SIGKILL. `OOMKilled` là `false`; thời gian dừng đúng bằng grace period. Tín hiệu không tới được app, hoặc app nhận mà không dừng kịp.

Phân biệt hai trường hợp bằng `OOMKilled`, thời gian dừng và log của orchestrator (`Reason: OOMKilled` trong `kubectl describe pod`).

## (Sự cố) Bảo mật vừa bật rootfs chỉ đọc cho mọi service. API Python khởi động lại liên tục, log báo `OSError: [Errno 30] Read-only file system`. Bạn làm gì?

Đừng tắt `read_only` cho cả service để "chữa cháy"; tìm đúng chỗ app ghi và mở đúng chỗ đó.

1. Khoanh vùng: chỉ service bị bật `read_only` mới lỗi, lỗi xảy ra lúc khởi động, traceback chỉ đường dẫn (`/app/.cache`,
   `/home/app/.config`, `/var/run/app.pid`...). Một lỗi thường che lỗi sau: sửa một đường dẫn rồi chạy lại.
2. Liệt kê mọi chỗ ghi một lần cho đủ: chạy image **không** `--read-only` ở staging, cho nó chạy vài phút qua các luồng chính, rồi
   `docker diff <c>` liệt kê tệp được thêm (`A`) hay sửa (`C`). Cộng thêm thư viện hay ghi ngầm: cache của pip, matplotlib,
   Hugging Face (`HOME`, `XDG_CACHE_HOME`), `__pycache__` (`PYTHONDONTWRITEBYTECODE=1`), tệp tạm (`/tmp`).
3. Sửa tối thiểu: tmpfs (Docker, compose `tmpfs:`) hay `emptyDir` (Kubernetes, có `sizeLimit`) cho đúng các thư mục đó; trỏ cache
   về `/tmp` bằng biến môi trường; dữ liệu cần sống qua lần khởi động lại thì là volume, không phải tmpfs.
4. Chứng minh: container khởi động sạch với `read_only`, healthcheck xanh, các luồng chính chạy, `docker diff` không còn gì ngoài
   các mount đã khai báo.
5. Phòng ngừa: CI chạy smoke test image với `--read-only --tmpfs /tmp` để lỗi lộ trước khi lên production; ghi các thư mục ghi được
   vào README của service; tmpfs tính vào giới hạn RAM của container, nên đặt kích thước để tránh OOM kill.

## Multi-stage build giải quyết vấn đề gì? Viết một Dockerfile multi-stage cho API Python.

Tách nơi build (cần compiler, header, trình quản lý gói, cache) khỏi nơi chạy (chỉ cần interpreter, dependency đã cài và code).
Image cuối nhỏ hơn, ít gói và ít CVE hơn, không có công cụ cho kẻ tấn công.

```dockerfile
FROM python:3.12.16-slim-trixie AS build
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH PIP_NO_CACHE_DIR=1
COPY requirements.txt .
RUN pip install -r requirements.txt

FROM python:3.12.16-slim-trixie
ENV PATH=/opt/venv/bin:$PATH PYTHONUNBUFFERED=1
RUN useradd --system --uid 10001 app
COPY --from=build /opt/venv /opt/venv
COPY app/ /srv/app/
WORKDIR /srv
USER 10001
HEALTHCHECK CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Điểm hay bị hỏi tiếp: venv phải chép sang image cùng distro và cùng phiên bản Python (đường dẫn interpreter ghi cứng trong venv);
`requirements.txt` chép trước code để cache; USER là số để `runAsNonRoot` kiểm được.

## Build cache của BuildKit hoạt động thế nào? Vì sao `RUN apt-get update` riêng một dòng là bẫy?

Mỗi bước có cache key: `FROM` theo digest image nền, `COPY` theo checksum nội dung tệp, `RUN` theo chuỗi lệnh cộng key của bước
trước. Một bước đổi thì mọi bước sau trong stage build lại. BuildKit không biết lệnh `RUN` lấy gì từ mạng: `RUN apt-get update`
đứng riêng được cache mãi, rồi một ngày bạn thêm gói vào dòng `apt-get install` phía sau và nó cài theo danh sách gói cũ hàng tháng
trước (có khi 404 vì gói đã bị thay). Viết `apt-get update && apt-get install -y --no-install-recommends ... && rm -rf
/var/lib/apt/lists/*` trong một `RUN`.

Muốn cache tải gói bền mà không vào image: `RUN --mount=type=cache`. Trong CI runner mới tinh không có cache cục bộ: dùng
`--cache-to/--cache-from type=registry` hay `type=gha`.

## Tag và digest khác nhau thế nào? Bạn tham chiếu image trong manifest production ra sao?

Tag là con trỏ đổi được; digest là SHA-256 của manifest, không đổi được. Image chính thức được build lại dưới cùng tag khi distro
vá lỗ hổng, và ai có quyền push cũng đẩy đè được tag của mình. Production tham chiếu `repo:1.8.2@sha256:...`: tag để người đọc,
digest để kéo. Hệ quả: không tự nhận bản vá, nên cần Renovate/Dependabot mở PR khi digest mới xuất hiện, CI build và quét, rồi
merge. Thêm tag immutability ở registry cho tag phát hành, và admission policy từ chối image chỉ có tag.

## Làm sao chạy container với ít quyền nhất? Liệt kê các lớp và cái giá của từng lớp.

- `USER` không phải root, UID số: rẻ, chỉ cần chỉnh quyền thư mục ghi.
- `--cap-drop ALL`, thêm đúng capability cần: rẻ; app nghe cổng thấp cần `NET_BIND_SERVICE` (hoặc nghe cổng cao).
- `no-new-privileges`: gần như miễn phí; chặn setuid.
- `--read-only` cộng tmpfs cho thư mục cần ghi: phải biết app ghi vào đâu; lỗi lúc khởi động nếu quên.
- seccomp và AppArmor mặc định: miễn phí; đừng tắt.
- Giới hạn RAM, CPU, PID: cần đo để đặt đúng; đặt sai thì OOM hay throttle.
- Rootless Docker, Podman rootless hay user namespace: tốn công cấu hình (cổng thấp, mạng, cgroup delegation) nhưng thoát container
  chỉ còn là UID vô danh.
- Không mount `docker.sock`, không `--privileged`, không `--pid=host`/`--network=host` trừ khi có lý do ghi rõ.

Trên Kubernetes, tập hợp này gần đúng là Pod Security Standard `restricted`.

## Rootless Docker hoạt động thế nào? Hạn chế là gì?

dockerd, containerd và container chạy dưới user thường, trong một user namespace ánh xạ dải UID từ `/etc/subuid` (ví dụ 100000 tới
165535) thành 0 tới 65535 bên trong. Root trong container là UID 100000 trên host: thoát được container thì không có quyền gì đáng
kể. Cài bằng `dockerd-rootless-setuptool.sh install`, chạy bằng systemd user service, `DOCKER_HOST=unix:///run/user/<uid>/docker.sock`.

Hạn chế: cổng dưới 1024 cần `net.ipv4.ip_unprivileged_port_start` hoặc capability cho `rootlesskit`; mạng đi qua slirp4netns hoặc
pasta nên chậm hơn và IP nguồn có thể bị che; giới hạn CPU/RAM cần cgroup v2 với systemd delegation; một số storage driver và
`--privileged` không khả dụng. Khác `userns-remap`: remap vẫn có daemon root, chỉ đổi UID của container.

## (Vì sao chọn công cụ này) Vì sao bạn chọn trivy làm scanner? Khi nào chọn thứ khác?

Trivy là một binary tĩnh, quét được image, thư mục mã nguồn, SBOM của vendor, IaC (Dockerfile, Kubernetes, Terraform), cluster
Kubernetes và bí mật bằng cùng một công cụ và một định dạng cấu hình; chạy offline được với DB đã cache, phù hợp CI tự host; output
JSON, SARIF, CycloneDX, SPDX; đọc VEX và `.trivyignore.yaml` có purl, statement, expired_at để mã hoá ngoại lệ. Đánh đổi: DB lớn
(khoảng 1,6 GB), cấu hình nhiều tầng, kết quả đổi theo DB.

Chọn khác khi: đã dùng syft cho SBOM thì Grype đi cặp tự nhiên; tổ chức dùng Docker Hub và Desktop có thể dùng Docker Scout để có
gợi ý image nền; cần gợi ý sửa trong PR và hỗ trợ thương mại thì Snyk; registry đã có quét sẵn (ECR, Harbor với trivy bên trong)
thì dùng nó cho quét định kỳ và trivy cho gate trong CI.

## Gate quét lỗ hổng hôm qua xanh hôm nay đỏ dù không ai đổi code. Bạn thiết kế gate thế nào để không bị team tắt đi?

Nguyên nhân: DB lỗ hổng được build lại nhiều lần mỗi ngày; CVE mới được công bố hay chấm lại cho gói đã có trong image. Thiết kế:

- Chỉ chặn HIGH/CRITICAL **có bản vá** (`severity`, `ignore-unfixed`), vì đó là thứ hành động được ngay.
- Ngoại lệ là dữ liệu trong repo (`.trivyignore.yaml` khoanh theo purl, có statement và expired_at, security duyệt qua CODEOWNERS);
  tuyên bố của vendor qua VEX.
- Tách gate build (chặn image mới) với quét định kỳ image đang chạy (mở ticket theo thời hạn vá: CRITICAL 7 ngày, HIGH 30 ngày),
  để hotfix lúc sự cố không bị chặn bởi CVE công bố sáng nay; có break-glass có log.
- Cache DB, ghi phiên bản DB vào log để giải thích hai lần chạy khác nhau.
- Giảm nguồn lỗ hổng tận gốc: image nền tối giản, gỡ thứ không dùng lúc chạy (pip, curl), rebuild định kỳ khi image nền có digest
  mới.
- Đo và công khai: tuổi của lỗ hổng có bản vá, số ngoại lệ theo team.

## (Thiết kế) Thiết kế chuỗi cung ứng image cho 60 service: từ commit tới production, đảm bảo chỉ image đã quét và ký mới chạy được.

1. **Image nền**: danh sách ngắn do platform sở hữu, ghim digest, Renovate cập nhật hằng tuần.
2. **Build** trong CI bằng BuildKit (rootless trên Kubernetes, không docker.sock): Dockerfile chuẩn qua hadolint/conftest; cache ra
   registry; nhãn OCI `revision`, `source`.
3. **Kiểm** trước khi push: test, trivy gate theo chính sách (HIGH/CRITICAL có bản vá), quét bí mật.
4. **Push** lên registry duy nhất với tag bất biến (commit SHA, semver), lấy digest.
5. **Attest và ký**: SBOM CycloneDX và provenance SLSA đính kèm (`--sbom`, `--provenance=mode=max`); cosign keyless ký digest bằng
   OIDC của workflow; chữ ký và attestation lưu cạnh image, ghi vào Rekor.
6. **Deploy theo digest** (GitOps, module 12): manifest chỉ chứa `repo@sha256:...`.
7. **Admission**: Kyverno hoặc Sigstore policy-controller từ chối image không theo digest, không có chữ ký từ đúng workflow, thiếu
   SBOM; Pod Security `restricted` cho runtime.
8. **Vận hành**: quét định kỳ image đang chạy dựa trên SBOM đã lưu (trả lời "ai bị ảnh hưởng bởi CVE mới" trong vài phút), ticket
   theo thời hạn vá, metric tuân thủ theo team, pull-through cache cho image ngoài.

Đánh đổi cần nói: độ phức tạp của PKI keyless và admission (một lỗi cấu hình chặn mọi deploy, cần chế độ audit trước và đường
break-glass), thời gian build tăng do attestation, và phụ thuộc vào dịch vụ Sigstore công cộng hoặc phải tự host.

## Khi nào dùng LXC/LXD thay cho Docker, và khi nào dùng VM?

LXD (hay Incus) cho **system container**: một hệ điều hành đầy đủ với systemd, nhiều service, sống lâu và được vá tại chỗ như một
máy. Hợp để thay VM nhẹ trên một host (lab nhiều máy, thử playbook Ansible, môi trường dev giống server thật, chạy app cũ cần
systemd), khởi động vài giây, mật độ cao hơn VM nhiều. Docker cho **application container**: một tiến trình, image bất biến, thay
thay vì vá, hợp với CI, microservice, Kubernetes.

Dùng VM khi cần kernel khác hay hệ điều hành khác (Windows, kernel module riêng), cô lập mạnh giữa các bên không tin nhau, hoặc
yêu cầu tuân thủ đòi ranh giới phần cứng ảo. LXD quản lý được cả VM bằng cùng lệnh, nên trong một số tổ chức nó là một lớp quản lý
chung cho cả hai.

## Image distroless không có shell. Bạn debug một container distroless đang lỗi trên production thế nào?

Không build lại image có shell để deploy đè: đổi thứ đang chạy, có khi làm mất chính lỗi, và mở lại bề mặt tấn công. Thay vào đó
gắn một container debug dùng chung namespace với container lỗi: trên Docker,
`docker run -it --rm --pid=container:<c> --network=container:<c> busybox` (thấy tiến trình, `/proc/<pid>/root` để đọc tệp, cùng
network để `wget localhost`); Docker Desktop có `docker debug`. Trên Kubernetes, `kubectl debug -it <pod> --image=busybox
--target=<container>` tạo ephemeral container. Kết hợp với log có cấu trúc, metric và `/proc/<pid>/status` để xem bộ nhớ, luồng.
Distroless còn có biến thể `:debug` có busybox, dùng ở staging, không dùng ở production.
