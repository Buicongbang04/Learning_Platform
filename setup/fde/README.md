# Lab VM "khách hàng" của track FDE

Bài tập track Forward Deployed Engineer chạy trên **VM thật** (QEMU/KVM) dựng từ cloud image chính thức, không phải
container giả lập. Mọi thao tác đi qua `fdekit.py` ở gốc repo: tải image, dựng overlay, seed cloud-init, SSH, snapshot
và dọn dẹp. Test không gọi `qemu-system-*` trần.

## Yêu cầu

| Thứ | Kiểm tra | Ghi chú |
| --- | --- | --- |
| CPU có ảo hoá, `/dev/kvm` đọc/ghi được | `ls -l /dev/kvm` và `id` (thuộc nhóm `kvm`) | Thiếu quyền: `sudo usermod -aG kvm $USER` rồi đăng xuất/đăng nhập lại |
| QEMU | `qemu-system-x86_64 --version`, `qemu-img --version` | Debian/Ubuntu: `sudo apt install qemu-system-x86 qemu-utils` |
| OpenSSH client | `ssh -V` | `ssh`, `scp`, `ssh-keygen` |
| Đĩa | ~35 GB trống cho `data/raw/fde-images/` | 4 cloud image (~4,1 GB) + golden image của 7 hồ sơ khách (1,3–2,5 GB mỗi cái) + snapshot dẫn xuất (chỉ phần khác golden) |
| RAM | mỗi VM 1–5 GB | `fdekit` skip khi RAM trống ít hơn RAM của VM + 512 MB |

Không cần `cloud-localds`/`genisoimage`: seed NoCloud (ISO nhãn `cidata`) được tạo bằng thư viện `pycdlib`.
Máy thiếu KVM hay QEMU thì test VM **skip** với thông báo, không treo.

## Cloud image đã ghim

Khai báo trong `fdekit.IMAGES`: URL bản phát hành có ngày/version cố định và sha256 lấy từ tệp checksum chính thức
lúc thêm (2026-11-03). `fetch_image()` tải một lần vào `data/raw/fde-images/`, kiểm sha256, tệp sai hay hỏng thì tải lại.

| Khoá | Bản | Nguồn checksum |
| --- | --- | --- |
| `ubuntu-22.04` | `release-20261004` | `SHA256SUMS` cạnh image |
| `ubuntu-20.04` | `release-20250624` (bản cuối của focal) | `SHA256SUMS` cạnh image |
| `rocky-8` | `8.10-20240528.0` GenericCloud Base | `CHECKSUM` cạnh image |
| `debian-12` | `20261018-2635` genericcloud | Debian chỉ công bố `SHA512SUMS`: đã tải, khớp sha512 chính thức, rồi ghi sha256 của đúng tệp đó |

Lần đầu chạy test VM, `fetch_image()` tải image cần dùng (ubuntu-22.04 ~730 MB) ngay trong test. Máy không có mạng
thì test skip; nên tải trước:

```bash
uv run python -c "import fdekit; fdekit.fetch_image('ubuntu-22.04')"
```

## Hồ sơ khách

Mỗi hồ sơ là một tệp `setup/fde/profiles/<hồ sơ>.yaml`, nạp vào `fdekit.PROFILES` (dataclass `Profile`).

| Hồ sơ | OS | Đĩa | RAM mặc định | sudo | Egress | Runtime | Dịch vụ phía host |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `lab-open` | Ubuntu 22.04 | 20 GB | 2048 MB | có | `open` | Docker + plugin `docker compose` | — |
| `hospital` | Ubuntu 20.04 | 8 GB | 2048 MB | có | `proxy` (TLS inspection) | Docker | mitmproxy |
| `bank` | Rocky Linux 8.10, SELinux enforcing | 20 GB | 2048 MB | **không** | `none` | Podman rootless | — |
| `lawfirm-staging` | Ubuntu 22.04 | 30 GB | 2048 MB | có | `none` | Docker | registry nội bộ |
| `factory` | Debian 12 | 12 GB | 3072 MB | có | `proxy` (không TLS inspection), netem | Docker CE + plugin `docker compose` | mitmproxy |
| `lawfirm-hardened` | Rocky Linux 8.10, SELinux enforcing | 20 GB | 5120 MB | **không** | `none` | Podman rootless (linger bật) | registry nội bộ |
| `lawfirm-prod` | Ubuntu 22.04 | 30 GB | 5120 MB | **không** | `none` | k3s air-gapped (namespace `quillo`) | registry nội bộ |

