---
title: "Hiện trường: installer dừng ở xưởng"
level: basic
services: []
files:
  - path: starter/install.sh
    note: Installer hiện tại của team, chạy tốt trên lab; bạn sửa
  - path: fieldsync/fieldsync.py
    note: Công cụ fieldsync trong bundle (không sửa)
  - path: tests/test_installer_factory.py
    note: Không sửa
run:
  - nice -n 15 uv run python -m fdekit prepare factory
  - uv run pytest tracks/fde/modules/04-restricted-hosts/exercises/basic/02-installer-stops -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Installer qua QA trên máy lab, khách chạy thì dừng. Bạn phải tái hiện trên máy giống của khách, tìm nguyên nhân trong
**cấu hình của máy** chứ không đoán trong code, rồi sửa installer sao cho nó chạy được trong giới hạn khách đặt ra, không
xin khách nới giới hạn đó.

## Đề bài

`fieldsync` đồng bộ bộ tài liệu kỹ thuật (hướng dẫn máy, quy trình QC) xuống máy trạm ở xưởng. Bundle
`fieldsync-1.4.0.tar` có một thư mục `fieldsync-1.4.0/` gồm `bin/fieldsync` (công cụ Python, chính là
`fieldsync/fieldsync.py`, không sửa; gọi sai cú pháp như `fieldsync --help` thì nó in hướng dẫn) và `assets/` (bộ tài liệu,
1100–1400 tệp trong vài thư mục con). Khi cài, installer chạy `fieldsync build-index` để lập `index.json` (sha256 từng
tệp), rồi đặt mọi thứ vào `$HOME/fieldsync/`: `bin/fieldsync`, `assets/`, `index.json`.

`starter/install.sh` là installer team đang dùng, đã qua QA trên `lab-open`. Ticket từ IT nhà máy (máy `factory`,
Debian 12):

> Bên em chạy `sh install.sh fieldsync-1.4.0.tar` bằng user `fde` như hướng dẫn thì dừng ngay, báo `Permission denied`.
> Anh trực ca thử thêm vài cách thì nó chạy được xa hơn một chút rồi lại dừng, lần này là `Too many open files`. Máy ở
> văn phòng bên em cài bình thường. Lưu ý: máy xưởng theo baseline bảo mật của tập đoàn, bên em không đổi cấu hình hệ
> thống (mount, giới hạn tài nguyên, systemd) cho từng phần mềm.

Sửa `starter/install.sh` (giữ cách gọi `sh install.sh <bundle.tar>`, chạy bằng user `fde`, cài vào `$HOME/fieldsync`).
Test dựng hai bundle với bộ tài liệu sinh ngẫu nhiên mỗi lần chạy, boot `factory` (1024 MB), rồi:

1. Chạy `cd /tmp && sh /home/fde/fs/install.sh /home/fde/fs/fieldsync-1.4.0.tar`.
2. Cài đè bằng bundle thứ hai (bộ tài liệu tháng sau, khác hoàn toàn), lần này shell gọi installer đã đặt
   `ulimit -n <số ngẫu nhiên 400–700>` trước (như một phiên của IT có giới hạn thấp hơn).

Mỗi lần chạy installer ≤120 s. Đo trên máy của repo: cả bài ~60 s (máy `factory` có đường truyền chập chờn, SSH chậm).
Tự boot máy để điều tra: `with fdekit.vm("factory", memory_mb=1024) as m:`; so với `fdekit.vm("lab-open", ...)`.

## Tiêu chí đạt

`test_install_on_factory`:

- Hai lần chạy installer đều thoát `0`.
- Sau mỗi lần: `~/fieldsync/index.json` có `count` bằng số tệp và `files` đúng sha256 của **từng** tệp trong bộ tài liệu
  của bundle vừa cài; `~/fieldsync/assets/` có đúng các tệp đó (không thừa tệp của lần trước); `~/fieldsync/bin/fieldsync
  --version` in `fieldsync 1.4.0`.
- Cấu hình hệ thống không đổi: sha256 của `/etc/fstab`, `/etc/security/limits.conf`, `/etc/security/limits.d/*`,
  `/etc/systemd/system.conf.d/*`, `/etc/systemd/user.conf.d/*` và tuỳ chọn mount của `/tmp` giống hệt lúc đầu; phiên đăng
  nhập mới vẫn có `ulimit -Hn` là `1024`.

## Gợi ý

### Gợi ý 1

Tái hiện trước: chạy đúng lệnh của khách trên `factory` và trên `lab-open`, đọc toàn bộ output. Mã thoát 126 khác 127 khác 1.

### Gợi ý 2

Hai lỗi có thể đến từ hai nguyên nhân khác nhau. Với mỗi lỗi, hỏi "giới hạn này đến từ đâu, ai đặt, mình có quyền đổi
không"; nếu không có quyền, chương trình có cách nào tự thích nghi?

### Gợi ý 3

Đọc kỹ hướng dẫn của `fieldsync` và nghĩ xem điều nó đánh đổi có quan trọng ở **thời điểm cài** không.
