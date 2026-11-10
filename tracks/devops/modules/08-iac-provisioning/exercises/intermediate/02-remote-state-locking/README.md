---
title: Remote state trên S3 có khoá và mã hoá, chuyển state từ local lên backend
level: intermediate
services: [localstack-devops]
files:
  - path: starter/infra/main.tf
    note: Tài nguyên của stack, không sửa
  - path: tests/fixtures/no-lockfile/main.tf
    note: Backend thiếu khoá và mã hoá, test dùng để chứng minh phép kiểm
  - path: tests/test_remote_state.py
    note: Không sửa
run:
  - docker compose -f setup/docker-compose.yml --profile devops up -d --wait localstack-devops
  - uv run pytest tracks/devops/modules/08-iac-provisioning/exercises/intermediate/02-remote-state-locking -q
---

## Mục tiêu

Đưa state của một stack từ máy cá nhân lên backend `s3` dùng chung: khoá để hai người không cùng ghi, mã hoá phía client để người
đọc được bucket vẫn không đọc được state, key theo môi trường; rồi biết xử lý một khoá bị kẹt.

## Đề bài

Stack `platform` của Olist Shop (`starter/infra/main.tf`: bảng DynamoDB `carts` và một tham số SSM) đang dùng state local. Viết hai
tệp mới trong `starter/infra/`:

- `encryption.tf`: biến `state_passphrase` (`sensitive = true`) và khối `terraform { encryption { ... } }` dùng key provider
  `pbkdf2` lấy passphrase từ biến đó, method `aes_gcm`, áp cho cả `state` và `plan` với `enforced = true`.
- `backend.tf`: khối `terraform { backend "s3" { ... } }` với bucket `"${var.prefix}-tfstate"`, key
  `"olist/${var.environment}/platform.tfstate"`, region `us-east-1`, `encrypt = true`, `use_lockfile = true`. Không cần
  `endpoint`: env của test (và hướng dẫn chạy tay ở mục 0 của module) đã trỏ S3 về LocalStack.

Bucket và key dùng biến là **early evaluation** của OpenTofu (từ 1.8); với Terraform bạn phải truyền bằng `-backend-config`.

**Cách test chấm.** Qua `TofuLab` trên `localstack-devops`, đặt `TF_VAR_state_passphrase` như CI lấy từ secret store:

1. Tạo trước bucket `<prefix>-tfstate` (bật versioning) bằng boto3, vì backend không tự tạo bucket.
2. Tạm bỏ `backend.tf`, `init` và `apply` với state local.
3. Trả `backend.tf` lại, chạy `tofu init -migrate-state -force-copy`, rồi plan và `state list`.
4. Đặt một tệp `olist/staging/platform.tfstate.tflock` giả như job CI `ci@runner-17` chết giữa chừng để lại, chạy plan với
   `-lock-timeout=0s`, rồi `tofu force-unlock -force <ID>` và plan lại.
5. Plan với passphrase sai; lưu `plan -out` rồi `tofu show` tệp đó với passphrase đúng và sai.

Một test riêng chạy `tests/fixtures/no-lockfile` (backend không `use_lockfile`, không `encryption`) và đòi các phép kiểm trên bắt
được nó. Cả bài khoảng 1,5 phút.

## Tiêu chí đạt

- State local sau bước 2 đã mã hoá: JSON có `encrypted_data`, không có `resources`, không đọc được tên bảng.
- State nằm ở `s3://<prefix>-tfstate/olist/staging/platform.tfstate`, cũng đã mã hoá.
- Sau khi chuyển, plan là `No changes`, state có đúng `aws_dynamodb_table.carts` và `aws_ssm_parameter.carts_table`.
- Có tệp khoá của job khác thì plan báo `Error acquiring the state lock` và cho biết người giữ (`ci@runner-17`); sau
  `force-unlock` plan chạy được.
- Passphrase sai thì plan lỗi (không đọc được state).
- `tofu plan -out` sinh tệp plan đã mã hoá: không phải tệp zip đọc được, `tofu show` đọc được với passphrase đúng và lỗi với
  passphrase sai. Bản `no-lockfile` (không `encryption`) sinh tệp plan zip thường.
- Sau `force-unlock`, tệp `.tflock` không còn trên bucket.

## Gợi ý

### Gợi ý 1

Khối `encryption` áp cho mọi backend kể cả local, nên nó phải có **trước** khi state lên S3. Thêm mã hoá cho một state cũ chưa mã
hoá là việc hai bước: lần đầu thêm `method "unencrypted"` làm `fallback` và **không** `enforced` (OpenTofu từ chối unencrypted khi
`enforced = true`), apply một lần để ghi lại state đã mã hoá, rồi bỏ fallback và bật `enforced`. Bài này tránh bước đó bằng cách mã
hoá ngay từ apply đầu.

### Gợi ý 2

`use_lockfile = true` khoá bằng object `<key>.tflock` ghi có điều kiện; không cần bảng DynamoDB. Thông báo lỗi khoá in `ID`,
`Who`, `Created`: đó là thứ bạn đối chiếu với job CI trước khi `force-unlock`. Passphrase của `pbkdf2` phải dài ít nhất 16 ký tự,
OpenTofu tự kiểm.