Trường tuỳ chọn của YAML (bỏ trống thì giữ hành vi Phase 1): `memory_mb` (RAM `customer_site()`/`vm(profile)` boot
mặc định, cũng là `facts.mem_mb`; mặc định 2048), `tmp_noexec`, `nofile`, `netem` (tham số `tc netem`), `k8s`
(`namespace`, `kubeconfig` trong VM; bắt buộc khi và chỉ khi runtime `k3s`). Ba trường "tật" được `prepare` truyền vào
script dựng golden dưới dạng biến `FDE_TMP_NOEXEC`, `FDE_NOFILE`, `FDE_NETEM` (`FDE_K8S_NAMESPACE`, `FDE_KUBECONFIG`
cho k3s), nên YAML là nguồn duy nhất; sửa YAML thì dựng lại golden bằng `--force`.

`Profile.facts` là "sự thật" để chấm báo cáo survey (13 khoá: `os_id`, `os_version`, `kernel_major`, `glibc`, `cpus`,
`mem_mb`, `disk_free_gb_max`, `gpu`, `proxy_url`, `sudo`, `selinux`, `runtime`, `egress`):

- `kernel_major` (`uname -r` lấy hai số đầu, vd. `5.15`), `glibc`, `disk_free_gb_max` (dung lượng trống của `/` làm
  tròn lên, VM mới boot thấy ít hơn hoặc bằng) và `gpu` đo trên golden, ghi trong YAML.
- `cpus` = 2 và `mem_mb` (= `memory_mb` của hồ sơ) là cấu hình `customer_site()` boot **mặc định** (không phụ thuộc máy host). Gọi
  `customer_site(..., memory_mb=...)` khác thì `mem_mb` thật khác theo; `MemTotal` trong VM luôn nhỏ hơn RAM cấp một ít.
- `os_id`/`os_version` lấy từ cloud image; `proxy_url`, `sudo`, `selinux`, `runtime`, `egress` suy từ hồ sơ.

`test_facts_match_vm` boot từng hồ sơ và so các giá trị này với lệnh thật trong VM.

## Chuẩn bị golden image

Mỗi hồ sơ khách có một golden image (đã cài sẵn runtime và "tật" của khách) ở `data/raw/fde-images/golden/<hồ sơ>.qcow2`.
Bài nào cần hồ sơ chưa có golden thì test skip kèm đúng lệnh cần chạy, ví dụ:

```bash
nice -n 15 uv run python -m fdekit prepare lab-open
nice -n 15 uv run python -m fdekit prepare hospital
nice -n 15 uv run python -m fdekit prepare bank
nice -n 15 uv run python -m fdekit prepare lawfirm-staging
nice -n 15 uv run python -m fdekit prepare factory
nice -n 15 uv run python -m fdekit prepare lawfirm-hardened
nice -n 15 uv run python -m fdekit prepare lawfirm-prod
```

Lệnh chỉ cần chạy một lần mỗi hồ sơ (khoảng 1–6 phút mỗi hồ sơ: đo được 64–93 s khi dựng riêng từng hồ sơ, 89–323 s khi
dựng cả bốn cùng lúc, chưa tính lần đầu tải cloud image; không tính vào ngân sách 300 s của bài); golden đã có thì lệnh
trả ngay, dựng lại bằng `--force`. Cách dựng: overlay trên cloud image, phóng to lên `disk_gb`, boot **có mạng** với
user `fde` có sudo tạm, chạy `setup/fde/cloud-init/<hồ sơ>.sh` (gỡ snapd và apt/dnf timer chạy nền, cài runtime từ kho
chính thức của distro, cấu hình "tật"), rồi xoá sudo tạm, key SSH, log cloud-init, machine-id, tắt sạch và ghi qcow2 độc
lập. Log cài đặt: `data/raw/fde-images/golden/<hồ sơ>.prepare.log`.

`prepare` cũng `docker pull` image phía host mà hồ sơ cần (`hospital`: mitmproxy, `lawfirm-staging`: registry), để
bài không phải tải image trong ngân sách 300 s. Thiếu image thì test skip kèm đúng lệnh, tự pull trước được:

