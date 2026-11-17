---
title: App Python 3.12 trên máy bệnh viện cũ
level: intermediate
services: []
files:
  - path: starter/build_bundle.sh
    note: 4 TODO, POSIX sh, chạy trên máy bạn (có mạng)
  - path: starter/install.sh
    note: 4 TODO, POSIX sh, chạy trên máy khách (không mạng, không sudo)
  - path: app/pyproject.toml
    note: App mẫu census (không sửa)
  - path: app/uv.lock
    note: Phụ thuộc đã ghim (không sửa)
  - path: tests/test_python_bundle.py
    note: Không sửa
run:
  - nice -n 15 uv run python -m fdekit prepare hospital
  - uv run pytest tracks/fde/modules/04-restricted-hosts/exercises/intermediate/02-modern-python-old-host -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Product viết app bằng Python 3.12 vì đó là bản họ hỗ trợ; bệnh viện chạy Ubuntu 20.04 với Python 3.8 và sẽ không nâng OS
chỉ vì bạn. Bài này mang theo **runtime** của chính bạn và mọi phụ thuộc trong một bundle, cài hoàn toàn trong `$HOME` của
một máy không ra được mạng, không đụng một tệp nào của hệ điều hành.

## Đề bài

`app/` là CLI `census` (đếm giường đang dùng theo khoa từ tệp CSV xuất của hệ thống nhập viện) với `uv.lock` đã ghim;
`requires-python = ">=3.12"`, phụ thuộc `pydantic` (có phần biên dịch). Chạy: `census <admissions.csv> <YYYY-MM-DD>`, in
JSON (gồm phiên bản Python và thư viện nó đang dùng, đường dẫn interpreter).

Máy `hospital`: Ubuntu 20.04, Python hệ thống 3.8. Quy định của IT bệnh viện: máy chủ không được tải gói từ internet (bài
này VM không có đường ra nào), mọi thứ cài vào `$HOME` của user dịch vụ, không đổi gì ngoài đó; được mang vào bundle mọi
thứ cần thiết, kể cả runtime, miễn ghim phiên bản và sha256. Runtime đã chuẩn bị sẵn ở phần `0. Cài đặt` của README module
(python-build-standalone CPython 3.12.15 bản `20261021`).

Viết hai script POSIX sh:

**`starter/build_bundle.sh <thư mục app> <thư mục công cụ> <thư mục bundle>`** chạy trên máy bạn. Test chạy nó trong
sandbox (`testkit.run_sandboxed`): có mạng, có `uv` trên `PATH`, `HOME` là một thư mục tạm rỗng, thư mục công cụ là
`data/raw/fde-tools/` (chỉ đọc), chỉ ghi được trong thư mục làm việc tạm chứa bản sao `app/` và thư mục bundle; thoát `0`
trong 240 s. Bundle phải có `install.sh` ở thư mục gốc.

**`starter/install.sh`** nằm trong bundle. Test nén bundle, chép vào `hospital` (1024 MB, **không mạng**), giải nén thành
`/home/fde/census-bundle/`, rồi chạy **hai lần** `cd /tmp && sh /home/fde/census-bundle/install.sh` bằng user `fde`, mỗi
lần ≤150 s. Sau đó `/home/fde/.local/bin/census` phải chạy được, cả trong phiên đăng nhập bình thường lẫn khi gọi bằng
`env -i HOME=/home/fde PATH=/usr/bin:/bin`.

Đo trên máy của repo: cả bài ~30 s (gồm tải wheel). Tự boot máy để điều tra: `with fdekit.vm("hospital",
memory_mb=1024) as m:`.

## Tiêu chí đạt

`test_python312_app_on_hospital`:

- `build_bundle.sh` thoát `0`, bundle có `install.sh`.
- Hai lần `install.sh` đều thoát `0` trên `hospital` không mạng.
- `census` đọc một tệp CSV sinh ngẫu nhiên mỗi lần chạy test, in đúng số giường đang dùng theo khoa và số bản ghi, ở cả
  hai cách gọi.
- `census` báo chạy bằng Python `3.12.x`, `pydantic` `2.11.7`, `pydantic-core` `2.33.2` (bản ghim trong `uv.lock`), và
  interpreter của nó (sau khi `readlink -f`) nằm trong `/home/fde/`.
- Không đổi gì ngoài `$HOME`: danh sách và sha256 các tệp trong `/usr/local`, `/opt`, `/etc/environment`,
  `/etc/profile.d` cùng output `/usr/bin/python3 -V` giống hệt trước khi cài.

## Gợi ý

### Gợi ý 1

Thử trên VM trước: Python có sẵn trên máy làm được những gì (`venv`? `pip`?) và app nói gì khi chạy bằng nó. Ghi lại các
thông số của máy đích mà wheel phụ thuộc vào.

### Gợi ý 2

Runtime bạn mang theo có sẵn những gì để tạo môi trường và cài wheel? Đọc tài liệu của python-build-standalone về các
biến thể (`install_only`) và điều kiện về glibc.

### Gợi ý 3

Một lệnh chạy được trong phiên SSH của bạn chưa chắc chạy được khi `PATH` chỉ có `/usr/bin:/bin` và không có biến môi
trường nào khác. Cái gì trong bản cài của bạn đang dựa vào môi trường?
