---
title: Module lưu trữ S3 và IAM cho Olist Shop với for_each và validation
level: basic
services: [localstack-devops]
files:
  - path: starter/infra/main.tf
    note: Root module đã nối sẵn, không sửa
  - path: starter/infra/modules/olist-storage/variables.tf
    note: Thêm validation
  - path: starter/infra/modules/olist-storage/main.tf
    note: Viết tài nguyên
  - path: starter/infra/modules/olist-storage/outputs.tf
    note: Trả map tên, ARN, role
  - path: tests/test_storage_module.py
    note: Không sửa
run:
  - docker compose -f setup/docker-compose.yml --profile devops up -d --wait localstack-devops
  - uv run pytest tracks/devops/modules/08-iac-provisioning/exercises/basic/01-olist-storage-module -q
---

## Mục tiêu

Viết một child module có giao diện rõ ràng (biến có kiểu, validation, output dạng map), dùng `for_each` để thêm hay bớt một
bucket chỉ đụng đúng tài nguyên của nó, và sinh IAM policy tối thiểu cho từng service từ dữ liệu đầu vào thay vì viết tay.

## Đề bài

Olist Shop cần các bucket S3 theo mục đích (ảnh sản phẩm, file export, hoá đơn) và một IAM role cho mỗi service (`api`,
`worker`) chỉ có đúng quyền nó cần. Root module `starter/infra/main.tf` đã gọi `module "storage"` và chuyển tiếp output; bạn viết
phần thân của `modules/olist-storage/`.

Giao diện của module (giữ đúng tên):

| Biến | Kiểu | Validation bắt buộc |
| --- | --- | --- |
| `prefix` | `string` | Không |
| `environment` | `string` | Chỉ `dev`, `staging`, `prod` |
| `buckets` | `map(object({ versioning = optional(bool, true) }))` | Mọi khoá khớp `^[a-z][a-z0-9-]{2,20}$` |
| `services` | `map(object({ read = optional(list(string), []), write = optional(list(string), []) }))` | Mọi khoá bucket trong `read` và `write` phải có trong `buckets` |

Tài nguyên:

- Mỗi khoá của `buckets` một `aws_s3_bucket` tên `<prefix>-<environment>-<khoá>`, gắn tag `Project = "olist-shop"`,
  `Environment = <environment>`, `ManagedBy = "opentofu"`.
- `aws_s3_bucket_versioning` (`Enabled`) chỉ cho bucket có `versioning = true`; bucket `versioning = false` không có tài nguyên
  versioning nào.
- `aws_s3_bucket_public_access_block` bật đủ 4 cờ cho mọi bucket.
- Mỗi khoá của `services` một `aws_iam_role` tên `<prefix>-<environment>-<service>`, trust policy cho
  `ecs-tasks.amazonaws.com`, kèm policy (inline hay managed) cấp **đúng** các quyền sau và không gì khác: với mỗi bucket trong
  `read`: `s3:GetObject` trên `<arn>/*` và `s3:ListBucket` trên `<arn>`; với mỗi bucket trong `write`: `s3:PutObject` trên
  `<arn>/*`.

Output: `bucket_names` (khoá → tên), `bucket_arns` (khoá → ARN), `role_names` (service → tên role).

**Cách test chấm.** Test chép `starter/infra` vào thư mục tạm, ghi `ci.auto.tfvars.json` (environment `staging`; bucket `media`,
`exports` có `versioning = false`, `invoices`; `api` đọc `media`, `invoices`, ghi `media`; `worker` đọc `exports`, ghi `exports`,
`invoices`), rồi chạy `tofu init` và `apply` qua `TofuLab`: `tofu` chạy trong sandbox, provider `hashicorp/aws` 6.12.0 lấy offline
từ mirror, mọi request đi tới `localstack-devops` (không bao giờ ra AWS thật), `prefix` là `devops-ex-<8 hex>` riêng của lần
chạy. Kết quả đọc lại bằng boto3 trên LocalStack. Khi xong, test chạy `tofu destroy` và xoá mọi thứ còn sót có tiền tố đó. Cả bài
khoảng 1 phút.

## Tiêu chí đạt

- `tofu fmt -check -recursive` và `tofu validate` sạch.
- Đúng 3 bucket với đúng tên; versioning `Enabled` ở `media`, `invoices` và không bật ở `exports`; 4 cờ public access block bật ở
  cả 3; tag chung có mặt.
- Mỗi role tin `ecs-tasks.amazonaws.com` và có đúng tập (action, resource) ở trên: không thừa (không `s3:*`, không `*`), không
  thiếu.
- Ba output đúng giá trị.
- Plan lần hai sau apply là `No changes`.
- Thêm bucket `reports` vào `buckets` thì plan chỉ có hành động `create` cho tài nguyên có khoá `"reports"`; không tài nguyên nào
  khác bị update, replace hay destroy (kể cả policy của role).
- Ba đầu vào sai bị chặn bằng validation (lỗi `Invalid value for variable`): `environment = "prd"`, khoá bucket `Media_Files`,
  service đọc bucket `khong-co` không có trong `buckets`.

## Gợi ý

### Gợi ý 1

`for_each` nhận map hay set; địa chỉ tài nguyên là `aws_s3_bucket.this["media"]` nên thêm khoá mới không đẩy chỉ số của ai.
Để lọc bucket có versioning dùng biểu thức `for` có `if`: `{ for k, v in var.buckets : k => v if v.versioning }`. Validation có
thể tham chiếu biến khác của cùng module (`var.buckets` trong validation của `var.services`), dùng `alltrue`, `flatten`, `contains`.

### Gợi ý 2

Policy sinh từ `data "aws_iam_policy_document"` với `dynamic "statement"` (bỏ statement khi danh sách rỗng). Nếu policy lấy ARN từ
`aws_s3_bucket.this[key].arn`, mỗi lần thêm bucket data source bị hoãn tới lúc apply (nó phụ thuộc một tài nguyên đang có thay đổi)
và plan báo update mọi policy. ARN của bucket S3 tính được từ tên (`arn:<partition>:s3:::<tên>`), nên dựng ARN từ một `local`
tên bucket, không phụ thuộc tài nguyên.
