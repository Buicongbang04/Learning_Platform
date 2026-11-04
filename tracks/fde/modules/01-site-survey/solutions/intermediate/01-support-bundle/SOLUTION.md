# Lời giải: support bundle không ra ở ngân hàng

Lời giải ở `support_bundle.sh` cạnh tệp này. Chạy:

```bash
SOLUTION=1 uv run pytest tracks/fde/modules/01-site-survey/exercises/intermediate/01-support-bundle -q
```

## Nguyên nhân: sáu chỗ hỏng, khách chỉ thấy chỗ đầu

Script giả định "máy khách là Ubuntu có sudo". `set -eu` làm nó dừng ở lỗi đầu tiên, nên mỗi lần sửa một chỗ rồi gửi lại
khách sẽ nhận một lỗi mới. Đo trên VM `bank` bằng cách sửa lần lượt từng chỗ:

| Vòng | Dòng | Khách thấy | Nguyên nhân do hồ sơ `bank` |
| --- | --- | --- | --- |
| 1 | `lsb_release -is` | `lsb_release: command not found` (mã 127) | Rocky 8 bản cài tối thiểu/cloud image không có gói `redhat-lsb-core` |
| 2 | `sudo -n dmesg` | `sudo: a password is required` | User `fde` không có sudo. Trên Ubuntu 22.04 `kernel.dmesg_restrict=1` nên tác giả thêm `sudo`; trên Rocky 8 `dmesg` đọc được không cần root |
| 3 | `sudo -n aa-status` | `sudo: a password is required` | Như trên; Rocky dùng SELinux, không có AppArmor |
| 4 | `resolvectl dns` | `Failed to get global data: Unit dbus-org.freedesktop.resolve1.service not found.` | Lệnh có (systemd 239) nhưng `systemd-resolved` không chạy; Rocky để NetworkManager ghi thẳng `/etc/resolv.conf` |
| 5 | `docker info > runtime.txt 2>&1` | **Không in gì**, mã 127 | Không có Docker (runtime là Podman rootless); stderr đã bị chuyển vào tệp nên khách chỉ thấy script im lặng dừng |
| 6 | `python3 - <<EOF` | `python3: command not found` | RHEL/Rocky 8 tối thiểu chỉ có `/usr/libexec/platform-python` cho công cụ hệ thống, không có `python3` cho người dùng |

Vòng 5 là vòng tốn kém nhất ở hiện trường: khách báo "chạy không ra gì cả" và không có thông báo lỗi nào để gửi.

## Cách sửa

- **Không để một lệnh dò làm chết cả script**: bỏ `set -e`, gom lệnh vào hàm `collect` ghi output (cả stderr) vào tệp;
  lệnh lỗi thì nối thêm một dòng "lệnh ... lỗi hoặc không có trên máy này". Tệp không bao giờ rỗng, người đọc bundle biết
  vì sao thiếu.
- **OS** đọc `/etc/os-release`.
- **Không sudo**: thử `dmesg` thường; bị chặn thì ghi lý do. Bảo mật đọc `getenforce`/`sestatus` nếu có, không thì
  `aa-enabled`/`aa-status` (không root thì `aa-status` chỉ báo thiếu quyền, vẫn hơn không có gì).
- **DNS**: dùng `resolvectl dns` khi lệnh chạy được, ngược lại đọc `nameserver` trong `/etc/resolv.conf`. Trên Ubuntu
  `/etc/resolv.conf` chỉ có `127.0.0.53` (stub), DNS thật nằm sau `systemd-resolved`.
- **Runtime**: thử Docker daemon (`docker version --format '{{.Server.Version}}'`), rồi Podman
  (`podman version --format '{{.Client.Version}}'`), ghi `docker info`/`podman info` tương ứng.
- **JSON bằng shell** (`printf` + hàm escape), không phụ thuộc `python3`.

## Gửi gì cho khách

Một lần, kèm: bản script mới, sha256 của nó, một câu "đã chạy thử trên Rocky 8.10 không sudo, không mạng", và ghi chú
rằng script chỉ đọc, không cần quyền gì thêm. Không gửi "anh thử chạy với sudo xem sao".

## Lỗi hay gặp khi sửa

- Sửa đúng một dòng khách báo rồi gửi lại: khách nhận lỗi `sudo` ở vòng sau, mất thêm một ngày và thêm một change.
- Thay `lsb_release` bằng `cat /etc/redhat-release`: hết chạy trên Ubuntu.
- Bọc mọi lệnh bằng `|| true` mà không ghi lý do: tệp rỗng, người đọc bundle tưởng máy không có dữ liệu.
- Đọc `/etc/resolv.conf` trên Ubuntu và gửi `127.0.0.53` về như DNS của khách.