```bash
docker pull mitmproxy/mitmproxy:12.2.3@sha256:00b77b5d8804c8ad18cb6caefbf9d5849e895e8986c5ce011f4ae30f4385962f
docker pull registry:2.8.3@sha256:a3d8aaa63ed8681a604f1dea0aa03f100d5895b6a58ace528858a7b332415373
```

Bài bật Keycloak hoặc file share bằng `extra_services` (mục "Keycloak và file share của khách") cần thêm hai image
dưới đây; chưa có thì test skip kèm đúng lệnh pull:

```bash
docker pull quay.io/keycloak/keycloak:26.8.1-1@sha256:a78d6b79572168cb25886b80a8b5b8d4ed4390743e3eecb810538683e209dd6b
docker pull ghcr.io/servercontainers/samba:smbd-only-a3.24.3-s4.23.8-r0@sha256:04fb3bd3da742ddb988f621e8c38b0dcbc26e7b4c438c9836abb43d937bc27e6
```

**Lưu ý an toàn:** lúc dựng golden VM chạy với `restrict` tắt, tức là trong vài phút dựng, VM vừa ra internet vừa
với tới mọi dịch vụ đang nghe `127.0.0.1` trên host qua `10.0.2.2`. Chỉ chạy các script trong `setup/fde/cloud-init/`
của repo này (đọc trước nếu bạn sửa), không dựng golden từ image lạ.

Golden không mang theo mạng hay quyền của lúc dựng: lúc chạy bài, `customer_site()`/`vm(profile)` áp lại egress và
sudo theo hồ sơ (bank: `fde` không có sudo; SELinux enforcing; Podman rootless chạy được không cần mạng, không có
image nào được tải sẵn).

Đo ngày 2026-11-04 trên laptop của repo (16 core, NVMe; ba hồ sơ sau dựng song song):

| Hồ sơ | Thời gian dựng | Kích thước golden | Runtime đã cài (kho distro) |
| --- | --- | --- | --- |
| `lab-open` | 64 s | 1,79 GiB | `docker.io 29.1.3-0ubuntu3~22.04.2`, `containerd 2.2.1-0ubuntu1~22.04.2`, `runc 1.3.4-0ubuntu1~22.04.1`, `docker-compose-v2 2.40.3+ds1-0ubuntu1~22.04.1` (dựng lại 2026-11-04) |
| `hospital` | 77 s | 1,60 GiB | `docker.io 26.1.3-0ubuntu1~20.04.1`, `containerd 1.7.24-0ubuntu1~20.04.2`, `runc 1.1.12-0ubuntu2~20.04.1` |
| `bank` | 93 s | 1,53 GiB | `podman 4.9.4-38.module+el8.10.0+40397+5e4f25d4` (AppStream, module `container-tools`) |
| `lawfirm-staging` | 72 s | 1,73 GiB | `docker.io 29.1.3-0ubuntu3~22.04.2`, `containerd 2.2.1-0ubuntu1~22.04.2`, `runc 1.3.4-0ubuntu1~22.04.1` (không có `docker-compose-v2`) |

Dựng lại cả bốn cùng lúc (`--force`, 2026-11-04) mất 89–323 s mỗi golden (bank chậm nhất do mirror Rocky), kích thước như trên.

Ba hồ sơ Phase 2, đo ngày 2026-11-10 (cùng laptop; `factory` và `lawfirm-prod` dựng song song):

| Hồ sơ | Thời gian dựng | Kích thước golden | Đã cài |
| --- | --- | --- | --- |
| `factory` | 31 s (99 s lần đầu, gồm tải cloud image Debian ~350 MB) | 1,29 GiB | `.deb` chính thức download.docker.com ghim sha256: `docker-ce`/`docker-ce-cli 5:29.9.2-1~debian.12~bookworm`, `containerd.io 2.4.2-3~debian.12~bookworm`, `docker-buildx-plugin 0.38.1-1~debian.12~bookworm`, `docker-compose-plugin 5.6.1-1~debian.12~bookworm` |
| `lawfirm-hardened` | 95 s | 1,53 GiB | `podman 4.9.4-38.module+el8.10.0+40397+5e4f25d4`, linger bật cho `fde` |
| `lawfirm-prod` | 91 s | 2,53 GiB | k3s `v1.37.1+k3s1` (binary + `k3s-airgap-images-amd64.tar.zst` + `install.sh` của đúng tag, ghim sha256; image air-gap import lúc dựng rồi xoá tarball), `kubectl v1.37.1` (dl.k8s.io), `helm v3.22.1` (get.helm.sh) |

