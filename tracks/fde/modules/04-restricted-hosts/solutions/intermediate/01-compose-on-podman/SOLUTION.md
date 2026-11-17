# Lời giải: hiện trường "compose trên Podman của công ty luật"

Lời giải ở `deploy.sh` và `compose.yaml` cạnh tệp này:

```bash
SOLUTION=1 nice -n 15 uv run pytest tracks/fde/modules/04-restricted-hosts/exercises/intermediate/01-compose-on-podman -q -s
```

Đo 2026-11-11 trên máy của repo: 40 s (boot VM ~15 s, mỗi lần triển khai vài giây).

## Đi theo lỗi, từng lớp một

Chạy `deploy.sh` của team trên `lawfirm-hardened` gặp ba lỗi nối tiếp; mỗi lỗi chỉ lộ ra khi lỗi trước đã được sửa.

**1. Không có Docker.** `deploy.sh: line 7: docker: command not found` (mã 127). Image nạp bằng `podman load`; nó vào
storage của **user** `fde` (`~/.local/share/containers/storage`), user khác (kể cả root) không thấy.

**2. Compose không tìm thấy API.** Binary `docker-compose` tìm Docker Engine API ở `/var/run/docker.sock`:

```
failed to connect to the docker API at unix:///var/run/docker.sock; check if the path is correct and if the daemon is running: dial unix /var/run/docker.sock: connect: no such file or directory
```

Podman có API tương thích, phục vụ bởi unit **user** `podman.socket` (socket activation, chạy `podman system service`
khi có kết nối). Trên `lawfirm-hardened` IT đã bật linger cho `fde` nhưng **chưa** bật `podman.socket`
(`systemctl --user is-enabled podman.socket` ra `disabled`). Sửa: `systemctl --user enable --now podman.socket`, rồi
chạy compose với `DOCKER_HOST=unix://$XDG_RUNTIME_DIR/podman/podman.sock`. Không cần root: đây là unit của user, socket
nằm trong `/run/user/1000/podman/`. IT đã thử thành công phần này bằng tay (chạy `podman system service` trong phiên của
họ), nên ticket của họ bắt đầu từ lỗi thứ ba.

**3. SELinux chặn bind mount.** Compose chạy, container lên rồi thoát mã 1 sau chưa tới một giây:

```
notice-notice-1  Exited (1) 1 second ago
cat: can't open '/etc/notice/notice.conf': Permission denied
```

Quyền tệp cho phép (owner `fde`, root trong container rootless chính là `fde`). Nhưng nhãn khác nhau:

```
$ ls -Z ~/notice-bundle/config
unconfined_u:object_r:user_home_t:s0 notice.conf
$ podman inspect notice-notice-1 --format '{{.ProcessLabel}}'
system_u:system_r:container_t:s0:c665,c858
```

Policy không cho `container_t` đọc `user_home_t`. User `fde` không đọc được `/var/log/audit/audit.log`
(`ausearch -m avc` báo `Error opening config file (Permission denied)`, `journalctl` chỉ thấy journal của user), nên không
có AVC để nhìn: chẩn đoán bằng cách so nhãn như trên. Sửa ở đúng chỗ: thêm `Z` vào bind mount
(`./config:/etc/notice:ro,Z`). Podman đổi nhãn thư mục `config/` sang `container_file_t` với đúng cặp category MCS của
container này (`system_u:object_r:container_file_t:s0:c665,c858`), và container đọc được. User đổi nhãn được vì đó là tệp
của chính mình; không cần IT, không đổi policy.

## Các quyết định trong lời giải

- **`:Z` (riêng) thay vì `:z` (dùng chung):** thư mục cấu hình chỉ container này đọc. `:z` cũng đạt test; dùng khi nhiều
  container cùng đọc một thư mục. Không bao giờ đặt `:Z` lên `$HOME`, `/etc` hay thư mục của dịch vụ khác.
- **Không `security_opt: [label=disable]`, không `privileged: true`:** chạy được, nhưng là tắt SELinux cho container, đúng
  thứ IT nói không làm. Test kiểm `ProcessLabel` chứa `container_t` và `Privileged` là false. `chcon -R -t
  container_file_t config` cũng đạt test, nhưng nhãn đó mất khi IT chạy `restorecon` toàn home; `:Z` được Podman áp lại mỗi
  lần tạo container.
- **`deploy.sh` idempotent:** `enable` socket chỉ khi chưa bật, `podman load` lần hai không đổi gì, `up -d
  --force-recreate --pull never` tạo lại container để `start` đọc cấu hình mới (bind mount thấy nội dung mới ngay, nhưng app
  chỉ đọc lúc khởi động), và không bao giờ cố kéo image từ internet.
- **Bền qua đăng xuất:** linger đã bật nên user manager, socket và container (qua `conmon`) sống khi không ai đăng nhập;
  script vẫn kiểm `Linger` và cảnh báo kèm câu nhờ IT nếu máy khác chưa bật.
- `name: notice` trong compose cố định tên project, không phụ thuộc tên thư mục; `-p notice` trên dòng lệnh cũng được.

Ghi chú cho báo cáo: `restart: unless-stopped` dưới Podman rootless **không** làm container tự chạy lại sau khi máy
reboot (không có daemon chạy thường trực). Muốn vậy cần `systemctl --user enable podman-restart.service` hoặc chuyển dịch
vụ sang Quadlet; ghi lại để thống nhất với IT trước lần bảo trì đầu tiên.
