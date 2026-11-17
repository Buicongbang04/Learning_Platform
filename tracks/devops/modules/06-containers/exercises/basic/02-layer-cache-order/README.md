---
title: Thứ tự layer để cache dependency, và giữ bí mật ngoài build context
level: basic
services: []
files:
  - path: starter/Dockerfile
    note: 1 TODO
  - path: starter/.dockerignore
    note: 1 TODO
  - path: tests/test_layer_cache.py
    note: Không sửa
  - path: tests/fixtures/app/export_orders.py
    note: Job export của team, không sửa
  - path: tests/fixtures/app/requirements.txt
    note: Không sửa
run:
  - docker pull python:3.12.16-slim-trixie
  - uv run pytest tracks/devops/modules/06-containers/exercises/basic/02-layer-cache-order -q
---

## Mục tiêu

Đọc được build cache của BuildKit qua `docker history`, sắp layer để sửa một dòng code không cài lại dependency, và dùng
`.dockerignore` để bí mật trên máy dev không bao giờ lọt vào image.

## Đề bài

Team export có job `export_orders.py` (đếm đơn Olist theo tháng, dùng `python-dateutil`). Thư mục của job (`tests/fixtures/app/`)
có thêm `notes.md`, `tests/export_checks.py`, và trên máy mỗi dev có `.env` chứa token thật (test tạo `.env` với token giả trong
bản chép của context, vì `.env` không bao giờ được commit). CI phàn nàn: sửa một dòng log là `pip install` chạy lại từ đầu; bảo
mật phát hiện `.env` nằm trong image đã đẩy lên registry.

Sửa `starter/Dockerfile` và `starter/.dockerignore`. Giữ một stage, image nền `python:3.12.16-slim-trixie`, `USER 10001`, và
`CMD` chạy `export_orders.py` in một dòng JSON có `build_id`.

**Cách test chấm.** Test dựng build context từ `tests/fixtures/app/` cộng `.env` giả cộng hai tệp của bạn, đổi dòng
`BUILD_ID = "..."` trong `export_orders.py` thành một mã ngẫu nhiên, build bằng `DockerLab.build`; rồi đổi mã đó lần nữa (chỉ
sửa code, không đổi `requirements.txt`) và build lại. Sau đó:

- So `CreatedAt` của bước `RUN ... pip install ...` (bước mới nhất có `pip` và `install` mà image nền không có) trong
  `docker history` của hai lần build. Giống nhau nghĩa là lần build thứ hai lấy layer đó từ cache.
- Chạy image lần hai với `CMD` mặc định; output phải có đúng `build_id` mới (code mới đã vào image).
- Chạy `python3` trong image, duyệt toàn bộ hệ thống tệp (trừ `/proc`, `/sys`, `/dev`) tìm tệp tên `.env`, `export_checks.py`,
  `notes.md`; có tệp nào là fail.
- Một test làm đúng các bước trên với bản gốc của starter (`tests/fixtures/starter/`) và đòi bắt được: layer dependency build
  lại, `.env` và `export_checks.py` lọt vào image.

Lần build đầu cần mạng để tải `python-dateutil`; lỗi mạng thì test skip.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/06-containers/exercises/basic/02-layer-cache-order -q` pass.
- Giải thích được vì sao `COPY . .` đặt trước `pip install` làm cache vô dụng, dù `requirements.txt` không đổi.
- Chỉ ra được hai cách giữ `.env` ngoài image (`.dockerignore` loại trừ, hoặc chỉ `COPY` đúng tệp cần) và vì sao nên có cả hai.

## Gợi ý

### Gợi ý 1

Cache key của một bước `COPY` là checksum nội dung các tệp được chép; của bước `RUN` là chuỗi lệnh cộng layer cha. Một bước
đổi thì mọi bước sau nó build lại. Tự xem bằng `docker history --no-trunc <image>` sau hai lần build, chú ý cột `CREATED`.

### Gợi ý 2

`.dockerignore` kiểu allowlist an toàn hơn denylist: `*` loại tất cả, rồi `!requirements.txt`, `!export_orders.py` thêm lại
đúng thứ cần. Tệp mới ai đó thêm vào thư mục (một `id_rsa`, một bản dump DB) mặc định không vào context.