k3s trên `lawfirm-prod` (VM 5120 MB, đã tắt traefik và servicelb, còn CoreDNS, local-path-provisioner,
metrics-server): API server trả `/readyz` khoảng 10–35 s sau khi SSH lên; lúc nghỉ dùng ~670 MB RAM trong VM (`free`;
`kubectl top node` 759 Mi; RSS `k3s-server` ~580 MiB, `containerd` ~160 MiB), còn ~4 GB cho ứng dụng.
k3s cần route mặc định kể cả khi air-gapped, mà mạng `restrict=on` của QEMU không phát gateway qua DHCP, nên golden
có `/etc/netplan/60-fde-default-route.yaml` (default via `10.0.2.2`, metric 1024); egress vẫn bị QEMU chặn.

Kernel/glibc của golden: Ubuntu 22.04 `5.15.0-198-generic`/2.35, Ubuntu 20.04 `5.4.0-216-generic`/2.31,
Rocky 8.10 `4.18.0-553.el8_10`/2.28, Debian 12 `6.1.0-54-cloud-amd64`/2.36. Gói cài theo trạng thái kho lúc dựng, nên dựng lại về sau có thể ra bản vá mới
hơn; `test_facts_match_vm` sẽ báo nếu `facts` cần cập nhật.

## Mạng lab và dịch vụ phía host

`with fdekit.customer_site("hospital") as s:` dựng "khách hàng" trọn vẹn và trả `Site`:

| Thuộc tính | Ý nghĩa |
| --- | --- |
| `s.vm` | `VM` (SSH, put/get, port…) |
| `s.proxy_ca` | tệp PEM CA của mitmproxy, sinh mới mỗi lần chạy trong thư mục lab; **không** được trust sẵn trong VM |
| `s.registry` | địa chỉ registry nhìn từ VM: `10.0.2.101:5000` (HTTP) |
| `s.registry_host` | địa chỉ registry nhìn từ host (`127.0.0.1:<cổng ngẫu nhiên>`) để đẩy image vào |
| `s.keycloak` / `s.keycloak_host` | Keycloak nhìn từ VM (`http://10.0.2.102:8080`) / từ host (`http://127.0.0.1:<cổng>`) |
| `s.keycloak_admin` | (user, mật khẩu) admin realm `master`, mật khẩu sinh mới mỗi lần chạy |
| `s.keycloak_client` | (`quillo`, client secret) của client confidential `quillo`, secret sinh mới mỗi lần chạy |
| `s.fileshare` / `s.fileshare_host` | share SMB nhìn từ VM (`//10.0.2.103/contracts`) / từ host (`("127.0.0.1", <cổng>)`) |
| `s.fileshare_creds` | (`svc-quillo`, mật khẩu sinh mới mỗi lần chạy) |
| `s.fileshare_dir` | thư mục phía host là nội dung của share (test đặt tệp vào đây) |

- Mỗi run id có **một** tiến trình canh: nó chạy QEMU và khi tiến trình pytest chết thì dọn cả QEMU, container,
  network lẫn thư mục lab (chỉ gọi `docker` khi run đó có dựng container).
- Dịch vụ phía host chạy bằng `testkit.DockerLab`, container tên `fde-ex-<run_id>-<dịch vụ>` trong network
  `fde-ex-<run_id>`, cổng chỉ publish trên `127.0.0.1`. Image ghim tag + digest:
  `mitmproxy/mitmproxy:12.2.3@sha256:00b77b5d…` (phát hành 2026-05-12) và `registry:2.8.3@sha256:a3d8aaa6…`
  (2025-02-14); giá trị đầy đủ ở `fdekit.MITMPROXY_IMAGE`/`REGISTRY_IMAGE`.
- Trong VM, proxy ở `10.0.2.100:3128`, registry ở `10.0.2.101:5000`, nối bằng `guestfwd` của QEMU: mỗi kết nối từ VM
  QEMU chạy một relay Python nhỏ (`guestfwd-relay.py` trong thư mục lab) nối sang cổng `127.0.0.1` của container.
