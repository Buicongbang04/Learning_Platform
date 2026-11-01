---
title: Test module bằng tofu test với mock provider, sửa module theo chính sách trivy
level: intermediate
services: [localstack-devops]
files:
  - path: starter/modules/artifact-bucket/main.tf
    note: Module đã đúng, cần test
  - path: starter/modules/artifact-bucket/tests/artifact_bucket.tftest.hcl
    note: Viết test ở đây
  - path: starter/modules/upload-bucket/main.tf
    note: Module cũ, trivy báo lỗi HIGH
  - path: tests/fixtures/reference/main.tf
    note: Bản gốc của artifact-bucket để sinh đột biến
  - path: tests/test_module_tests_policy.py
    note: Không sửa
run:
  - docker compose -f setup/docker-compose.yml --profile devops up -d --wait localstack-devops
  - uv run pytest tracks/devops/modules/08-iac-provisioning/exercises/intermediate/04-module-tests-policy -q
---

## Mục tiêu

Viết test đơn vị cho module bằng `tofu test` với `mock_provider` (chạy không cần cloud) và đo chất lượng test bằng đột biến: test
tốt phải đỏ khi module bị làm hỏng. Dùng trivy làm policy-as-code chạy offline, sửa module theo kết quả quét thay vì tắt cảnh báo,
và dùng lại module tốt (composition) thay vì chép.

## Đề bài

Thư mục `starter/modules/` có hai module:

- `artifact-bucket/`: bucket có khoá KMS riêng (xoay khoá), versioning, mã hoá `aws:kms` bằng khoá đó, chặn public access, lifecycle
  xoá phiên bản cũ sau `noncurrent_days` (validation 1–365). Module này đúng; nó chưa có test.
- `upload-bucket/`: module cũ (biến `prefix`, `name`, output `bucket_name`), chỉ có bucket với mã hoá AES256. `trivy config` báo 5
  lỗi HIGH.

Việc của bạn:

1. Viết `artifact-bucket/tests/artifact_bucket.tftest.hcl`: `mock_provider "aws"`, khối `variables`, ít nhất 4 khối `run`. Test
   phải **đỏ** khi module bị một trong các đột biến sau, và xanh trên bản gốc:
   - versioning đổi sang `Suspended`;
   - mã hoá đổi sang `AES256` (không còn `aws:kms` với khoá của module);
   - bỏ validation của `noncurrent_days`;
   - một cờ public access block (`restrict_public_buckets`) thành `false`;
   - tắt xoay khoá KMS (`enable_key_rotation = false`).
2. Sửa `upload-bucket/` để `trivy config` không còn lỗi HIGH hay CRITICAL, giữ biến `prefix`, `name`, output `bucket_name` và tên
   bucket `<prefix>-<name>`. Không được dùng chú thích `trivy:ignore` hay `tfsec:ignore`.

**Cách test chấm.**

- `tofu test` chạy qua `TofuLab` (sandbox, provider từ mirror) trên module của bạn, trên bản gốc trong `tests/fixtures/reference`,
  và trên 5 bản đột biến của bản gốc; test của bạn được chép vào `tests/` của từng bản. Với mock provider, `tofu test` không gọi
  LocalStack.
- trivy (từ module 06) quét bản chép của `starter/modules/` trong sandbox với `--severity HIGH,CRITICAL --skip-check-update`
  (bộ kiểm có sẵn trong binary, không tải gì), `--config` và `--ignorefile` rỗng nên `trivy.yaml` hay `.trivyignore` trong thư mục
  bài không có tác dụng. Một test quét bản gốc của `upload-bucket` (`tests/fixtures/original-upload-bucket`) và đòi thấy
  `AWS-0086` và `AWS-0132`.
- Test tích hợp: một root (`tests/fixtures/root`) gọi cả hai module của bạn, apply thật trên `localstack-devops`, kiểm mã hoá KMS,
  versioning, public access block và xoay khoá bằng boto3.

Cả bài khoảng 3 phút (mỗi lần `tofu test` dựng một thư mục làm việc riêng).

## Tiêu chí đạt

- `tofu test` pass trên module của bạn với ít nhất 4 khối `run` pass, và pass trên bản gốc.
- Mỗi đột biến trong 5 đột biến làm `tofu test` của bạn fail.
- Tệp test có `mock_provider "aws"`.
- `trivy config` không còn lỗi HIGH/CRITICAL trong `starter/modules/`; không có chú thích `trivy:ignore`/`tfsec:ignore`.
- Apply hai module trên LocalStack: cả hai bucket mã hoá `aws:kms`, versioning `Enabled`, chặn đủ public access; khoá KMS của
  `reports` bật xoay khoá.

## Gợi ý

### Gợi ý 1

`run` mặc định `command = apply`; với mock provider, "apply" chỉ sinh giá trị giả cho thuộc tính computed nên vẫn chạy offline.
`command = plan` nhanh hơn nhưng thuộc tính computed (như `aws_kms_key.this.arn`) là unknown; muốn so mã hoá với ARN của khoá thì
dùng apply, hoặc đặt giá trị giả bằng `mock_resource "aws_kms_key" { defaults = { arn = "..." } }`. Kiểm validation bằng
`expect_failures = [var.noncurrent_days]` với giá trị ở cả hai phía của khoảng.

### Gợi ý 2

Các khối lồng như `rule` của mã hoá là **set**, không đánh chỉ số `[0]` được; duyệt bằng `for` trong `alltrue([...])`. Với
`upload-bucket`, cách gọn nhất là gọi `module "bucket" { source = "../artifact-bucket" ... }` rồi chuyển tiếp output: module tốt
được dùng lại, chuẩn bảo mật chỉ nằm một chỗ.
