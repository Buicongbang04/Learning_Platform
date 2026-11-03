---
title: Version hoá một tệp dữ liệu bằng DVC (add, cache, checkout theo commit)
level: basic
services: []
files:
  - path: starter/track.sh
    note: 2 TODO
  - path: starter/restore.sh
    note: 1 TODO
  - path: tests/test_track.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/03-data-versioning-quality/exercises/basic/01-dvc-add-cache-checkout -q
---

## Mục tiêu

Dùng `dvc add` để Git chỉ giữ một con trỏ nhỏ (`.dvc`) còn dữ liệu nằm trong cache, rồi quay về đúng phiên bản dữ liệu của
một commit cũ chỉ bằng `git checkout` + `dvc checkout`.

## Đề bài

Test dựng một repo Git tạm, chạy `dvc init`, rồi gọi hai script của bạn trong sandbox (`cwd` là gốc repo):

- `bash track.sh <tệp>`: đưa tệp dưới quyền DVC và commit con trỏ vào Git với message `track <tệp>`. Chạy lại script
  sau khi tệp đã đổi nội dung phải tạo một commit mới (một phiên bản dữ liệu mới).
- `bash restore.sh <rev> <tệp>`: đưa **tệp dữ liệu** về đúng nội dung mà commit `<rev>` đã ghi nhận, không đổi
  `HEAD` của Git và không để lại thay đổi nào chưa commit ngoài con trỏ `.dvc` đã được lấy về từ `<rev>`.

Dữ liệu là CSV chuyến taxi nhỏ do test sinh ra. Cả hai script đã có `set -euo pipefail`; chỉ cần điền lệnh.

## Tiêu chí đạt

- Sau `track.sh`: tệp dữ liệu không nằm trong Git (bị `.gitignore`), con trỏ `.dvc` nằm trong Git và có `md5` khớp nội dung.
- Bản sao nội dung nằm trong cache của DVC (`.dvc/cache`), cây làm việc Git sạch.
- Sửa dữ liệu rồi `track.sh` lần nữa: có hai commit `track ...`, hai `md5` khác nhau.
- `restore.sh <commit đầu> <tệp>` trả đúng nội dung phiên bản 1; `HEAD` không đổi.

## Gợi ý

### Gợi ý 1

`dvc add` tự ghi `data/.gitignore` và tạo `data/trips.csv.dvc`. Bạn phải `git add` cả hai rồi mới commit.

### Gợi ý 2

Lấy con trỏ cũ về: `git checkout <rev> -- <tệp>.dvc`. Sau đó `dvc checkout <tệp>` đọc con trỏ đó và dựng lại tệp từ cache.
Chạy lại `git status` để thấy con trỏ đã khác `HEAD`.