- Egress `none`/`proxy` ⇒ `restrict=on`: không route ra internet, không DNS (resolver `10.0.2.3` của QEMU cũng bị chặn),
  không tới loopback host qua `10.0.2.2`; chỉ còn SSH/`forwards` và các `guestfwd` ở trên. Egress `open` ⇒ restrict tắt.
  `vm(profile)` tự suy `restrict` và `sudo` từ hồ sơ.

### Keycloak và file share của khách

`customer_site(profile, extra_services=("keycloak", "fileshare"))` bật thêm hai dịch vụ của "IT khách" cho một bài mà
không cần hồ sơ mới (`extra_services` nhận `registry`, `keycloak`, `fileshare`; `proxy` đi theo egress của hồ sơ nên
không bật thêm được). Hồ sơ cũng có thể khai báo chúng trong `services`.

- **Keycloak** `quay.io/keycloak/keycloak:26.8.1-1@sha256:a78d6b79…` (2026-10-23), `start-dev --import-realm`, giới hạn
  1024 MB. Trong VM ở `10.0.2.102:8080` (HTTP). `KC_HOSTNAME=http://10.0.2.102:8080` nên issuer luôn là
  `http://10.0.2.102:8080/realms/lawfirm`, dù token lấy qua cổng host hay từ trong VM (đã kiểm: `iss` của token lấy qua
  host bằng `issuer` trong discovery đọc từ VM). Sẵn sàng (discovery của realm trả 200) sau **~18–20 s** đo trên máy
  16 lõi; `customer_site` chạy container trước rồi boot VM song song, chỉ chờ Keycloak sau khi VM đã lên, nên không cần
  snapshot dẫn xuất cho dữ liệu Keycloak.
- Realm `lawfirm` (`setup/fde/keycloak/lawfirm-realm.json`): client confidential `quillo` (code flow + PKCE S256, bật
  thêm password grant để test lấy token; mapper audience `quillo` nên `aud` là `quillo`), nhóm `legal`, `finance`, `it`;
  user `an` ∈ legal, `binh` ∈ finance, `chi` ∈ legal + finance. Mật khẩu user cố định trong tệp realm, **chỉ dùng trong
  lab** (`fdekit.KEYCLOAK_PASSWORDS`). Client secret và mật khẩu admin sinh mới mỗi lần chạy, truyền vào container qua tệp
  trong thư mục lab (0700) mount chỉ đọc, không nằm trên dòng lệnh `docker run`.
- Như mặc định của Keycloak, token **không** có claim `groups` (không có mapper group membership). Đây là cấu hình thật
  của IdP khách, không phải lỗi của lab.
- `fdekit.keycloak_token(site, user, password)` lấy access token bằng password grant qua cổng host; chỉ dùng cho test.
- **File share** `ghcr.io/servercontainers/samba:smbd-only-a3.24.3-s4.23.8-r0@sha256:04fb3bd3…` (2026-10-22, Samba
  4.23.8 trên Alpine, image đa kiến trúc được cập nhật hằng tháng), giới hạn 256 MB. Trong VM ở `10.0.2.103:445`, chỉ
  SMB2/SMB3 (không NetBIOS, `guestfwd` chỉ TCP), share `contracts` **chỉ đọc** cho user `svc-quillo`, không cho khách
  vô danh. Nội dung share là `s.fileshare_dir` phía host, sẵn sàng sau dưới 1 s. Trong VM Ubuntu có thể mount bằng
  module `cifs` của kernel, không cần gói `cifs-utils`:
  `sudo mount -t cifs //10.0.2.103/contracts /mnt/c -o ro,ip=10.0.2.103,username=svc-quillo,password=…,vers=3.0`.
- Container `fde-ex-<run_id>-keycloak`/`-fileshare` được dọn cùng run id như proxy/registry, kể cả khi pytest bị
  `SIGKILL` (tiến trình canh xoá chúng trong vài giây).

### "Tật" của khách (cố ý, không phải lỗi của lab)

- `hospital`: IT khách đặt `http_proxy`/`https_proxy` trong `/etc/environment`, ngoài ra không cấu hình gì thêm
  (CA của proxy chưa được trust, Docker daemon và apt không được cấu hình proxy). Docker từ gói `docker.io` của Ubuntu
  20.04, **không** có plugin `docker compose`; muốn cài qua apt thì phải đi qua proxy trên.
