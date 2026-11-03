---
title: DVC remote trên MinIO (S3), push, xoá cache, pull lại
level: intermediate
services: []
files:
  - path: starter/remote.sh
    note: 3 TODO
  - path: tests/test_remote.py
    note: Không sửa
run:
  - docker compose -f setup/mlops/compose.yaml up -d
  - uv run pytest tracks/mlops/modules/03-data-versioning-quality/exercises/intermediate/04-dvc-remote-minio -q
---

## Mục tiêu

Cấu hình một DVC remote S3 trỏ vào MinIO mà không đưa khoá truy cập vào Git, đẩy dữ liệu lên, và chứng minh rằng một máy mới (cache
trống) kéo lại được đúng dữ liệu.

## Đề bài

Cần stack MLOps đang chạy (`setup/mlops/README.md`); thiếu stack thì test skip kèm lệnh bật. Bucket `dvc` đã được `minio-init` tạo.

Điền `starter/remote.sh`, gọi như `bash remote.sh <remote-url> <endpoint> <tệp>` trong gốc một repo Git đã `dvc init`
và đã `dvc add <tệp>`:

1. Thêm remote mặc định tên `storage` với URL `<remote-url>` (dạng `s3://dvc/<tiền-tố>`).
2. Đặt `endpointurl` của remote là `<endpoint>` (MinIO, không phải AWS).
3. Đẩy dữ liệu lên remote.

Khoá truy cập (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) đã có trong môi trường khi test chạy script. **Không** ghi khoá vào
`.dvc/config`, vì tệp này được commit. Test tạo tiền-tố riêng cho mỗi lần chạy và dọn sau khi xong.

## Tiêu chí đạt

- `.dvc/config` có remote `storage` là mặc định, đúng `url` và `endpointurl`, và không chứa khoá truy cập hay mật khẩu.
- Sau script, đối tượng dữ liệu nằm dưới đúng tiền-tố trong bucket `dvc` (kiểm bằng `boto3`).
- Test xoá `.dvc/cache` và tệp dữ liệu rồi chạy `dvc pull`: tệp trở lại với nội dung y hệt.

## Gợi ý

### Gợi ý 1

`dvc remote add -d <tên> <url>` rồi `dvc remote modify <tên> endpointurl <url>`. Thêm `--local` ghi vào `.dvc/config.local` (không commit),
còn không có `--local` ghi vào `.dvc/config` (commit).

### Gợi ý 2

Khoá lấy từ biến môi trường, DVC (qua boto) tự đọc `AWS_ACCESS_KEY_ID` và `AWS_SECRET_ACCESS_KEY`; bạn không cần làm gì thêm để có khoá.
