# Lời giải: cấu hình proxy công ty cho shell, apt và Docker

`configure_proxy.sh` ghi **năm chỗ**, vì năm nhóm chương trình đọc cấu hình mạng ở năm nơi khác nhau:

| Chỗ ghi | Ai đọc | Vì sao `/etc/environment` có sẵn của IT không đủ |
| --- | --- | --- |
| `/usr/local/share/ca-certificates/benhvien-proxy-ca.crt` + `update-ca-certificates` | OpenSSL (curl, `python3` hệ thống, apt qua HTTPS), Go (dockerd) đều đọc `/etc/ssl/certs/ca-certificates.crt` | Trước đó CA của proxy không có trong bundle hệ thống ⇒ `curl: (60) SSL certificate problem: unable to get local issuer certificate` |
| `/etc/environment`: đủ 6 khoá, cả chữ hoa | `pam_env` khi đăng nhập (SSH, console) | Nhiều công cụ chỉ đọc một dạng: curl bỏ qua `HTTP_PROXY` chữ hoa (chống "httpoxy") nhưng đọc `HTTPS_PROXY`; Go đọc cả hai; một số SDK chỉ đọc chữ hoa. Ghi cả hai, cùng giá trị |
| `/etc/apt/apt.conf.d/95benhvien-proxy` | apt | `sudo` mặc định `env_reset`: biến proxy của bạn **không** đi theo sang `sudo apt-get` |
| `/etc/systemd/system/docker.service.d/http-proxy.conf` | dockerd (service systemd) | Service khởi động bởi systemd lúc boot, không qua PAM, không đọc `/etc/environment`. `docker pull` là daemon kéo, không phải CLI của bạn |
| restart `docker` | dockerd | Daemon đọc biến môi trường **và** bundle CA lúc khởi động (Go nạp system roots một lần); sửa mà không restart thì như chưa sửa |

Danh sách đi thẳng: `localhost,127.0.0.1,::1,10.0.2.15,.benhvien.internal`. Ba bẫy đã gặp thật:

- `10.0.2.0/24` thay cho `10.0.2.15` **không** chạy với curl 7.68 của Ubuntu 20.04 (CIDR trong `no_proxy` chỉ có từ curl
  7.86); request tới dịch vụ nội bộ đi vòng qua proxy, proxy (ở máy khác) không với tới được ⇒ đo trên `hospital`:
  `no_proxy=10.0.2.0/24` cho `curl: (28) Operation timed out`, `no_proxy=10.0.2.15` cho `200`. Liệt kê IP cụ thể, hoặc
  thêm CIDR **cùng với** IP cho công cụ mới.
- `*.benhvien.internal` không phải cú pháp chung; `.benhvien.internal` (dấu chấm đầu) được curl, Python, Go, Docker hiểu.
- Docker daemon cũng cần `NO_PROXY`: khi khách có registry nội bộ, quên nó là `docker pull` registry nội bộ đi qua proxy.

Idempotent: mỗi tệp dựng sẵn vào thư mục tạm, so `cmp -s` với tệp đang có, chỉ ghi khi khác; Docker chỉ restart khi
drop-in hoặc CA đổi. `/etc/environment` được viết lại bằng cách bỏ mọi dòng của 6 khoá rồi thêm đúng 6 dòng, giữ nguyên
`PATH` và các dòng khác của IT.

Restart Docker là downtime: không có `live-restore` thì **mọi** container trên máy dừng rồi chạy lại. Script in cảnh báo
khi `docker info` báo `LiveRestoreEnabled` khác `true`; trên máy production, chạy nó trong cửa sổ bảo trì đã thoả thuận.

Kiểm đầu vào: CA phải là PEM đọc được bằng `openssl x509`; script in subject + fingerprint SHA-256 để bạn **đọc lại với IT**
qua kênh khác (một tệp `.pem` gửi qua email có thể bị thay). Proxy chứa `user:pass@` thì từ chối: mật khẩu cá nhân nằm
trong `/etc/environment` thì mọi user và mọi log `env` đều thấy; xin IT tài khoản dịch vụ hoặc cho máy chủ đi proxy
không xác thực theo IP.

## Không làm

- `curl -k`, `--insecure`, `PYTHONHTTPSVERIFY=0`, `Acquire::https::Verify-Peer "false"`, `insecure-registries` cho Docker
  Hub: chạy được ngay, nhưng từ đó máy không còn phân biệt được proxy của bệnh viện với kẻ đứng giữa bất kỳ. Test kiểm
  `PYTHONHTTPSVERIFY` và insecure registry; phần còn lại là kỷ luật nghề.
- Sửa `/etc/docker/daemon.json` khoá `proxies` cũng được (Docker ≥ 23), nhưng phải gộp với nội dung có sẵn (xem bài
  basic 02); drop-in systemd tách biệt, không đụng tệp IT có thể đã chỉnh.
- Đặt proxy trong `~/.bashrc` của `fde`: chỉ shell tương tác của một user thấy, `cron`, service, `sudo` đều không.