- `lawfirm-staging`: registry nội bộ chạy HTTP thường ở `10.0.2.101:5000`; Docker trong VM chưa khai báo registry này
  trong `insecure-registries`. Docker cài từ gói `docker.io` của Ubuntu, **không** có plugin `docker compose` (khác
  `lab-open`), mà máy không ra internet: bundle offline phải tự mang binary compose v2 độc lập.
- `factory`: máy Debian 12 ở xưởng, 3 GB RAM. Ra internet qua proxy **không** TLS inspection (CA hệ thống đủ dùng),
  `http_proxy`/`https_proxy` trong `/etc/environment` như `hospital`, Docker daemon chưa cấu hình proxy. Đường truyền
  xấu: `fde-netem.service` chạy lúc boot `tc qdisc replace dev <giao diện route mặc định> root netem delay 150ms 50ms
  loss 3%` (áp cho mọi gói đi ra, kể cả SSH của bạn). `/tmp` là tmpfs 512 MB `noexec,nosuid,nodev` (chép binary vào
  `/tmp` rồi chạy sẽ "Permission denied"). Giới hạn `nofile` mềm và cứng 1024 cho phiên đăng nhập (`limits.d`) và cho
  service systemd (`DefaultLimitNOFILE`). Docker CE 29.9.2 + plugin compose 5.6.1 cài từ `.deb` chính thức của
  download.docker.com, ghim sha256 trong `lib.sh`.
- `lawfirm-hardened`: như `bank` (Rocky 8.10, SELinux enforcing, không sudo, không mạng, Podman rootless) nhưng IT đã
  bật linger cho `fde` (`loginctl enable-linger`, user manager chạy từ lúc boot) mà **chưa** bật `podman.socket` của
  user; có registry nội bộ HTTP ở `10.0.2.101:5000`, Podman chưa khai báo nó là insecure.
- `lawfirm-prod`: k3s air-gapped do IT khách cài và quản, `fde` không có sudo và không đọc được
  `/etc/rancher/k3s/k3s.yaml`; chỉ có `~/.kube/config` (token ServiceAccount `quillo/fde`, server
  `https://127.0.0.1:6443`, API server chỉ với tới từ trong VM). Quyền: Role `fde-deployer` (pods, services, configmaps,
  secrets, PVC, serviceaccounts, deployments, statefulsets, jobs, networkpolicies, ingresses, PDB, HPA trong `quillo`)
  và RoleBinding tới ClusterRole `view` trong `quillo`; không có quyền cluster nào (`auth can-i get nodes` = no).
  ResourceQuota, LimitRange, nhãn namespace chỉ đọc. Route mặc định qua `10.0.2.2` chỉ để k3s chạy: VM vẫn không tới
  được internet hay dịch vụ `127.0.0.1` của host (`test_lawfirm_prod_rbac` kiểm cả hai).
  Namespace `quillo` gắn nhãn PSA `enforce=restricted` (cả `warn`, `audit`), `ResourceQuota` (`requests.cpu: 3`,
  `requests.memory: 4Gi`, `limits.memory: 5Gi`, `pods: 12`, nên pod thiếu requests/limits bị từ chối), `LimitRange`
  chỉ đặt `max` cho Pod (cpu 2, memory 3Gi) và PVC (10Gi) — kiểu `Pod` không sinh default nên container vẫn phải tự
  khai báo resources; NetworkPolicy `default-deny` chặn mọi ingress/egress trừ DNS tới CoreDNS. `fde` được tạo, sửa,
  xoá NetworkPolicy **của mình** (tên bất kỳ khác `default-deny`) để mở đúng luồng cần; riêng `default-deny` do IT
  giữ: ValidatingAdmissionPolicy `quillo-protect-default-deny` từ chối UPDATE/DELETE policy tên `default-deny` khi
  người gọi là ServiceAccount `quillo/fde` (RBAC không chặn theo tên được, nên `kubectl auth can-i delete
  networkpolicy` vẫn trả `yes`, nhưng lệnh thật bị admission từ chối; không có `deletecollection`). `registries.yaml`
  mirror `docker.io` và `10.0.2.101:5000` về registry nội bộ HTTP. `helm`, `kubectl` có trong `PATH`.

## Một VM của bài tập trông thế nào

