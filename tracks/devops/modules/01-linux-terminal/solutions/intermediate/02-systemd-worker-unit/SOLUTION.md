# Lời giải: systemd unit cho worker và timer backup của Olist Shop

Ba unit đầy đủ ở cạnh tệp này. Cả hai service đạt exposure 1.3 (OK) với `systemd-analyze security --offline=yes`
trên systemd 255.

## Cách làm

1. **Đổi user trước, rồi mới hardening.** `User=olist` đã bớt hơn một nửa rủi ro: root trong service bị chiếm quyền là
   root của cả máy. User tạo một lần bằng `useradd --system --home-dir /nonexistent --shell /usr/sbin/nologin olist`
   (trong Ansible, module 09). `DynamicUser=yes` là lựa chọn khác: systemd tự cấp UID tạm cho mỗi lần chạy, rất chặt,
   nhưng tệp backup do UID tạm sở hữu khó chia sẻ với service khác, nên ở đây dùng user cố định.
2. **Bí mật ra `EnvironmentFile=`.** Unit file đọc được bởi mọi user (`systemctl cat`), nằm trong repo cấu hình, và
   `Environment=` hiện trong `systemctl show`. Tệp `/etc/olist-shop/worker.env` để `0640 root:olist`. Mạnh hơn nữa là
   `LoadCredential=` (systemd 247+) hoặc Vault/SOPS (module 12).
3. **Restart có giới hạn.** `Restart=on-failure` (không restart khi worker tự thoát `0`), `RestartSec=5s` để không đập
   liên tục vào Redis đang hỏng. `StartLimitIntervalSec=300` + `StartLimitBurst=5`: quá 5 lần trong 5 phút thì unit
   chuyển sang `failed` và dừng thử, để alert (`OnFailure=` gọi một unit gửi thông báo) thay vì quay vòng im lặng
   cả đêm. `Restart=always` không giới hạn che mất lỗi cấu hình và đốt CPU.
4. **Dừng có thời hạn.** `TimeoutStopSec=30s` khớp với thời gian worker cần để trả job đang xử lý; mặc định 90 giây
   làm mỗi lần deploy chậm thêm 90 giây khi worker không xử lý `SIGTERM`.
5. **Sandbox theo nhóm:**

   | Nhóm | Tuỳ chọn | Chặn gì |
   | --- | --- | --- |
   | Hệ thống tệp | `ProtectSystem=strict`, `ProtectHome=yes`, `PrivateTmp=yes`, `StateDirectory=`, `UMask=0027` | Sửa binary, cấu hình, đọc SSH key trong `/home`, tấn công qua `/tmp` dùng chung |
   | Quyền | `NoNewPrivileges=yes`, `CapabilityBoundingSet=`, `AmbientCapabilities=`, `RestrictSUIDSGID=yes` | Leo thang qua setuid binary, giữ capability |
   | Kernel | `ProtectKernelTunables/Modules/Logs=yes`, `ProtectControlGroups=yes`, `ProtectClock=yes`, `ProtectHostname=yes` | Đổi sysctl, nạp module, đọc `dmesg`, đổi giờ |
   | Thiết bị, tiến trình | `PrivateDevices=yes`, `ProtectProc=invisible`, `ProcSubset=pid` | Đọc ổ đĩa thô, nhìn thấy tiến trình khác |
   | Mạng, syscall | `RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX`, `SystemCallFilter=@system-service`, `~@privileged @resources`, `SystemCallArchitectures=native` | Raw socket, netlink, syscall hiếm dùng để khai thác |
   | Tài nguyên | `MemoryMax=512M`, `TasksMax=64`, `LimitNOFILE=8192` | Một worker rò bộ nhớ hoặc fork bomb kéo sập cả VM |

6. **Backup là `oneshot` không có `[Install]`.** `Nice=15` và `IOSchedulingClass=idle` để `pg_dump` không giành CPU
   và đĩa với API. `UMask=0077` vì bản backup chứa toàn bộ dữ liệu khách hàng. `TimeoutStartSec=1h` thay cho mặc định
   vô hạn của `oneshot`: backup treo thì unit phải fail để có alert.
7. **Timer thay cron.** `Persistent=true` ghi lần chạy cuối vào đĩa; máy tắt lúc 02:30 thì timer chạy bù ngay khi máy
   lên. `RandomizedDelaySec=15min` rải lịch khi có nhiều máy. `AccuracySec=1min` (mặc định cũng là 1 phút) cho
   systemd gộp các lần đánh thức để tiết kiệm điện.

## Đánh đổi của hardening

- `MemoryDenyWriteExecute=yes` có ở backup (Bash, `pg_dump`) nhưng **không** ở worker: thư viện Python dùng JIT hoặc
  `ctypes` callback (một số bản `cffi`, `numba`) cần vùng nhớ vừa ghi vừa chạy và sẽ crash với `SIGSYS`.
- `SystemCallFilter=` quá chặt làm service chết bằng `SIGSYS` ở một nhánh code hiếm chạy; thêm
  `SystemCallErrorNumber=EPERM` để syscall bị chặn trả lỗi thay vì giết tiến trình, và chạy thử đủ lâu trên staging.
- `ProtectSystem=strict` bắt khai báo mọi chỗ ghi; quên một thư mục cache là worker lỗi `Read-only file system` lúc
  3 giờ sáng. Liệt kê chúng bằng `strace -f -e trace=openat` hoặc đọc lỗi trong `journalctl -u`.
- Mỗi tuỳ chọn có từ một phiên bản systemd nhất định (`ProtectProc=` từ 247). Trên RHEL 8 (systemd 239), tuỳ chọn
  mới bị bỏ qua kèm cảnh báo, nên `verify` trên đúng phiên bản đích là một bước của CI.

## Vận hành

```bash
sudo install -m 0644 olist-worker.service olist-backup.service olist-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now olist-worker.service olist-backup.timer
systemctl list-timers olist-backup.timer
journalctl -u olist-worker -f
systemctl status olist-worker
```

Sửa unit gốc của package thì không sửa tệp trong `/usr/lib/systemd/system` mà dùng drop-in:
`systemctl edit olist-worker` tạo `/etc/systemd/system/olist-worker.service.d/override.conf`, sống sót qua lần nâng
cấp package.
