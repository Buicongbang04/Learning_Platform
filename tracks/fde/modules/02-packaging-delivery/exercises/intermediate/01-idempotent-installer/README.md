---
title: Installer chạy lại bao nhiêu lần cũng được
level: intermediate
services: []
files:
  - path: starter/install.sh
    note: 6 TODO, bash, chạy bằng root trong VM
  - path: beacon/beacon.py
    note: Dịch vụ mẫu (không sửa)
  - path: beacon/make_bundle.py
    note: Dựng bundle beacon ngay trong VM (không sửa)
  - path: tests/test_installer.py
    note: Không sửa
run:
  - nice -n 15 uv run python -m fdekit prepare lab-open
  - uv run pytest tracks/fde/modules/02-packaging-delivery/exercises/intermediate/01-idempotent-installer -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Ở khách, installer của bạn sẽ bị chạy lại: vì mạng SSH rớt giữa chừng, vì IT "chạy lại cho chắc", vì đợt nâng cấp sau
dùng đúng script đó. Installer tốt chạy lần hai **không đổi gì**, không ghi đè thứ khách đã sửa, từ chối bundle hỏng
trước khi đụng vào bản đang chạy, và tự quay về bản cũ khi bản mới không lên.

## Đề bài

`beacon` là một dịch vụ HTTP nhỏ (Python stdlib) có một tệp "model". Bundle `beacon-<version>.tar` chứa thư mục
`beacon-<version>/` gồm:

| Tệp | Nội dung |
| --- | --- |
| `manifest.json` (đầu tar) | `{"name": "beacon", "version": "X.Y.Z", "files": {đường dẫn: {"sha256", "size"}}}`, như bài basic 01 |
| `app/beacon.py`, `app/VERSION` | Dịch vụ; `GET /healthz` trả 503 khi đang kiểm model, 200 + JSON `version`, `greeting`, `weights_sha256` khi sẵn sàng |
| `config/beacon.env` | Cấu hình mặc định: `BEACON_PORT=8088`, `BEACON_GREETING=…` |
| `systemd/beacon.service` | Unit chạy `/usr/bin/python3 /opt/beacon/current/app/beacon.py` bằng user `beacon`, đọc `/etc/beacon/beacon.env` |
| `models/weights.bin` | Model giả |

Viết `starter/install.sh`. Test chạy `sudo bash /home/fde/install.sh /home/fde/beacon-<version>.tar` trên `lab-open`,
mỗi lần ≤180 s. Installer phải:

1. Chỉ cài bundle khớp manifest (đủ tệp, không thừa, đúng sha256), kiểm **trước** khi đụng vào bản đang chạy; bundle
   không đạt ⇒ thoát khác `0` và không để lại gì trong `/opt/beacon`, `/etc/beacon`, unit.
2. Đặt mã ở `/opt/beacon/current/` (unit trỏ vào đó; bố cục bên dưới tuỳ bạn), tạo user hệ thống `beacon`, cài unit,
   `enable` dịch vụ, tạo `/etc/beacon/beacon.env` từ cấu hình mặc định **chỉ khi chưa có**.
3. Khởi động bản mới và chờ `/healthz` báo đúng version (tối đa 60 s). Không lên ⇒ quay về bản đang chạy trước đó, thoát
   khác `0`.
4. Chạy lại đúng bundle đang chạy ⇒ thoát `0` và **không đổi gì**: không tệp/symlink nào trong `/opt/beacon`,
   `/etc/beacon`, `/etc/systemd/system/beacon.service` bị tạo, xoá, ghi lại (inode, kích thước, mtime giữ nguyên),
   dịch vụ không bị restart.
5. Mỗi lần chạy ghi thêm vào `/var/log/beacon/install.log`; dòng **cuối** của lần chạy có dạng
   `<thời điểm ISO-8601> <version> <kết quả>`, với kết quả là `installed`, `unchanged`, `failed` hoặc `rolled-back`.

Test dựng bundle ngay trong VM bằng `beacon/make_bundle.py` (bundle sai sha256 là `--bad-sha`, bản không khởi động được
là `--broken-app`). Bạn chạy thử tay được: boot VM như trong test, `python3 make_bundle.py 1.0.0 4 /home/fde/beacon-1.0.0.tar`.

## Tiêu chí đạt

`test_install_rerun_upgrade_and_rollback` chạy theo thứ tự trên một VM:

| Bước | Cần thấy |
| --- | --- |
| Cài 1.0.0 | Thoát `0`, log `1.0.0 installed`, `/healthz` (cổng 8088 forward ra host) trả `1.0.0` và lời chào mặc định, dịch vụ `enabled` |
| Cài lại 1.0.0 | Thoát `0`, log `1.0.0 unchanged`, trạng thái như mục 4 không đổi |
| Khách sửa `BEACON_GREETING` rồi restart; cài lại 1.0.0 | Thoát `0`, `unchanged`, không đổi gì, lời chào của khách còn nguyên |
| Cài 1.1.0, rồi cài lại 1.1.0 | `installed` rồi `unchanged`; `/healthz` trả `1.1.0` với lời chào của khách |
| Cài 1.2.0 sai sha256 | Thoát khác `0`, log `1.2.0 failed`, trạng thái không đổi, vẫn phục vụ 1.1.0 |
| Cài 1.3.0 không khởi động được | Thoát khác `0`, log `1.3.0 rolled-back`, `/healthz` lại trả `1.1.0`, dịch vụ `active` |

## Gợi ý

### Gợi ý 1

"Không đổi gì" khó hơn "cài lại cho chắc": `install -m`, `cp`, `ln -sf`, `systemctl daemon-reload` + `restart` đều làm đổi
mtime, inode hay PID. So trước (`cmp -s`, so manifest đã cài với manifest trong bundle) rồi mới ghi.

### Gợi ý 2

Đổi bản bằng một symlink `current` trỏ vào thư mục của từng release: quay về bản cũ chỉ là trỏ lại. `ln -sfn` + `mv -T`
đổi symlink theo cách không có thời điểm nào nó trỏ vào hư không.

### Gợi ý 3

`tar -xOf bundle.tar --wildcards --occurrence=1 '*/manifest.json'` đọc manifest mà không giải nén cả bundle.