- Overlay qcow2 riêng trên golden: bài nào cũng bắt đầu từ trạng thái sạch, golden không bao giờ bị ghi.
- Seed cloud-init chỉ chứa **khoá công khai** SSH sinh riêng cho lần chạy; user trong VM là `fde`.
- Mạng user-mode của QEMU, chỉ bind `127.0.0.1` phía host; SSH và các cổng `forwards` là cổng trống ngẫu nhiên.
- Khi `restrict` tắt (mặc định, hồ sơ egress `open`), VM ra internet được và địa chỉ `10.0.2.2` trong VM trỏ tới
  loopback của host: mọi dịch vụ đang nghe `127.0.0.1` trên máy (Postgres, MLflow…) đều với tới được từ VM. Hồ sơ
  egress `none`/`proxy` bật `restrict=on`: VM chỉ còn các `hostfwd`/`guestfwd` được khai báo.
- Tên tiến trình `fde-ex-<run id 8 ký tự>`, thư mục lab `.fde-lab/fde-ex-<run id>/` (overlay, seed, key, log console).
- QEMU và container của `customer_site` chết theo tiến trình pytest (kể cả khi bị `SIGKILL` do app cắt test sau 300 s,
  và kể cả VM mở từ luồng phụ): một tiến trình canh nhỏ giữ đầu đọc của pipe "lifeline", thấy EOF thì giết QEMU, xoá
  container/network `fde-ex-<run_id>*` và thư mục lab.

## Snapshot dẫn xuất

Bài/milestone cần bắt đầu từ "máy khách đã cài sẵn X" (vd. quillo 1.0.0 đã chạy trên `lawfirm-prod`) không dựng lại X
trong ngân sách 300 s: nó boot từ một **snapshot dẫn xuất** dựng một lần từ golden bằng **lời giải tham chiếu**.

- Đăng ký: tệp `setup/fde/derived/<tên>.py` có `PROFILE` (hồ sơ), `INPUTS` (list `Path` tương đối gốc repo hoặc chuỗi
  như version, digest), `SITE` (`True` thì `build` nhận `Site` của `customer_site`, không thì `VM`), `MEMORY_MB`
  (`None` = RAM của hồ sơ) và hàm `build(target)`. Nạp vào `fdekit.DERIVED`.
- Dựng (chỉ bằng CLI, không tính vào 300 s): `nice -n 15 uv run python -m fdekit derive <tên>` (`--force` để dựng lại,
  `derive --list` xem trạng thái). Lệnh dựng golden nếu thiếu, boot hồ sơ, chạy `build`, xoá key SSH của lần dựng, tắt
  sạch, rồi ghi `data/raw/fde-images/derived/<tên>-<khoá>.qcow2` chỉ chứa phần khác golden (backing file là golden đã
  `resolve`, nên đừng di chuyển `data/raw/fde-images/golden/`). Bản cũ cùng tên bị xoá.
- Khoá = 12 hex đầu của sha256 trên: sha golden, sha tệp đăng ký, sha từng tệp/cây thư mục trong `INPUTS` theo thứ tự
  (bỏ `__pycache__`, `*.pyc`, `.git`…), và chuỗi trong `INPUTS`. Sửa lời giải tham chiếu, bundle, script hay dựng lại
  golden đều đổi khoá.
- Trong test: `fdekit.derived("<tên>")` trả đường dẫn để boot `fdekit.vm(profile, base=path)` hoặc
  `fdekit.customer_site(profile, base=path)`. Không bao giờ dựng: thiếu golden thì skip kèm lệnh `prepare`, chưa có
  snapshot thì skip "Chưa có snapshot dẫn xuất … Chạy một lần: uv run python -m fdekit derive <tên>", có bản với khoá
  khác thì skip "… đã cũ … Chạy lại: …". Tên chưa có tệp đăng ký là `ValueError` (CLI chỉ dựng được tên đã đăng
  ký, nên không có snapshot "tự do" mà lệnh skip chỉ tới lại không chạy được).
- Chỉ đĩa VM nằm trong snapshot: dịch vụ phía host (registry, proxy) của `customer_site` luôn dựng mới và rỗng. Image
  cần có sẵn thì để trong VM (containerd/Podman/Docker của VM), không phải trong registry.
- `selftest` (`lab-open` có `/home/fde/marker`) là snapshot tự kiểm của `test_derived_boot_roundtrip`: test gọi
  `python -m fdekit derive selftest --force` qua `fdekit.main` (đi đúng đường CLI) rồi boot từ kết quả.
