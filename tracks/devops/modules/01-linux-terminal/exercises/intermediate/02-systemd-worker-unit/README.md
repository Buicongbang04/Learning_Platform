---
title: Viết systemd unit cho worker và timer backup của Olist Shop
level: intermediate
services: []
files:
  - path: starter/olist-worker.service
    note: Unit cũ chạy bằng root, sửa lại
  - path: starter/olist-backup.service
    note: Viết thêm
  - path: starter/olist-backup.timer
    note: Viết thêm
  - path: tests/test_units.py
    note: Không sửa
run:
  - systemd-analyze security --offline=yes --no-pager tracks/devops/modules/01-linux-terminal/exercises/intermediate/02-systemd-worker-unit/starter/olist-worker.service
  - uv run pytest tracks/devops/modules/01-linux-terminal/exercises/intermediate/02-systemd-worker-unit -q -rs
---

## Mục tiêu

Đưa một tiến trình nền lên production trên VM bằng systemd đúng cách: chạy bằng user riêng, bí mật nằm ngoài unit,
restart có giới hạn, dừng có thời hạn, sandbox đủ chặt để `systemd-analyze security` chấm OK, và thay cron bằng timer
có chạy bù.

## Đề bài

Olist Shop chạy trên VM (trước khi lên container ở module 06). Code ở `/opt/olist-shop`, virtualenv ở
`/opt/olist-shop/.venv`, worker chạy bằng `python -m olist_shop.worker`. Team dev để lại `starter/olist-worker.service`
chạy bằng root, mật khẩu database viết thẳng trong unit, `Restart=always` không giới hạn. Sửa nó và viết thêm hai unit
backup.

**`olist-worker.service`**

| Mục | Yêu cầu test kiểm |
| --- | --- |
| User | `User=olist` |
| Bí mật | Không còn `Environment=` chứa `PASSWORD`, `SECRET`, `TOKEN`, `DSN` hay `..._KEY`; đọc từ `EnvironmentFile=` (ví dụ `/etc/olist-shop/worker.env`, quyền `0640 root:olist`) |
| Khởi động | `After=` và `Wants=network-online.target` trong `[Unit]` |
| Restart | `Restart=on-failure`; `RestartSec=` ít nhất 1 giây; có `StartLimitIntervalSec=` và `StartLimitBurst=` trong `[Unit]` |
| Dừng | `TimeoutStopSec=` trong khoảng (0, 60] giây (worker cần thời gian trả job đang dở, như bài Basic 03) |
| Tài nguyên | Có `MemoryMax=`; có `StateDirectory=` hoặc `ReadWritePaths=` cho chỗ được ghi |
| Lệnh chạy | `ExecStart=` dùng đường dẫn tuyệt đối |
| Cài | `WantedBy=multi-user.target` |

**`olist-backup.service`** chạy `/opt/olist-shop/bin/backup.sh` (script viết ở capstone M01):

| Mục | Yêu cầu test kiểm |
| --- | --- |
| Kiểu | `Type=oneshot`, `User=olist`, có `EnvironmentFile=` |
| Ưu tiên | `Nice=` từ 10 trở lên, `IOSchedulingClass=idle` hoặc `best-effort` |
| Ghi | `ReadWritePaths=` chỉ tới thư mục chứa bản backup (ví dụ `/var/backups/olist-shop`) |
| Restart | Không có, hoặc `no`, hoặc `on-failure` |
| Cài | **Không** có phần `[Install]`: timer kích hoạt service, người vận hành enable timer |

**Cả hai service** có `NoNewPrivileges=yes`, `ProtectSystem=strict`, `ProtectHome=` (`yes`, `read-only` hoặc
`tmpfs`), `PrivateTmp=yes`, `CapabilityBoundingSet=` để rỗng, và điểm exposure của
`systemd-analyze security --offline=yes` **không quá 3.0**. Unit cũ được 9.4 (UNSAFE).

**`olist-backup.timer`**: chạy lúc 02:30 mỗi ngày (`OnCalendar=`), `Persistent=true` để chạy bù khi máy tắt đúng
giờ hẹn, `RandomizedDelaySec=` lớn hơn 0 để nhiều máy không cùng đập vào database một lúc, `Unit=` (nếu có) là
`olist-backup.service`, `WantedBy=timers.target`.

Cuối cùng, `systemd-analyze verify` trên cả ba tệp phải không có lỗi và không có dòng cảnh báo "Unknown key",
"Failed to parse", "ignoring" (systemd bỏ qua dòng sai và vẫn trả exit 0, nên test bắt cả cảnh báo). Máy bạn không có
`/opt/olist-shop`, nên test chép unit sang thư mục tạm và thay chương trình trong mọi dòng `Exec*=` bằng một tệp thực
thi giả trước khi `verify`. Máy không có `systemd-analyze` (macOS, WSL không bật systemd) thì 3 test này skip, các test
còn lại vẫn chạy.

Bài không cần `sudo` và không cài unit vào máy: mọi kiểm tra chạy trên tệp.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/01-linux-terminal/exercises/intermediate/02-systemd-worker-unit -q -rs` pass,
  không skip trên Linux có systemd.
- Giải thích được từng dòng hardening bạn thêm: nó chặn kiểu tấn công nào, và nó có thể làm hỏng gì ở worker.
- Nói được `Restart=always` không giới hạn sai ở đâu, và `StartLimitBurst` cộng `OnFailure=` dùng để làm gì.
- So sánh được timer với cron ở ba điểm: chạy bù, log, phụ thuộc.

## Gợi ý

### Gợi ý 1

Chạy lệnh trong `run:` để xem bảng các mục ✗ kèm điểm trừ. Những mục trừ nhiều nhất thường là `User=` (root),
`CapabilityBoundingSet=`, `PrivateDevices=`, `ProtectKernel*=`, `RestrictAddressFamilies=`, `SystemCallFilter=`.
`man systemd.exec` mô tả từng tuỳ chọn và phiên bản systemd bắt đầu có nó.

### Gợi ý 2

`ProtectSystem=strict` làm cả hệ thống tệp chỉ đọc với service; `StateDirectory=olist-shop` cho bạn
`/var/lib/olist-shop` ghi được, đúng chủ sở hữu, mà không cần tạo tay. Bộ `SystemCallFilter=@system-service` cộng
`SystemCallFilter=~@privileged @resources` là điểm khởi đầu systemd khuyên dùng cho service thường. Thời gian viết
được `5s`, `30s`, `15min`, `1h`. Thử lịch bằng `systemd-analyze calendar '*-*-* 02:30:00'`.
