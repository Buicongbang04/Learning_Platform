---
title: "Hiện trường: nâng cấp quillo 1.0.0 → 1.1.0 tại chỗ ở bệnh viện, rồi rollback"
level: intermediate
services: []
files:
  - path: starter/upgrade.sh
    note: Bạn viết (chạy trên laptop, tới máy bệnh viện qua SSH)
  - path: starter/rollback.sh
    note: Bạn viết
  - path: tests/test_upgrade_rollback.py
    note: Không sửa; chạy thẳng tệp này để dựng máy bệnh viện và tự thử
run:
  - nice -n 15 uv run python tracks/fde/product/release.py build --version 1.1.0 --out tracks/fde/product/dist
  - nice -n 15 uv run python -m fdekit prepare hospital
  - nice -n 15 uv run python -m fdekit derive 09-production-trust-hospital
  - uv run pytest tracks/fde/modules/09-production-trust/exercises/intermediate/01-upgrade-rollback -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

CAB của bệnh viện đã duyệt cửa sổ bảo trì tối nay. Điều kiện của họ: nâng cấp quillo lên 1.1.0 **tại chỗ** (giữ thư mục
cài, giám sát và backup đêm của IT đã trỏ vào đó), và trong cùng cửa sổ phải **diễn tập rollback**: sau khi 1.1.0 chạy và
Phòng Vật tư đã lưu một tài liệu có nhãn, đưa hệ thống về 1.0.0 và chứng minh không mất gì. Rollback chưa từng chạy thử
là rollback không có thật; đêm nay bạn chạy nó.

## Đề bài

Máy bệnh viện như bài basic 03: hồ sơ `hospital` (Ubuntu 20.04, đĩa 8 GB, sau proxy công ty, không ra internet trực
tiếp), snapshot `09-production-trust-hospital`, quillo 1.0.0 cài bằng compose ở `/home/fde/quillo-1.0.0` theo
[README sản phẩm](../../../../../product/README.md) (mục "Bản phát hành", "Cài từ bundle", "Backup và restore"), 12 hợp
đồng trong `vat-tu/`. `fde` có sudo.

Viết `starter/upgrade.sh` và `starter/rollback.sh` (POSIX `sh`). Test chạy chúng **trên laptop** trong sandbox (chỉ
`$WORK` ghi được, `/tmp` là thư mục rỗng) với `SSH` (lệnh ssh tới `fde@` máy bệnh viện; `$SSH "lệnh"` chạy một lệnh ở
đó, stdin/stdout đi qua được), `BUNDLE` (đường dẫn `quillo-1.1.0.tar` trên laptop, chỉ đọc), `WORK` (thư mục làm việc,
cùng một thư mục cho cả hai script).

Test làm theo thứ tự:

1. Boot snapshot, chờ quillo 1.0.0 trả `/healthz` 200; đếm tài liệu và chunk; hỏi một câu về hợp đồng phân phối với
   Fuse Medical (`top_k` 4) và ghi lại hợp đồng được trích.
2. Chạy `upgrade.sh` (≤ 150 s, phải thoát `0`), rồi chờ `/healthz` 200 với `"version": "1.1.0"` (≤ 120 s).
3. Kiểm trên 1.1.0 (mục "Tiêu chí đạt"), rồi nạp qua API một phụ lục giá mới vào `vat-tu/` với hai `tags` (mã phụ lục
   ngẫu nhiên mỗi lần chạy) và hỏi về nó.
4. Chạy `rollback.sh` (≤ 120 s, phải thoát `0`), rồi chờ `/healthz` 200 với `"version": "1.0.0"` (≤ 120 s).
5. Kiểm sau rollback.

Quy định của IT bệnh viện trong cửa sổ bảo trì: trong lúc mỗi script chạy, đĩa `/` không bao giờ dùng quá 85%
(Available ≥ 15% của Size theo `df -B1 --output=size,avail /`, test đo mỗi 2 s qua một phiên SSH riêng); không xoá hay
sửa `/home/fde/quillo-1.0.0.tar` (bản lưu trữ của phiên bản 1.0.0); không đổi `QUILLO_ADMIN_TOKEN`,
`QUILLO_DB_PASSWORD` trong `.env`; dữ liệu bệnh viện không rời máy (không tệp nào trong `$WORK` là bản dump hay chứa dữ
liệu của bảng `documents`/`chunks`). Bản backup trước nâng cấp phải nằm trong `/home/fde/backups/` trên máy, định dạng
của `ops/backup.sh` (`<tên>.dump` + `<tên>.dump.sha256`).

Chạy thẳng tệp test (`PYTHONPATH=. uv run python tracks/fde/modules/09-production-trust/exercises/intermediate/01-upgrade-rollback/tests/test_upgrade_rollback.py`)
để dựng đúng máy đó và thử tay. Cả bài ~80 s trên máy của repo.

## Tiêu chí đạt

`test_upgrade_rollback_keeps_documents`:

- Hai script thoát `0` trong thời hạn, quillo lên đúng version sau mỗi script, đĩa không xuống dưới mức 15% ở lần đo nào
  trong lúc script chạy.
- Sau nâng cấp: `schema_migrations` có migration 2; số tài liệu và chunk không đổi; câu hỏi ở bước 1 vẫn trích hợp đồng
  đó; một trong ba tệp `.dump` mới nhất ở `/home/fde/backups/` khớp `.sha256` và restore vào database trống ra đúng số tài
  liệu, chunk trước nâng cấp với schema 1.
- Sau rollback: số tài liệu và chunk bằng lúc trước rollback (gồm phụ lục nạp trên 1.1.0), phụ lục còn đúng `tags`, câu
  hỏi ở bước 1 vẫn trích hợp đồng cũ và câu hỏi về phụ lục vẫn trích phụ lục.
- Token, mật khẩu database, bản lưu trữ 1.0.0 không đổi; `$WORK` không chứa dữ liệu bệnh viện.

## Gợi ý

### Gợi ý 1

Viết ra giấy trạng thái của máy sau từng bước của cả hai script (đĩa, image trong Docker, `.env`, schema), kể cả khi
script dừng giữa chừng. Rollback phải chạy được từ mọi trạng thái đó, không chỉ từ trạng thái "nâng cấp xong đẹp".

### Gợi ý 2

Liệt kê những gì thay đổi giữa hai bản (mã, image, cấu hình, dữ liệu) và với từng thứ, hỏi: nó có cần quay về không, và
quay về bằng cách nào thì không làm mất thứ khác.

### Gợi ý 3

Thử chạy cách nâng cấp đầu tiên bạn nghĩ tới trên máy dựng bằng tệp test, trong khi một cửa sổ khác theo dõi máy như
giám sát của bệnh viện. Thất bại ở lab tối nay rẻ hơn thất bại trong cửa sổ bảo trì.
