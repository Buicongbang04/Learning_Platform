---
title: "Hiện trường: backup và kế hoạch chỗ chứa trước khi nâng cấp ở bệnh viện"
level: basic
services: []
files:
  - path: starter/pre_upgrade.sh
    note: Bạn viết (chạy trên laptop, tới máy bệnh viện qua SSH)
  - path: tests/test_backup_before_upgrade.py
    note: Không sửa; chạy thẳng tệp này để dựng máy bệnh viện và tự thử
run:
  - nice -n 15 uv run python tracks/fde/product/release.py build --version 1.1.0 --out tracks/fde/product/dist
  - nice -n 15 uv run python -m fdekit prepare hospital
  - nice -n 15 uv run python -m fdekit derive 09-production-trust-hospital
  - uv run pytest tracks/fde/modules/09-production-trust/exercises/basic/03-backup-before-upgrade -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Bệnh viện chạy quillo 1.0.0 được vài tháng và muốn lên 1.1.0 (gắn nhãn tài liệu). Hội đồng thay đổi (CAB) của IT bệnh
viện chỉ duyệt cửa sổ bảo trì khi bạn nộp trước hai thứ: một **bản backup đã kiểm** nằm sẵn trên máy, và một **kế hoạch
chỗ chứa** cho biết lần nâng cấp sẽ đặt gì lên đĩa và máy còn bao nhiêu chỗ sau đó. Việc này làm trong giờ hành chính,
khi bác sĩ vẫn đang dùng quillo.

## Đề bài

Máy bệnh viện: hồ sơ `hospital` (Ubuntu 20.04, đĩa 8 GB, sau proxy công ty), snapshot dẫn xuất
`09-production-trust-hospital`. quillo 1.0.0 cài bằng compose ở `/home/fde/quillo-1.0.0` đúng theo mục "Cài từ bundle"
của [README sản phẩm](../../../../../product/README.md) (có `ops/backup.sh`, `ops/restore.sh`); Phòng Vật tư đã nạp 12 hợp
đồng. `fde` có sudo. Bundle 1.1.0 (`tracks/fde/product/dist/quillo-1.1.0.tar`) nằm trên laptop của bạn.

Viết `starter/pre_upgrade.sh` (POSIX `sh`). Test chạy nó **trên laptop** trong sandbox (chỉ `$WORK` ghi được, `/tmp` là
thư mục rỗng), với các biến:

| Biến | Giá trị |
| --- | --- |
| `SSH` | lệnh ssh tới `fde@` máy bệnh viện; `$SSH "lệnh"` chạy một lệnh ở đó, stdin/stdout đi qua được |
| `BUNDLE` | đường dẫn `quillo-1.1.0.tar` trên laptop (chỉ đọc) |
| `WORK` | thư mục làm việc trên laptop |

Script phải tạo trên máy bệnh viện một bản backup database quillo theo định dạng của `ops/backup.sh` (`pg_dump -Fc`, tệp
`<tên>.dump` kèm `<tên>.dump.sha256` cùng thư mục, quyền `0600`) và ghi `$WORK/storage-plan.json`:

| Khoá | Kiểu | Ý nghĩa |
| --- | --- | --- |
| `disk_free_bytes` | số nguyên | dung lượng trống của `/` trên máy (`df -B1`, cột Available) **trước** khi backup |
| `db_bytes` | số nguyên | `pg_database_size` của database `quillo` |
| `dump` | chuỗi | đường dẫn tuyệt đối của tệp `.dump` trên máy |
| `dump_bytes` | số nguyên | kích thước tệp đó |
| `stage` | mảng chuỗi | các tệp của bundle 1.1.0 (đường dẫn trong thư mục gốc `quillo-1.1.0/`, vd. `compose.yaml`) mà lần nâng cấp sẽ đặt lên đĩa máy này |
| `stage_bytes` | số nguyên | tổng kích thước các tệp trong `stage` (theo bundle) |
| `free_after_bytes` | số nguyên | `disk_free_bytes − dump_bytes − stage_bytes` |

Một tệp của bundle được **vắng** trong `stage` chỉ khi: nó nằm trong `chart/` (bản cài compose không dùng), hoặc
`/home/fde/quillo-1.0.0/manifest.json` ghi cùng đường dẫn với cùng sha256 (dùng lại bản đang có trên máy), hoặc nó là
`images/*.tar` mà image bên trong (image ID, tức digest của config) đã có trong Docker của máy.

Quy định của IT bệnh viện trong lúc script chạy (test đo mỗi 2 s qua một phiên SSH riêng):

1. quillo phục vụ bình thường: `/healthz` trả 200 ở mọi lần đo.
2. Đĩa `/` không bao giờ dùng quá 85%: Available ≥ 15% của Size (`df -B1 --output=size,avail /`) ở mọi lần đo.
3. Không thêm, xoá hay sửa tệp nào trong `/home/fde/quillo-1.0.0/` (trừ những gì quillo tự ghi trong `inbox/`), không
   đụng `/home/fde/quillo-1.0.0.tar` (bản lưu trữ của phiên bản đang chạy).
4. Dữ liệu bệnh viện không rời máy: không tệp nào trong `$WORK` là bản dump hay chứa dữ liệu của bảng `documents`/`chunks`.

Mỗi lần chấm, máy có thêm một lượng dữ liệu khác của bệnh viện (20–120 MiB trong `/var/lib/his-export/`), nên số đo
đổi theo lần chạy. Chạy thẳng tệp test (`PYTHONPATH=. uv run python tracks/fde/modules/09-production-trust/exercises/basic/03-backup-before-upgrade/tests/test_backup_before_upgrade.py`)
để dựng đúng máy đó và thử tay. Cả bài ~40 s trên máy của repo.

## Tiêu chí đạt

`test_backup_and_storage_plan`:

- `pre_upgrade.sh` thoát `0` trong 180 s; bốn quy định trên đúng ở mọi lần đo và sau khi chạy.
- Tệp `dump` có trên máy, quyền `0600`, đúng `dump_bytes`, khớp `.sha256` đi kèm (`sha256sum -c`); restore vào một
  database trống bằng `pg_restore` cho đúng số tài liệu, số chunk của database đang chạy và schema 1.
- `disk_free_bytes` lệch không quá 64 MiB so với số test đo ngay trước khi chạy script; `db_bytes` lệch không quá 10% so
  với `pg_database_size`; `stage` chỉ gồm tệp có trong bundle, không lặp, đủ các tệp không được vắng; `stage_bytes` và
  `free_after_bytes` đúng phép tính trên.
- Kế hoạch vừa máy: đĩa trống test đo trước khi chạy − kích thước thật của dump − `stage_bytes` ≥ 15% Size.

## Gợi ý

### Gợi ý 1

Đo trước, quyết sau: dung lượng trống, kích thước database, kích thước từng tệp trong bundle. Một kế hoạch chỗ chứa là
phép cộng trừ trên những con số đó, không phải cảm giác "8 GB chắc đủ".

### Gợi ý 2

So `manifest.json` của bản đang chạy với của bundle mới. Hai tệp khác sha256 chưa chắc là hai thứ khác nhau.

### Gợi ý 3

Một bản backup chưa từng được restore thử là một giả định. Restore thử ở đâu để không đụng database đang phục vụ?
