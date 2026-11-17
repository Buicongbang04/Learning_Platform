---
title: "Support bundle khách gửi được mà không lộ gì"
level: basic
services: []
files:
  - path: starter/support_bundle.sh
    note: Bản đồng nghiệp viết vội; bạn viết lại
  - path: tests/test_support_bundle.py
    note: Không sửa
run:
  - nice -n 15 uv run python -m fdekit prepare lab-open
  - uv run pytest tracks/fde/modules/08-field-troubleshooting/exercises/basic/01-support-bundle -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Ở nhà máy của khách, `docbridge` (connector công ty bạn viết, đồng bộ hồ sơ từ ERP sang quillo) chạy dưới dạng service
systemd, kèm một container cache. Mỗi khi có sự cố, IT khách phải gửi bạn tình trạng máy, và lần trước họ gửi nguyên
thư mục `/etc` cùng log 2 GB qua email. Bạn viết script support bundle để IT khách chạy bằng tài khoản vận hành (không
root): đủ thông tin để bạn chẩn đoán mà không phải hỏi lại, nhỏ, và không mang theo bất kỳ secret hay dữ liệu nghiệp vụ
nào, vì bundle sẽ nằm trong hệ thống ticket của hai công ty nhiều năm.

## Đề bài

Bài này dạy cách che secret mà bạn **không biết trước** giá trị. Đừng mở công cụ support bundle của quillo
(`exercises/intermediate/01-field-incident/tools/quillo-support.sh`) để tham khảo: nó là công cụ của nhà cung cấp, chỉ
che đúng hai secret mà quillo tự biết, nên không giải được bài này và làm hỏng việc luyện tập.

Viết `starter/support_bundle.sh` (POSIX `sh`, không bash; được dùng công cụ có sẵn trên Ubuntu 22.04). Cách chạy:
`sh support_bundle.sh <tệp ra .tar.gz>`, bằng user `support`: không sudo, thuộc nhóm `adm`, `systemd-journal`,
`docbridge` và (thường là) `docker`.

Máy khách (`lab-open`, test dựng mới mỗi lần):

| Thành phần | Ở đâu |
| --- | --- |
| Service `docbridge.service` (systemd, user `docbridge`) | nghe một cổng TCP trên `127.0.0.1` (cổng ghi trong `listen_port=` của tệp cấu hình) |
| Tệp cấu hình | `/etc/docbridge/docbridge.conf` (dạng `khoá=giá trị`, dòng `#` là chú thích) |
| Chứng chỉ client | `/etc/docbridge/tls/` |
| Log ứng dụng | `/var/log/docbridge/docbridge.log` (lớn, chỉ ghi nối) |
| Dữ liệu nghiệp vụ | `/var/lib/docbridge/data/` |
| Container cache | tên `docbridge-cache` (Docker) |

Bundle là một `.tar.gz` gồm **một** thư mục gốc (tên tuỳ bạn), bên dưới có ít nhất các tệp sau (đường dẫn tính từ thư
mục gốc):

| Tệp | Nội dung |
| --- | --- |
| `system/os-release` | nguyên nội dung `/etc/os-release` |
| `system/uname.txt` | `uname -a` |
| `system/df.txt` | `df -h` |
| `system/memory.txt` | `free -m` |
| `system/uptime.txt` | `uptime` |
| `network/listen.txt` | socket TCP đang nghe (`ss -ltn`) |
| `network/ip.txt` | `ip addr` |
| `docbridge/status.txt` | `systemctl status` của `docbridge` |
| `docbridge/journal.txt` | các dòng journal mới nhất của unit `docbridge` (ít nhất từ lần khởi động gần nhất) |
| `docbridge/docbridge.conf` | tệp cấu hình đã che secret |
| `docbridge/docbridge.log` | phần **cuối** của log ứng dụng đã che secret: ≥ 1000 dòng cuối, ≤ 2 MB, kết thúc bằng dòng cuối hiện tại của log |
| `docker/ps.txt` | `docker ps -a` |
| `docker/docbridge-cache.log` | log gần nhất của container (`docker logs`) |
| `docker/docbridge-cache.json` | `docker inspect` của container, vẫn là JSON hợp lệ sau khi che secret |
| `errors.txt` | mỗi lệnh thu thập thất bại một dòng (lệnh nào, mã thoát/lý do); không có lỗi thì để rỗng |

Quy tắc:

1. **Không lộ secret.** Không đoạn nào dài từ 10 ký tự liên tiếp của bất kỳ secret nào xuất hiện trong bất kỳ tệp nào của
   bundle. Secret là: giá trị của khoá có tên chứa `password`, `secret` hay `token` (không phân biệt hoa thường) trong
   tệp cấu hình, biến môi trường của service và container; phần mật khẩu trong URL dạng `scheme://user:mật-khẩu@host`;
   credential sau `Authorization: Bearer`/`Basic`; và nội dung của private key.
