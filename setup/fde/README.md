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

## Chuẩn bị golden image

Mỗi hồ sơ khách có một golden image (đã cài sẵn runtime và "tật" của khách) ở `data/raw/fde-images/golden/<hồ sơ>.qcow2`.
Bài nào cần hồ sơ chưa có golden thì test skip kèm đúng lệnh cần chạy, ví dụ:

```bash
nice -n 15 uv run python -m fdekit prepare lab-open
```

Lệnh chỉ cần chạy một lần mỗi hồ sơ (thời gian dựng không tính vào ngân sách 300 s của bài).

## Một VM của bài tập trông thế nào

- Overlay qcow2 riêng trên golden: bài nào cũng bắt đầu từ trạng thái sạch, golden không bao giờ bị ghi.
- Seed cloud-init chỉ chứa **khoá công khai** SSH sinh riêng cho lần chạy; user trong VM là `fde`.
- Mạng user-mode của QEMU, chỉ bind `127.0.0.1` phía host; SSH và các cổng `forwards` là cổng trống ngẫu nhiên.
- Khi `restrict` tắt (mặc định, hồ sơ egress `open`), VM ra internet được và địa chỉ `10.0.2.2` trong VM trỏ tới
  loopback của host: mọi dịch vụ đang nghe `127.0.0.1` trên máy (Postgres, MLflow…) đều với tới được từ VM. Hồ sơ
  egress `none`/`proxy` bật `restrict=on`: VM chỉ còn các `hostfwd`/`guestfwd` được khai báo.
- Tên tiến trình `fde-ex-<run id 8 ký tự>`, thư mục lab `.fde-lab/fde-ex-<run id>/` (overlay, seed, key, log console).
- QEMU chết theo tiến trình pytest (kể cả khi bị `SIGKILL` do app cắt test sau 300 s, và kể cả VM mở từ luồng phụ):
  một tiến trình canh nhỏ giữ đầu đọc của pipe "lifeline", thấy EOF thì giết QEMU và xoá thư mục lab.

## Dọn dẹp

```bash
uv run python -m fdekit leftovers          # liệt kê tiến trình QEMU, thư mục .fde-lab, container fde-ex-* còn sót
uv run python -m fdekit clean <run_id>     # dọn đúng một run id (8 ký tự hex)
```

`leftovers` không có `run_id` chỉ để xem; không có lệnh xoá hàng loạt vì nhiều phiên có thể chạy song song trên cùng máy.

## Biến trong `setup/.env`

| Biến | Dùng cho |
| --- | --- |
| `FDE_CAPSTONE_DIR` | Đường dẫn repo capstone **của bạn** (repo git riêng, ngoài repo học). Chưa đặt thì test capstone skip |
| `FDE_PC_SSH` | (Phase 2) SSH tới PC có GPU cho bài cần GPU; chưa đặt thì các bài đó skip |