- `05-gpu-field-factory`, `05-gpu-field-lab` (module 05): `factory` và `lab-open` (5120 MB) đang chạy quillo 1.0.0 bằng
  compose (`~/quillo-1.0.0`, `llm-small`), có thêm `llm-medium` ở `~/models/`. Dựng từ bundle
  `tracks/fde/product/dist/quillo-1.0.0.tar` bằng `setup/fde/derived/05-gpu-field-quillo.sh` (đầu vào của khoá: bundle,
  script, sha256 của `llm-medium`); netem của `factory` bị tắt trong lúc chép và bật lại ở lần boot sau.

## PC GPU

Driver NVIDIA trên laptop của repo không chạy, nên mọi bài bắt buộc chạy bằng CPU. Bài GPU thật là **tuỳ chọn**, chạy
trên PC có GPU của bạn qua SSH; `fdekit.require_pc()` skip với thông báo "Bài GPU tuỳ chọn: đặt FDE_PC_SSH=user@host
trong setup/.env (xem setup/fde/README.md mục PC GPU)" khi chưa đặt biến. Bộ chấm không bao giờ tự dò hay kết nối PC
khi biến chưa đặt.

Chuẩn bị một lần trên PC (bạn tự làm, có quyền admin trên PC):

1. Bật OpenSSH server (Ubuntu: `sudo apt install openssh-server`; Windows + WSL2 thì bật trong WSL và forward cổng).
2. Tạo user riêng **không sudo** cho lab: `sudo adduser --disabled-password fde-lab` (không thêm vào nhóm `sudo`,
   `docker` chỉ khi bài cần chạy container GPU). Kiểm tra `nvidia-smi` chạy được dưới user này.
3. Trên laptop, sinh khoá riêng cho PC và chỉ dùng khoá này: `ssh-keygen -t ed25519 -f ~/.ssh/fde-pc -N ""`, chép
   `~/.ssh/fde-pc.pub` vào `~fde-lab/.ssh/authorized_keys` trên PC, thêm vào `~/.ssh/config` của laptop:
   `Host <địa chỉ PC>` / `User fde-lab` / `IdentityFile ~/.ssh/fde-pc` / `IdentitiesOnly yes`. Đăng nhập tay một lần
   (`ssh fde-lab@<địa chỉ PC>`) để xác nhận host key.
4. Đặt `FDE_PC_SSH=fde-lab@<địa chỉ PC>` trong `setup/.env`.

`PC.ssh(cmd)` chạy `ssh -o BatchMode=yes -o ConnectTimeout=10 <FDE_PC_SSH> <cmd>` (không hỏi mật khẩu, không đổi
cấu hình host key của bạn); `PC.gpu()` trả `name`, `memory_mb`, `driver`, `cuda` từ `nvidia-smi --query-gpu`.
Bài chỉ ghi vào `~/fde-ex-<run_id>` trên PC (`PC.workdir`) và `PC.cleanup()` (hoặc ra khỏi `with fdekit.require_pc()
as pc:`) chỉ xoá đúng thư mục đó.

## Dọn dẹp

```bash
uv run python -m fdekit leftovers          # liệt kê tiến trình QEMU, thư mục .fde-lab, container/network fde-ex-* còn sót
uv run python -m fdekit clean <run_id>     # dọn đúng một run id (8 ký tự hex)
uv run python -m fdekit clean-tmp          # xoá /var/tmp/fde-capstone-* của bạn mà tiến trình tạo ra đã chết
```

`leftovers` không có `run_id` chỉ để xem; không có lệnh xoá hàng loạt vì nhiều phiên có thể chạy song song trên cùng máy.
`leftovers` báo thêm thư mục tạm của bộ chấm capstone (`/var/tmp/fde-capstone-<pid>-*`, bundle ~1,1 GB) còn sót khi
pytest bị `SIGKILL`: tên mang pid của tiến trình pytest, nên `clean-tmp` chỉ xoá thư mục thuộc user của bạn mà pid đó đã
chết, không đụng thư mục của phiên đang chạy.

## Biến trong `setup/.env`

| Biến | Dùng cho |
| --- | --- |
| `FDE_CAPSTONE_DIR` | Đường dẫn repo capstone **của bạn** (repo git riêng, ngoài repo học). Chưa đặt thì test capstone skip |
| `FDE_PC_SSH` | `user@host` của PC có GPU cho bài GPU tuỳ chọn (mục "PC GPU"); chưa đặt thì các bài đó skip |
