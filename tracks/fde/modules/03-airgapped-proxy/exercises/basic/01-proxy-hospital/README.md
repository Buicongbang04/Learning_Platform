---
title: Cấu hình proxy công ty cho shell, apt và Docker
level: basic
services: []
files:
  - path: starter/configure_proxy.sh
    note: 6 TODO, POSIX sh, chạy bằng sudo trên máy hospital
  - path: tests/test_proxy.py
    note: Không sửa
run:
  - nice -n 15 uv run python -m fdekit prepare hospital
  - uv run pytest tracks/fde/modules/03-airgapped-proxy/exercises/basic/01-proxy-hospital -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Máy của bệnh viện chỉ ra internet qua proxy công ty, và proxy đó **soi TLS** (mở gói HTTPS, ký lại bằng CA nội bộ).
IT đã đặt proxy "cho máy" theo cách họ quen, nhưng mỗi chương trình đọc cấu hình mạng ở một chỗ khác nhau. Bài này
viết một script đưa máy về trạng thái mà shell, `apt` và Docker đều đi ra ngoài được, đúng cách, chạy lại bao nhiêu lần
cũng được, và **không** tắt kiểm chứng chỉ ở đâu cả.

## Đề bài

IT bệnh viện gửi bạn:

> Proxy: `http://10.0.2.100:3128`, không cần đăng nhập. Proxy có kiểm tra SSL, chứng chỉ gốc của bệnh viện đính kèm
> (`proxy-ca.pem`, fingerprint đọc qua điện thoại). Tên miền nội bộ `*.benhvien.internal` và chính máy này phải đi thẳng,
> không qua proxy.

Viết `starter/configure_proxy.sh <proxy url> <ca.pem>` (POSIX sh). Test dựng máy `hospital` (`fdekit.customer_site`,
proxy mitmproxy thật, CA mới mỗi lần chạy), chép CA vào `/home/fde/proxy-ca.pem`, rồi chạy **hai lần liên tiếp**:

```bash
sudo sh /home/fde/configure_proxy.sh http://10.0.2.100:3128 /home/fde/proxy-ca.pem
```

Sau đó test kiểm bằng lệnh thật trong VM, mỗi lệnh trong một phiên SSH **mới** (như một người đăng nhập vào sau khi bạn
cấu hình xong). Proxy của lab chạy trên máy bạn, nên máy bạn phải ra được internet; không có mạng thì test skip.

Bạn tự boot máy để điều tra: `with fdekit.customer_site("hospital") as s:` rồi `s.vm.ssh(...)`, CA ở `s.proxy_ca`.

## Tiêu chí đạt

`test_proxy_for_shell_apt_docker`:

| Kiểm | Cách test làm |
| --- | --- |
| Script chạy được và chạy lại được | Hai lần chạy đều thoát `0`, mỗi lần ≤120 s |
| Không nhân đôi cấu hình | `/etc/environment` có đúng **một** dòng cho mỗi khoá `http_proxy`, `https_proxy`, `no_proxy`, `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY` |
| Biến môi trường của shell đăng nhập mới | Cả chữ thường lẫn chữ hoa: proxy = `http://10.0.2.100:3128`; `no_proxy` và `NO_PROXY` (tách theo dấu phẩy) có `localhost`, `127.0.0.1`, `.benhvien.internal`; không có `PYTHONHTTPSVERIFY` |
| HTTPS qua proxy, chứng chỉ được kiểm | `curl -q https://pypi.org/simple/pip/` (bỏ qua `~/.curlrc`) và `urllib` của `python3` hệ thống trả 200 |
| Dịch vụ trên chính máy này đi thẳng | Một server HTTP nghe `10.0.2.15:18099`; `curl -q http://10.0.2.15:18099/...` trong shell đăng nhập mới trả 200 |
| apt | `sudo apt-get update` thoát `0`, không có dòng nào bắt đầu bằng `Err:`, `W:`, `E:` |
| Docker | User `fde` chạy được `docker pull` + `docker run` của `hello-world@sha256:c567b231…` (digest đầy đủ trong test) |
| Không tắt TLS của registry | `docker info` không có registry nào bị đánh dấu insecure ngoài mặc định `127.0.0.0/8`, `::1/128` |

## Gợi ý

### Gợi ý 1

Mỗi dòng trong bảng trên là một chương trình khác nhau đọc cấu hình mạng theo cách riêng. Với từng cái, hỏi: nó chạy
dưới tiến trình nào (shell của bạn, `sudo`, một service systemd khởi động lúc boot), và tiến trình đó lấy biến môi
trường từ đâu.

### Gợi ý 2

Proxy soi TLS thì mọi thứ đi HTTPS qua nó thấy chứng chỉ do CA bệnh viện ký. "Tin CA này" phải làm ở nơi các chương
trình trên máy thật sự đọc danh sách CA, và chương trình nào đã đọc danh sách đó lúc khởi động thì không tự đọc lại.

### Gợi ý 3

`no_proxy` không có một chuẩn chung: mỗi công cụ hiểu dấu `.` đầu tên miền, dải CIDR, cổng theo cách khác nhau, và
công cụ cũ trên Ubuntu 20.04 hiểu ít hơn công cụ mới. Thử đúng công cụ, đúng phiên bản có trên máy khách.
