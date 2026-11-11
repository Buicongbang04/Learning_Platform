# Lời giải: k3s air-gapped trên máy staging của công ty luật

Lời giải ở `install_k3s.sh` cạnh tệp này:

```bash
SOLUTION=1 nice -n 15 uv run pytest tracks/fde/modules/06-k8s-at-customer/exercises/intermediate/02-k3s-airgap -q -s
```

Đo 2026-11-11 trên máy của repo: ~60 s (boot ~12 s, chép ~270 MB ~2 s, cài và k3s sẵn sàng ~25 s, lần cài thứ hai
~15 s).

## Ba lớp hỏng

**1. Image hệ thống tải từ internet.** Quickstart chỉ cài binary; k3s cần image `pause`, CoreDNS, local-path,
metrics-server… và không thấy chúng trên đĩa thì kéo từ Docker Hub:

```text
failed to pull image "rancher/mirrored-pause:3.10.2": … Head "https://registry-1.docker.io/v2/rancher/mirrored-pause/
manifests/3.10.2": dial tcp: lookup registry-1.docker.io: Try again
```

Mọi pod (kể cả CoreDNS) kẹt `ContainerCreating` vì thiếu sandbox `pause`; node vẫn `Ready` vì kubelet và API server là
tiến trình của k3s, không phải pod. Sửa: đặt `k3s-airgap-images-amd64.tar.zst` vào `/var/lib/rancher/k3s/agent/images/`
**trước** khi k3s khởi động (k3s nạp mọi tarball trong thư mục đó lúc start; đặt sau thì phải restart).

**2. Registry HTTP.** Pod `hello` `ErrImagePull`: `http: server gave HTTP response to HTTPS client`. containerd của k3s
mặc định dùng HTTPS cho mọi registry trừ localhost. Sửa: `/etc/rancher/k3s/registries.yaml` khai mirror
`"10.0.2.101:5000"` với endpoint `http://10.0.2.101:5000`, viết trước khi k3s start (đọc lúc khởi động). Đây không phải
`insecure-registries` của Docker: Docker trên máy này là runtime khác, cấu hình riêng.

**3. Không có route mặc định IPv4.** Hai lớp trên sửa xong, `hello` chạy, pod trong cluster gọi được service, nhưng từ
chính máy `curl http://<ClusterIP>/` treo. Lý do: máy chỉ có route subnet `10.0.2.0/24` IPv4, còn IPv6 có route mặc
định (router advertisement của mạng). k3s chọn địa chỉ node theo route mặc định, nên lặng lẽ dựng cluster **chỉ IPv6**
(`INTERNAL-IP fec0::…`, ClusterIP `fd00:43::…`); traffic từ host tới ClusterIP không có route để đi qua NAT của
kube-proxy. Ép `node-ip: 10.0.2.15` thì flannel thoát `failed to get default interface: unable to find default route`
và k3s khởi động lại liên tục. Tài liệu air-gap của k3s ghi rõ: máy không có route mặc định thì phải tạo một cái (route
blackhole qua interface dummy cũng đủ), vì k3s cần nó để tự dò IP node và cho ClusterIP routing.

Sửa: chỉ khi chưa có route mặc định IPv4, thêm `default via 10.0.2.2` (gateway theo phiếu khảo sát) bằng `ip route add`
cho lần chạy này và `/etc/netplan/60-k3s-default-route.yaml` để còn sau reboot (`netplan generate`, không `netplan apply`
giữa phiên SSH). Route không mở egress: firewall của khách vẫn chặn; trên lab, QEMU chặn.

## Các quyết định

- **Kiểm sha256** ba tệp trước khi cài (`sha256sum -c`), ghim trong script: tệp mang vào bằng USB/scp phải kiểm ở máy
  đích, không chỉ ở máy tải.
- **Viết mọi cấu hình trước `install.sh`**: `install.sh` tạo unit và start k3s; cấu hình viết sau đòi restart.
- **Chạy lại an toàn**: `install` ghi đè binary cùng nội dung, tarball chỉ chép khi khác (`cmp`), route chỉ thêm khi chưa
  có, `install.sh` chạy lại thì restart service với cùng cấu hình; dữ liệu cluster (`/var/lib/rancher/k3s/server`) giữ
  nguyên nên `hello` vẫn chạy sau lần hai.
- Không tắt Docker hay đổi cấu hình Docker: k3s dùng containerd riêng của nó (`/run/k3s/containerd`).

## Chấp nhận khác

- Route blackhole qua interface dummy (`ip link add dummy0 type dummy`, `ip route add default dev dummy0 metric 1024`,
  bền vững bằng systemd-networkd `.netdev`/`.network`) thay vì gateway: đúng theo tài liệu k3s và không cần biết gateway.
- `INSTALL_K3S_EXEC` hoặc `config.yaml` để tắt traefik/servicelb khi máy ít RAM: đạt (test chỉ đòi CoreDNS,
  local-path-provisioner, metrics-server).
- Không chấp nhận: dual-stack/IPv6-only rồi sửa test cho hợp; `curl` từ host phải tới được service như mọi cluster
  bình thường.
