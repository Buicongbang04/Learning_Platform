---
title: Dịch vụ không root trên máy ngân hàng
level: basic
services: []
files:
  - path: starter/install.sh
    note: 5 TODO, POSIX sh, chạy bằng user fde (không sudo) trên máy bank
  - path: starter/heartbeat.service
    note: Unit systemd --user của agent, bạn viết
  - path: heartbeat/heartbeat.sh
    note: Agent heartbeat của sản phẩm (không sửa)
  - path: tests/test_user_service.py
    note: Không sửa
run:
  - nice -n 15 uv run python -m fdekit prepare bank
  - uv run pytest tracks/fde/modules/04-restricted-hosts/exercises/basic/01-user-service -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Ở ngân hàng bạn không có sudo, và xin một service hệ thống mất vài tuần. Một agent nhỏ vẫn phải chạy 24/7: tự khởi động,
đọc lại cấu hình khi restart, và **không chết khi bạn đăng xuất**. Bài này dựng đúng thứ đó bằng `systemd --user`, hoàn
toàn trong `$HOME`.

## Đề bài

Máy `bank`: Rocky Linux 8.10, SELinux enforcing, user `fde` **không** có sudo, không mạng. Agent `heartbeat/heartbeat.sh`
(POSIX sh, không sửa) đọc `~/.config/heartbeat/heartbeat.env` (hai khoá `TOKEN=` và `INTERVAL=` tính bằng giây) rồi cứ mỗi
`INTERVAL` giây ghi một dòng `<epoch> <pid> <token>` vào `~/.local/state/heartbeat/beats.log`; `<pid>` là pid của chính
tiến trình `sh` chạy agent.

Viết hai tệp:

- **`starter/heartbeat.service`**: unit `systemd --user` chạy agent. Tên unit cố định `heartbeat.service`.
- **`starter/install.sh`** (POSIX sh): cài agent và unit cho user đang chạy nó, bật và chạy dịch vụ. Không dùng `sudo`,
  không ghi ngoài `$HOME`.

Test boot `bank` (1024 MB), chép `heartbeat.sh`, `install.sh`, `heartbeat.service` vào `/home/fde/heartbeat-bundle/`,
ghi `heartbeat.env` với `TOKEN` ngẫu nhiên và `INTERVAL=1`, rồi chạy **hai lần** (mỗi lần ≤60 s):

```bash
cd /tmp && sh /home/fde/heartbeat-bundle/install.sh
```

Sau đó test đổi `TOKEN` trong `heartbeat.env`, chạy `systemctl --user restart heartbeat.service`, rồi **không mở phiên SSH
nào trong 25 s** (đăng xuất hoàn toàn) và đăng nhập lại để kiểm. Đo trên máy của repo: cả bài ~41 s. Tự boot máy để điều
tra: `with fdekit.vm("bank", memory_mb=1024) as m:` rồi `m.ssh(...)`, hoặc `ssh` bằng `m.ssh_command()`.

## Tiêu chí đạt

`test_heartbeat_survives_restart_and_logout_on_bank`:

- Hai lần chạy `install.sh` đều thoát `0`.
- `systemctl --user is-active heartbeat.service` là `active`, `is-enabled` là `enabled`; trong 15 s, `beats.log` có dòng
  với pid bằng `MainPID` của unit và đúng `TOKEN` đang cấu hình.
- Sau khi đổi `TOKEN` và `systemctl --user restart`: `MainPID` là tiến trình mới và trong 15 s ghi dòng với `TOKEN` mới.
- Sau 25 s không có phiên SSH nào: unit vẫn `active`, **cùng** `MainPID` như trước khi đăng xuất, và trong khoảng đó
  `beats.log` có dòng của pid này với khoảng cách giữa hai dòng liên tiếp (tính cả đầu và cuối khoảng) không quá 6 s.

## Gợi ý

### Gợi ý 1

Làm tay một lần trên VM trước khi viết script: tạo unit, `enable`, `start`, xem `beats.log`. Rồi đóng mọi phiên SSH, chờ
nửa phút, đăng nhập lại và so `systemctl --user show -p MainPID heartbeat.service` với trước đó.

### Gợi ý 2

User manager (`systemd --user`) không có `multi-user.target`. Unit của user được "kéo lên" bởi target nào khi user manager
khởi động? Và chính user manager được khởi động, dừng lúc nào?

### Gợi ý 3

Unit không đọc `~/.bashrc` hay `PATH` của bạn. Đường dẫn trong unit nên là tuyệt đối; systemd có specifier cho thư mục
home của user.
