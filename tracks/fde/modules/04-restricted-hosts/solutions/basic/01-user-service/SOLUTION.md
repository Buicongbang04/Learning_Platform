# Lời giải: dịch vụ không root trên máy ngân hàng

Lời giải ở `install.sh` và `heartbeat.service` cạnh tệp này:

```bash
SOLUTION=1 nice -n 15 uv run pytest tracks/fde/modules/04-restricted-hosts/exercises/basic/01-user-service -q
```

Đo 2026-11-11 trên máy của repo: 41 s (boot ~12 s, chờ đăng xuất 25 s).

## Chỗ hỏng: linger tắt mặc định

Mọi thứ trông đúng khi bạn đang đăng nhập: unit `enabled`, `active`, log chạy đều. Nhưng `bank` (như mọi máy RHEL/Rocky
mặc định) có `Linger=no` cho `fde`: user manager `user@1000.service` chỉ chạy khi có ít nhất một phiên. Phiên SSH cuối
đóng là systemd-logind dừng user manager, và nó gửi `SIGTERM` cho mọi unit của user. Lần đăng nhập sau, user manager khởi
động lại, `default.target` kéo `heartbeat.service` lên với pid mới. Từ phía người dùng: "agent chạy được lúc anh FDE ở
đây, tối về là im". Đo bằng chính lời giải bỏ phần linger: test báo `heartbeat.service chạy lại với pid mới sau khi mọi
phiên SSH đóng` (MainPID 5902 → 11756): agent đã bị dừng khi phiên cuối đóng và chỉ chạy lại khi test đăng nhập lại.

Trên `bank`, polkit cho user tự bật linger cho chính mình qua SSH (`loginctl enable-linger fde` thoát 0, sau đó
`loginctl show-user fde -p Linger` ra `Linger=yes`). Không phải máy nào cũng vậy: action
`org.freedesktop.login1.set-self-linger` có thể bị IT đặt là `auth_admin`. Vì thế lời giải **thử** bật, và nếu không
được thì dừng với đúng một câu nhờ IT (`loginctl enable-linger <user>`), không âm thầm cài một dịch vụ sẽ chết lúc đêm.

## Các quyết định trong lời giải

- **Unit:** `ExecStart=/bin/sh %h/.local/lib/heartbeat/heartbeat.sh` (đường dẫn tuyệt đối qua `%h`, không phụ thuộc
  `PATH`, không chạy từ thư mục bundle mà người khác có thể xoá); `Restart=on-failure`; `WantedBy=default.target` (unit
  của user không có `multi-user.target`).
- **Vì sao không `nohup`/`setsid`:** trên Rocky 8 (`KillUserProcesses=no`) một tiến trình `nohup` cũng sống qua đăng xuất,
  nhưng không ai restart nó khi chết, không có `journalctl --user -u`, không tự chạy khi máy boot lại; test cũng kiểm pid
  ghi log phải là `MainPID` của unit.
- **Idempotent:** so `cmp -s` trước khi chép; chỉ `restart` khi script hoặc unit đổi, còn lại `start` (không làm gì nếu
  đang chạy). Chạy lần hai không đổi pid, không thêm symlink.
- **Kiểm môi trường sớm:** `systemctl --user show-environment` lỗi nghĩa là không có D-Bus của user (vào bằng `su`/`sudo -u`):
  script dừng với hướng dẫn thay vì để `systemctl` báo `Failed to connect to bus` khó hiểu.
- Không có gì cần SELinux ở bài này: unit của user chạy trong domain `unconfined_t` của user, đọc ghi `user_home_t` được.

Các cách khác cũng đạt test: để unit ở `~/.config/systemd/user/` nhưng script ở `~/.local/share/heartbeat/`; dùng
`Type=exec`; bật linger ngay đầu script. Cách **không** đạt: chạy `heartbeat.sh` bằng `nohup`, `screen`, `tmux` hay cron
`@reboot` (MainPID không khớp, hoặc chết khi đăng xuất tuỳ cấu hình), và mọi thứ cần `sudo`.
