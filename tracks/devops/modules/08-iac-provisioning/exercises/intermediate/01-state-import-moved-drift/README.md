---
title: Thao tác state - import tài nguyên có sẵn, refactor bằng moved, bỏ quản lý bằng removed, xử lý drift
level: intermediate
services: [localstack-devops]
files:
  - path: starter/infra/main.tf
    note: Root mới đã gọi module documents
  - path: starter/infra/modules/documents/main.tf
    note: Module mới (for_each)
  - path: tests/fixtures/v1/main.tf
    note: Cấu hình cũ đang chạy, test apply nó trước
  - path: tests/test_state_operations.py
    note: Không sửa
run:
  - docker compose -f setup/docker-compose.yml --profile devops up -d --wait localstack-devops
  - uv run pytest tracks/devops/modules/08-iac-provisioning/exercises/intermediate/01-state-import-moved-drift -q
---

## Mục tiêu

Thay đổi cách tổ chức cấu hình trên một state đang chạy mà không tạo lại tài nguyên nào: dời địa chỉ bằng `moved`, nhận tài nguyên
tạo tay bằng khối `import`, trả một tài nguyên cho team khác bằng `removed` mà không xoá nó; rồi phân biệt drift cần sửa với thay
đổi ngoài OpenTofu cần bỏ qua.

## Đề bài

Cấu hình đang chạy của Olist Shop là `tests/fixtures/v1/main.tf`: hai bucket `invoices`, `reports` (mỗi cái một
`aws_s3_bucket_versioning`) khai báo rời, và bucket `scratch`. Team đã viết lại thành `starter/infra/`: hai bucket đi vào module
`documents` với `for_each`. Ngoài ra:

- Team data đã tạo tay bucket `<prefix>-legacy-exports` (tag `Project = olist-shop`, `Owner = data-team`, versioning `Enabled`).
  Từ nay nó được quản bằng OpenTofu ở root với địa chỉ `aws_s3_bucket.legacy_exports` và
  `aws_s3_bucket_versioning.legacy_exports`.
- Bucket `scratch` được giao cho team data tự quản: bỏ khỏi state của bạn, **không** xoá.
- Công cụ FinOps tự gắn tag `cost-center` vào bucket. Tag này không thuộc cấu hình và không được bị xoá hay ghi đè.

Thêm vào `starter/infra/` (tệp mới như `state.tf`, `legacy.tf`, và sửa module nếu cần) để đạt các tiêu chí dưới. Không đổi địa chỉ
`module.documents`, `aws_s3_bucket.this`, `aws_s3_bucket_versioning.this` và các khoá `invoices`, `reports`.

**Cách test chấm.** Mọi bước chạy trên cùng một state qua `TofuLab`, trên `localstack-devops`:

1. Apply `tests/fixtures/v1`, rồi tạo bucket `legacy-exports` bằng boto3 (như ai đó tạo trên console).
2. Thay cấu hình bằng `starter/infra/` của bạn, `tofu init`, rồi `tofu plan -out` và `tofu show -json`. Plan có tạo hay xoá tài
   nguyên thì test **dừng, không apply** (không bao giờ apply một plan phá dữ liệu) và các bước sau báo lỗi.
3. Apply đúng plan đó, plan lại, đọc `tofu state list`.
4. Gây drift bằng boto3: thêm tag `cost-center = fin-42` vào `invoices`, tắt (Suspended) versioning của `reports`. Chạy
   `plan -refresh-only`, rồi plan thường, rồi apply.

Cả bài khoảng 1 phút.

## Tiêu chí đạt

- Plan ở bước 2 không có hành động `create` hay `delete` nào.
- Bốn địa chỉ trong module có `previous_address` đúng địa chỉ cũ (`aws_s3_bucket.invoices` → `module.documents.aws_s3_bucket.this["invoices"]`, tương tự cho `reports` và hai tài nguyên versioning).
- `aws_s3_bucket.legacy_exports` và `aws_s3_bucket_versioning.legacy_exports` được import (khối `import`) với hành động `no-op`:
  cấu hình khớp thực tế, không update.
- `aws_s3_bucket.scratch` có hành động `forget`, và sau apply bucket vẫn còn trên LocalStack.
- Sau apply, state đúng 6 địa chỉ (4 trong module, 2 legacy) và plan là `No changes`.
- Sau drift: `plan -refresh-only` báo có thay đổi (mã 2); plan thường chỉ có đúng một hành động là `update`
  `module.documents.aws_s3_bucket_versioning.this["reports"]`; apply xong versioning của `reports` bật lại và tag `cost-center`
  vẫn còn trên `invoices`.

## Gợi ý

### Gợi ý 1

`moved` dời được cả vào trong module: `to = module.documents.aws_s3_bucket.this["invoices"]`. Khối `import` nhận biểu thức cho
`id` (`"${var.prefix}-legacy-exports"`); id của `aws_s3_bucket_versioning` là tên bucket. Chưa biết viết cấu hình cho tài nguyên
import sao cho khớp? Chạy `tofu plan -generate-config-out=generated.tf` với khối `import` để OpenTofu viết nháp, rồi dọn lại.

### Gợi ý 2

`removed { from = ...; lifecycle { destroy = false } }` bỏ tài nguyên khỏi state mà không gọi API xoá; thiếu `destroy = false` thì
nó bị destroy. Thay đổi ngoài OpenTofu mà bạn chấp nhận (tag của công cụ khác) thì bỏ qua đúng phần đó bằng
`lifecycle { ignore_changes = [tags["cost-center"]] }`, không bỏ qua cả `tags`. Drift của versioning thì để plan sửa.