2. **Giữ thông tin chẩn đoán.** Che giá trị, **không** xoá dòng hay biến: dòng cấu hình không chứa secret giữ nguyên;
   dòng có khoá nhạy cảm vẫn còn tên khoá; URL vẫn còn user, host, cổng, đường dẫn; dòng log có `Authorization` vẫn còn;
   `Config.Env` trong `docker inspect` vẫn còn đủ tên biến, biến không nhạy cảm giữ nguyên giá trị.
3. **Không thu dữ liệu nghiệp vụ, không private key** (không chuỗi `PRIVATE KEY` nào trong bundle), không archive lồng
   bên trong (chỉ tệp văn bản thường).
4. **Không cần root, không để lại gì.** Chạy được bằng `support` không sudo. Ngoài tệp bundle, script không để lại tệp
   hay thư mục nào của `support` trong `/tmp`, `/var/tmp`, `/dev/shm`, `$HOME`; thư mục ra chỉ có đúng tệp bundle.
5. **Lệnh lỗi không làm hỏng bundle.** Khi `support` không vào được Docker, script vẫn thoát `0`, vẫn có mọi tệp không
   thuộc `docker/`, và `errors.txt` có dòng nhắc tới docker.
6. Thoát `0`, chạy ≤ 60 s, bundle ≤ 5 MB.

Test dựng máy rồi chạy script **hai lượt**, mỗi lượt gieo secret ngẫu nhiên mới vào mọi chỗ ở quy tắc 1 (cấu hình, môi
trường của unit, dòng journal, log ứng dụng ở giữa và ở cuối, header `Authorization: Bearer` và `Basic`, biến môi trường
và log của container, private key, một tệp trong thư mục dữ liệu), đổi cổng, nội dung log và các giá trị khác; lượt 2
rút `support` khỏi nhóm `docker` và kiểm bundle không chứa secret của **cả hai** lượt. Cả bài
~30 s trên máy của repo.

## Tiêu chí đạt

`test_support_bundle_no_planted_secret`, ở cả hai lượt:

- Script thoát `0` trong 60 s; thư mục ra chỉ có bundle; không tệp nào của `support` sót lại (quy tắc 4); bundle ≤ 5 MB,
  đọc được bằng `tar -xzf`, một thư mục gốc, chỉ tệp thường và thư mục.
- Không secret nào lộ (quy tắc 1, so từng đoạn 10 ký tự), không byte NUL, không archive lồng, không `PRIVATE KEY`, không
  nội dung của thư mục dữ liệu.
- Mọi tệp bắt buộc có mặt và đúng với máy lúc đó: `os-release` khớp từng byte, `uname.txt` có phiên bản kernel, `df.txt`
  có dòng của `/`, `memory.txt` là output `free`, `uptime.txt` có `load average`, `listen.txt` có cổng của docbridge,
  `ip.txt` có địa chỉ của máy, `status.txt` là trạng thái đang chạy của `docbridge.service`, `journal.txt` có dòng
  journal mới nhất của unit và giữ dòng có URL kết nối ERP, `docbridge.conf`/`docbridge.log` đúng quy tắc 2 và giới hạn ở
  bảng trên.
- Lượt 1: `docker/ps.txt` có `docbridge-cache`; `docker/docbridge-cache.log` có log của container (giữ dòng URL
  upstream); `docker/docbridge-cache.json` là JSON hợp lệ có `Config.Env` đúng quy tắc 2. Lượt 2: `errors.txt` nhắc tới
  docker.

## Gợi ý

### Gợi ý 1

Chạy bản của đồng nghiệp trong đầu: mỗi lệnh trong đó in ra cái gì, ai đọc được những thứ đó sau khi bundle rời máy? Có
lệnh nào in ra cấu hình của tiến trình mà bạn không chủ ý thu?

### Gợi ý 2

Thu trước vào một thư mục tạm của riêng bạn, xử lý mọi tệp qua cùng một bộ lọc, rồi mới đóng gói. Một bộ lọc cho mọi
tệp dễ kiểm hơn nhiều bộ lọc riêng cho từng lệnh.

### Gợi ý 3

Tự kiểm như test kiểm: đặt một chuỗi lạ vào mọi chỗ có thể chứa secret trên một máy thử, chạy script, rồi tìm chuỗi đó
(và một phần của nó) trong bundle đã giải nén. Đừng quên output lệnh cũng chứa log.
