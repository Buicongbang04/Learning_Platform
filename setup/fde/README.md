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
| Đĩa | ~25 GB trống cho `data/raw/fde-images/` | 4 cloud image (~3,8 GB) + golden image của từng hồ sơ khách |
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

| Hồ sơ | OS | Đĩa | sudo | Egress | Runtime | Dịch vụ phía host |
| --- | --- | --- | --- | --- | --- | --- |
| `lab-open` | Ubuntu 22.04 | 20 GB | có | `open` | Docker + plugin `docker compose` | — |
| `hospital` | Ubuntu 20.04 | 8 GB | có | `proxy` (TLS inspection) | Docker | mitmproxy |
| `bank` | Rocky Linux 8.10, SELinux enforcing | 20 GB | **không** | `none` | Podman rootless | — |
| `lawfirm-staging` | Ubuntu 22.04 | 30 GB | có | `none` | Docker | registry nội bộ |

`Profile.facts` là "sự thật" để chấm báo cáo survey (13 khoá: `os_id`, `os_version`, `kernel_major`, `glibc`, `cpus`,
`mem_mb`, `disk_free_gb_max`, `gpu`, `proxy_url`, `sudo`, `selinux`, `runtime`, `egress`):

- `kernel_major` (`uname -r` lấy hai số đầu, vd. `5.15`), `glibc`, `disk_free_gb_max` (dung lượng trống của `/` làm
  tròn lên, VM mới boot thấy ít hơn hoặc bằng) và `gpu` đo trên golden, ghi trong YAML.
- `cpus` = 2 và `mem_mb` = 2048 là cấu hình `customer_site()` boot **mặc định** (không phụ thuộc máy host). Gọi
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

Kernel/glibc của golden: Ubuntu 22.04 `5.15.0-198-generic`/2.35, Ubuntu 20.04 `5.4.0-216-generic`/2.31,
Rocky 8.10 `4.18.0-553.el8_10`/2.28. Gói cài theo trạng thái kho lúc dựng, nên dựng lại về sau có thể ra bản vá mới
hơn; `test_facts_match_vm` sẽ báo nếu `facts` cần cập nhật.

## Mạng lab và dịch vụ phía host

`with fdekit.customer_site("hospital") as s:` dựng "khách hàng" trọn vẹn và trả `Site`:

| Thuộc tính | Ý nghĩa |
| --- | --- |
| `s.vm` | `VM` (SSH, put/get, port…) |
| `s.proxy_ca` | tệp PEM CA của mitmproxy, sinh mới mỗi lần chạy trong thư mục lab; **không** được trust sẵn trong VM |
| `s.registry` | địa chỉ registry nhìn từ VM: `10.0.2.101:5000` (HTTP) |
| `s.registry_host` | địa chỉ registry nhìn từ host (`127.0.0.1:<cổng ngẫu nhiên>`) để đẩy image vào |

- Mỗi run id có **một** tiến trình canh: nó chạy QEMU và khi tiến trình pytest chết thì dọn cả QEMU, container,
  network lẫn thư mục lab (chỉ gọi `docker` khi run đó có dựng container).
- Dịch vụ phía host chạy bằng `testkit.DockerLab`, container tên `fde-ex-<run_id>-proxy`/`-registry` trong network
  `fde-ex-<run_id>`, cổng chỉ publish trên `127.0.0.1`. Image ghim tag + digest:
  `mitmproxy/mitmproxy:12.2.3@sha256:00b77b5d…` (phát hành 2026-05-12) và `registry:2.8.3@sha256:a3d8aaa6…`
  (2025-02-14); giá trị đầy đủ ở `fdekit.MITMPROXY_IMAGE`/`REGISTRY_IMAGE`.
- Trong VM, proxy ở `10.0.2.100:3128`, registry ở `10.0.2.101:5000`, nối bằng `guestfwd` của QEMU: mỗi kết nối từ VM
  QEMU chạy một relay Python nhỏ (`guestfwd-relay.py` trong thư mục lab) nối sang cổng `127.0.0.1` của container.
- Egress `none`/`proxy` ⇒ `restrict=on`: không route ra internet, không DNS (resolver `10.0.2.3` của QEMU cũng bị chặn),
  không tới loopback host qua `10.0.2.2`; chỉ còn SSH/`forwards` và các `guestfwd` ở trên. Egress `open` ⇒ restrict tắt.
  `vm(profile)` tự suy `restrict` và `sudo` từ hồ sơ.

### "Tật" của khách (cố ý, không phải lỗi của lab)

- `hospital`: IT khách đặt `http_proxy`/`https_proxy` trong `/etc/environment`, ngoài ra không cấu hình gì thêm
  (CA của proxy chưa được trust, Docker daemon và apt không được cấu hình proxy). Docker từ gói `docker.io` của Ubuntu
  20.04, **không** có plugin `docker compose`; muốn cài qua apt thì phải đi qua proxy trên.
- `lawfirm-staging`: registry nội bộ chạy HTTP thường ở `10.0.2.101:5000`; Docker trong VM chưa khai báo registry này
  trong `insecure-registries`. Docker cài từ gói `docker.io` của Ubuntu, **không** có plugin `docker compose` (khác
  `lab-open`), mà máy không ra internet: bundle offline phải tự mang binary compose v2 độc lập.

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
| `FDE_PC_SSH` | (Phase 2) SSH tới PC có GPU cho bài cần GPU; chưa đặt thì các bài đó skip |
