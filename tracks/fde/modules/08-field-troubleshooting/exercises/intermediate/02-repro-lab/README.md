---
title: "Hiện trường: tái hiện lỗi của bệnh viện trên máy lab"
level: intermediate
services: []
files:
  - path: customer-bundle
    note: Support bundle bệnh viện gửi (đã giải nén, đã che secret)
  - path: starter/repro.sh
    note: Bạn viết
  - path: tests/test_repro_lab.py
    note: Không sửa
run:
  - nice -n 15 uv run python tracks/fde/product/release.py build --version 1.0.0 --out tracks/fde/product/dist
  - nice -n 15 uv run python -m fdekit prepare lab-open
  - nice -n 15 uv run python -m fdekit derive 07-customer-integration-quillo
  - uv run pytest tracks/fde/modules/08-field-troubleshooting/exercises/intermediate/02-repro-lab -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Tuần trước một đồng nghiệp bật SSO cho quillo ở bệnh viện (máy `hospital`, quillo 1.0.0), dặn IT bệnh viện "cấu hình
xong rồi, nhân viên dùng tài khoản bệnh viện đăng nhập được", rồi chuyển sang dự án khác. Hôm nay IT bệnh viện gửi ticket
kèm support bundle. Bạn không vào được máy của bệnh viện và chính sách của họ không cho thử nghiệm trên máy đang chạy.
Đội sản phẩm cũng hỏi bạn: "lỗi của quillo hay của môi trường? gửi cách tái hiện". Việc của bạn là dựng lại **đúng lỗi
đó** trên máy lab của mình bằng một script mà người khác chạy lại được.

## Đề bài

Ticket:

> Từ khi bật đăng nhập bằng tài khoản bệnh viện, bấm "Đăng nhập" thì trang báo lỗi, không ai đăng nhập được. Đăng nhập
> bằng token quản trị thì vẫn vào. IdP của bệnh viện vẫn hoạt động bình thường với các hệ thống khác.

Support bundle ở `customer-bundle/` (tạo bằng `quillo-support.sh` của bài intermediate 01; đọc `meta.txt`,
`quillo/env.txt`, `quillo/logs/api.log` trước). Máy lab của bạn: `lab-open` (Ubuntu 22.04, Docker + compose, `fde` có
sudo, ra internet được) đang chạy quillo 1.0.0 bằng compose ở `/home/fde/quillo-1.0.0`, **chưa** bật SSO (snapshot dẫn
xuất `07-customer-integration-quillo`; cách bật SSO ở mục "SSO (OIDC) và ACL theo thư mục" trong
[README sản phẩm](../../../../../product/README.md)).

Viết `starter/repro.sh` (POSIX `sh`). Test chép nó vào `/home/fde/repro/repro.sh` trên máy lab rồi chạy
`cd /home/fde/repro && sh repro.sh` bằng `fde`. Script phải tự dựng mọi thứ nó cần trên máy lab (không dùng dữ liệu hay
secret của bệnh viện, không cần mạng ra ngoài), và chạy lại lần hai trên cùng máy vẫn đúng.

**Chữ ký lỗi.** Với mỗi dòng log JSON `level` `ERROR` của dịch vụ `api` có trường `error`, chữ ký là cặp (`msg`, `error`
sau khi thay mọi URL `http(s)://…` bằng `<url>`). Bundle của bệnh viện có đúng một chữ ký trong `quillo/logs/api.log`,
đi cùng một request (`path`, `status`) ngay sau nó. Tái hiện đúng nghĩa là máy lab sinh ra **cùng chữ ký** khi được gọi
đúng như người dùng ở bệnh viện gọi, và trả **cùng status** cho request đó. Chữ ký khác (dù cùng `msg`) là một lỗi khác.

Test làm theo thứ tự:

1. Boot snapshot (`fdekit.vm("lab-open", base=..., memory_mb=3072, forwards=(18080,))`), chờ quillo `/healthz` 200.
2. Chạy `repro.sh` (≤ 150 s, phải thoát `0`), chờ `/healthz` 200 (≤ 120 s); làm lại lần nữa (chạy lại script).
3. Gọi **hai lần** đúng `path` của request trong bundle (GET, không theo redirect) qua cổng 18080, gọi `/api/me` bằng
   token quản trị trong `.env` của máy lab.
4. Đọc log `api` sinh ra từ bước 3 (`docker compose logs --since`) và so chữ ký.

Cả bài ~40 s trên máy của repo.

## Tiêu chí đạt

`test_repro_matches_customer_signature`:

- `repro.sh` thoát `0` ở cả hai lần chạy, mỗi lần ≤ 150 s; sau mỗi lần quillo trả `/healthz` 200 trong 120 s.
- Hai request ở bước 3 trả đúng status của request tương ứng trong bundle.
- `/api/me` với token quản trị trả `200`.
- Log `api` sinh ra từ các request ở bước 3 có một dòng `ERROR` mang **đúng** chữ ký của bundle.

## Gợi ý

### Gợi ý 1

Tách thông báo lỗi trong bundle thành từng lớp: thư viện nào báo, ở bước nào của kết nối, lý do cụ thể là gì. Lớp trong
cùng là thứ bạn phải tái tạo, các lớp ngoài sẽ tự đến.

### Gợi ý 2

Liệt kê những gì máy bệnh viện có mà máy lab chưa có (đọc `quillo/env.txt` và so với `.env` trên máy lab), rồi những gì
máy lab có mà bệnh viện **không** có. Tái hiện thường hỏng ở danh sách thứ hai.

### Gợi ý 3

Thử vài biến thể gần đúng và xem chữ ký của chúng khác nhau thế nào; mỗi biến thể sai cho bạn biết một điều về nguyên
nhân thật.
