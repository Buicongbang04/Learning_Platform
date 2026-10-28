---
title: Data lake trên S3 bằng boto3 - partition, multipart, lifecycle
level: intermediate
services: []
files:
  - path: starter/s3_lake.py
    note: 6 TODO
  - path: tests/test_s3_lake.py
    note: Không sửa. Mặc định chạy offline bằng moto; S3_BACKEND=localstack để chạy trên LocalStack
run:
  - uv run pytest tracks/data-engineer/modules/11-cloud/exercises/intermediate/01-s3-partitioned-lake -q
  - docker compose -f setup/docker-compose.yml up -d localstack
  - S3_BACKEND=localstack uv run pytest tracks/data-engineer/modules/11-cloud/exercises/intermediate/01-s3-partitioned-lake -q
---

## Mục tiêu

Thao tác object storage như một Data Engineer: đặt key theo partition kiểu Hive, upload file lớn
bằng multipart (và dọn dẹp khi lỗi), liệt kê có phân trang, cấu hình lifecycle để giảm chi phí.
Không cần tài khoản AWS.

## Đề bài

Hoàn thiện `starter/s3_lake.py`. Mọi hàm nhận sẵn một `boto3` S3 client `s3` (test tự tạo client
trỏ vào moto, LocalStack hoặc MinIO), nên code của bạn chạy y nguyên trên AWS thật.

1. **TODO 1** `partition_key(table, dt, filename, zone="raw") -> str`: trả
   `"<zone>/<table>/year=YYYY/month=MM/day=DD/<filename>"` (tháng, ngày có 2 chữ số).
   `table`, `filename` rỗng hoặc chứa `/` thì `ValueError`.
2. **TODO 2** `upload_partition(s3, bucket, table, dt, data: bytes, filename="part-0000.csv") -> str`:
   `put_object` vào key ở trên, trả về key.
3. **TODO 3** `multipart_upload(s3, bucket, key, data: bytes, part_size=8 MiB) -> int`: upload bằng
   `create_multipart_upload` → `upload_part` (PartNumber từ 1) → `complete_multipart_upload`, trả
   số part. `part_size < 5 MiB` thì `ValueError` (giới hạn của S3, trừ part cuối). Nếu có lỗi giữa
   chừng phải gọi `abort_multipart_upload` rồi ném lại lỗi (part mồ côi vẫn bị tính tiền lưu trữ).
4. **TODO 4** `list_partitions(s3, bucket, table, zone="raw", page_size=1000) -> list[str]`: các
   partition **duy nhất, đã sắp xếp** dạng `"year=2018/month=01/day=05"` của bảng. Phải dùng
   paginator `list_objects_v2` với `PaginationConfig={"PageSize": page_size}` (test dùng
   `page_size=2` để chắc bạn không chỉ đọc trang đầu).
5. **TODO 5** `lifecycle_rules() -> dict`: trả cấu hình dạng `{"Rules": [...]}` gồm đúng 3 rule
   `Status: "Enabled"`:
   - `ID "raw-tiering"`, `Filter {"Prefix": "raw/"}`: chuyển `STANDARD_IA` sau 30 ngày, `GLACIER`
     sau 90 ngày.
   - `ID "tmp-expire"`, `Filter {"Prefix": "tmp/"}`: `Expiration` sau 1 ngày.
   - `ID "abort-incomplete-mpu"`, `Filter {"Prefix": ""}`: `AbortIncompleteMultipartUpload`
     `DaysAfterInitiation` 7.
6. **TODO 6** `apply_lifecycle(s3, bucket) -> None`: gắn cấu hình trên vào bucket.

Chạy test: cách nhanh nhất là `uv run pytest ...` (moto giả lập S3 trong bộ nhớ,
`--with` chỉ thêm tạm thư viện, không sửa `pyproject.toml`). Không có moto thì test dùng LocalStack
(`localhost:4566`) hoặc MinIO (`localhost:9000`) nếu đang chạy, không có gì thì phần S3 tự skip
(phần hàm thuần vẫn chạy). MinIO không hỗ trợ transition sang `GLACIER` nếu chưa cấu hình tier, nên
test `apply_lifecycle` skip trên MinIO.

## Tiêu chí đạt

- `partition_key("orders", date(2018, 1, 5), "part-0000.csv")` ==
  `"raw/orders/year=2018/month=01/day=05/part-0000.csv"`; tên chứa `/` bị từ chối.
- Upload rồi đọc lại đúng nội dung; `list_partitions` trả đủ, sắp xếp, không trùng, kể cả khi phân trang.
- Multipart 11 MiB với part 5 MiB ra 3 part, nội dung khớp, không còn upload dở dang.
- Lỗi giữa multipart thì `abort_multipart_upload` được gọi đúng `UploadId` và lỗi được ném lại.
- `lifecycle_rules()` đúng 3 rule như đề; `apply_lifecycle` đọc lại được bằng
  `get_bucket_lifecycle_configuration`.

## Gợi ý

### Gợi ý 1

`complete_multipart_upload` cần `MultipartUpload={"Parts": [{"ETag": ..., "PartNumber": n}, ...]}`
với ETag lấy từ kết quả của từng `upload_part`. Bọc vòng upload trong `try/except Exception:`
→ `abort_multipart_upload(Bucket=..., Key=..., UploadId=...)` → `raise`.

### Gợi ý 2

```python
paginator = s3.get_paginator("list_objects_v2")
for page in paginator.paginate(Bucket=bucket, Prefix=f"{zone}/{table}/",
                               PaginationConfig={"PageSize": page_size}):
    for obj in page.get("Contents", []):
        ...
```

Lấy partition bằng cách cắt key: bỏ prefix bảng, bỏ phần tên file sau `/` cuối cùng.
