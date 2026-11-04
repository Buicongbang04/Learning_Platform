---
title: Wheelhouse offline cho một app Python
level: basic
services: []
files:
  - path: starter/build_bundle.sh
    note: 4 TODO, POSIX sh, chạy trên máy bạn (có mạng)
  - path: starter/install.sh
    note: 4 TODO, POSIX sh, chạy trên máy khách (không mạng)
  - path: app/pyproject.toml
    note: App mẫu intake (không sửa)
  - path: app/uv.lock
    note: Phụ thuộc đã ghim (không sửa)
  - path: tests/test_wheelhouse.py
    note: Không sửa
run:
  - nice -n 15 uv run python -m fdekit prepare lawfirm-staging
  - uv run pytest tracks/fde/modules/02-packaging-delivery/exercises/basic/03-offline-wheelhouse -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

"Có `pip install -r requirements.txt` là xong" chỉ đúng khi máy có internet và giống máy bạn. Máy staging của công ty
luật không ra internet, và nó **không giống** laptop của bạn. Bài này đóng một app Python nhỏ thành bundle cài được
hoàn toàn offline, đúng phụ thuộc đã ghim trong `uv.lock`, trên Python có sẵn của hệ điều hành khách.

## Đề bài

`app/` là CLI `intake` (Pydantic + PyYAML, có phần biên dịch C/Rust) với `uv.lock` đã ghim. Viết hai script POSIX sh:

**`starter/build_bundle.sh <thư mục app> <thư mục bundle>`** chạy trên máy bạn và tạo bundle. Test chạy nó trong sandbox
(`testkit.run_sandboxed`): có mạng, có `uv` trên `PATH`, `HOME` là một thư mục tạm rỗng (không có cache sẵn), chỉ ghi
được trong thư mục làm việc tạm chứa bản sao `app/` và thư mục bundle; thoát `0` trong 240 s. Bundle phải có `install.sh`
ở thư mục gốc.

**`starter/install.sh`** nằm trong bundle. Test nén bundle, chép vào máy `lawfirm-staging` (Ubuntu 22.04, **không ra
internet, không DNS**), giải nén thành `/home/fde/intake-bundle/` rồi chạy `sh /home/fde/intake-bundle/install.sh` bằng
user `fde`, **không sudo**, từ một thư mục khác (`/tmp`); thoát `0` trong 120 s. Sau đó
`/home/fde/intake/bin/intake <tệp.yaml>` phải chạy được.

Ràng buộc của khách: chỉ dùng `/usr/bin/python3` có sẵn của hệ điều hành (không mang Python riêng, không cài gói hệ
thống). Python, ABI và glibc của máy khách **không giống** máy bạn: wheel phải khớp với máy **đích**. Tự xác định các
thông số đó của `lawfirm-staging` (cách làm ở module 01) rồi ghi lại trong `build_bundle.sh`.

## Tiêu chí đạt

`test_offline_install_on_lawfirm_staging`:

- `build_bundle.sh` thoát `0`, bundle có `install.sh`.
- `install.sh` thoát `0` trên `lawfirm-staging` không mạng.
- `intake` đọc một tệp YAML sinh ngẫu nhiên mỗi lần chạy test và in đúng số tài liệu, tổng số trang, danh sách tag.
- `intake` báo nó chạy bằng đúng phiên bản Python của `/usr/bin/python3` trong VM, với `pydantic` và `pyyaml` đúng bản
  ghim trong `uv.lock` (2.11.7 và 6.0.2).

## Gợi ý

### Gợi ý 1

`uv export` biến `uv.lock` thành `requirements.txt` có hash; `uv build` dựng wheel của app. Còn tải wheel cho một máy
khác thì `uv` chưa có lệnh riêng: `pip download` có các tuỳ chọn chọn Python/nền tảng đích, và chạy được qua
`uvx --from pip==<bản> pip …` mà không cần cài pip vào đâu.

### Gợi ý 2

Đừng giả định máy đích có những gì laptop bạn có, kể cả những module "chuẩn" của Python. Đọc kỹ thông báo lỗi đầu tiên
trên VM; thứ còn thiếu có thể mang theo trong chính bundle.

### Gợi ý 3

Môi trường ảo nhìn thấy gói của hệ điều hành thì app có thể chạy bằng một phiên bản phụ thuộc khác hẳn bản bạn ghim, mà
không báo lỗi gì.
