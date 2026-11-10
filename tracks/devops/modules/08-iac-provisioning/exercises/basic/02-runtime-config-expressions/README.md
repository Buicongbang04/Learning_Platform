---
title: Cấu hình runtime của Olist Shop bằng biểu thức, template và custom condition
level: basic
services: [localstack-devops]
files:
  - path: starter/infra/versions.tf
    note: Không sửa
  - path: starter/infra/variables.tf
    note: Thêm validation, sensitive, ephemeral
  - path: starter/infra/main.tf
    note: Viết locals, data source, tài nguyên, check
  - path: starter/infra/outputs.tf
    note: Bốn output
  - path: starter/infra/templates/upstreams.conf.tftpl
    note: Template upstream Nginx
  - path: tests/test_runtime_config.py
    note: Không sửa
  - path: tests/fixtures/sensitive-only/main.tf
    note: Bản chỉ đánh dấu sensitive, test dùng để chứng minh phép kiểm secret
run:
  - docker compose -f setup/docker-compose.yml --profile devops up -d --wait localstack-devops
  - uv run pytest tracks/devops/modules/08-iac-provisioning/exercises/basic/02-runtime-config-expressions -q
---

## Mục tiêu

Biến một mô tả service gọn (map object) thành nhiều tài nguyên bằng `for`, `merge`, splat, `dynamic` và `templatefile`; chặn đầu
vào sai bằng validation, chặn trạng thái sai bằng precondition/postcondition, cảnh báo bằng `check`; và giữ mật khẩu khỏi state
bằng biến `ephemeral` cùng thuộc tính write-only.

## Đề bài

Biến `services` mô tả mỗi service của Olist Shop: `port`, `replicas`, `public` (mặc định `false`), `settings` (map chuỗi). Viết
cấu hình trong `starter/infra/` sao cho:

1. **Biến.** `environment` chỉ nhận `dev`, `staging`, `prod`. Mọi `port` trong `services` nằm trong 1024–65535 (validation).
   `db_password` là `sensitive = true` và `ephemeral = true`, validation dài ít nhất 16 ký tự. `expected_account_id` (mặc định
   `null`) giữ nguyên. `retention` là danh sách `{ prefix, days }`.
2. **Tham số thường.** Mỗi cặp khoá-giá trị trong `settings` của mỗi service thành một `aws_ssm_parameter` kiểu `String` tên
   `/<prefix>/<environment>/<service>/<KHOÁ>`. Dựng map phẳng bằng `for` lồng nhau và `merge(...)` (hay `flatten`), rồi `for_each`.
3. **Mật khẩu.** `aws_ssm_parameter` kiểu `SecureString` tên `/<prefix>/<environment>/db/password`, giá trị đưa qua thuộc tính
   write-only `value_wo` (kèm `value_wo_version`) từ `var.db_password`. Mật khẩu không được nằm trong state, output hay log.
4. **Template.** Bucket `<prefix>-<environment>-runtime-config` và object `nginx/upstreams.conf` có nội dung render từ
   `templates/upstreams.conf.tftpl` bằng `templatefile`, chỉ gồm service `public = true`, theo thứ tự tên, mỗi service đúng 3 dòng:

   ```text
   upstream api {
     server api:8000;
   }
   ```

   Object này có `precondition`: phải có ít nhất một service public.
5. **Lifecycle.** `aws_s3_bucket_lifecycle_configuration` cho bucket trên, một `rule` cho mỗi phần tử của `retention` bằng
   `dynamic "rule"`: `id = "expire-<prefix bỏ dấu / cuối>"`, `status = "Enabled"`, `filter { prefix }`, `expiration { days }`.
6. **Postcondition.** `data "aws_caller_identity"` có `postcondition`: khi `expected_account_id` khác `null` thì `account_id` phải
   bằng nó (chặn apply nhầm tài khoản).
7. **Check.** Khối `check` cảnh báo khi `environment = "prod"` mà có service `replicas < 2`; chỉ cảnh báo, không chặn.
8. **Output.** `parameter_names` (danh sách tên tham số String đã sắp xếp, lấy bằng splat), `public_services` (danh sách tên đã sắp
   xếp), `db_password_parameter` (tên tham số mật khẩu), `account_id`.

**Cách test chấm.** Test ghi `ci.auto.tfvars.json` (staging; `api` 8000, 2 replica, public, `LOG_LEVEL=info`, `WORKERS=4`; `worker`
9000, 1 replica, `QUEUE=orders`; `web` 3000, 2 replica, public; `retention` `nginx/` 30 ngày và `snapshots/` 7 ngày;
`expected_account_id = "000000000000"`, tài khoản của LocalStack), đặt `TF_VAR_db_password` như CI lấy từ secret store, rồi init và
apply qua `TofuLab` trên `localstack-devops`. Các phép kiểm đầu vào sai chạy `tofu plan` với một tệp tfvars ghi đè. Bài chạy
khoảng 2 phút.

## Tiêu chí đạt

- `tofu fmt -check -recursive` và `tofu validate` sạch.
- Đúng 3 tham số String với đúng giá trị; tham số mật khẩu là `SecureString` giải mã ra đúng mật khẩu.
- Mật khẩu không có trong `tofu state pull`, output của apply hay `tofu output`. Một test chạy bản chỉ đánh dấu `sensitive`
  (`tests/fixtures/sensitive-only`) và đòi phép kiểm này thấy mật khẩu trong state.
- `nginx/upstreams.conf` đúng từng byte như mẫu trên cho `api` và `web`.
- Hai rule lifecycle `expire-nginx` (30 ngày) và `expire-snapshots` (7 ngày).
- Bốn output đúng; plan lần hai `No changes`.
- `port` 80 hay 70000, mật khẩu dưới 16 ký tự: lỗi `Invalid value for variable`, và lỗi không in mật khẩu.
- Không service nào public: lỗi `Resource precondition failed`. `expected_account_id = "111111111111"`: lỗi
  `Resource postcondition failed`.
- `staging` không có cảnh báo `Check block assertion failed`; `prod` (worker 1 replica) có cảnh báo đó nhưng plan vẫn thành công.

## Gợi ý

### Gợi ý 1

`merge([for s, c in var.services : { for k, v in c.settings : "${local.base_path}/${s}/${k}" => v }]...)`: dấu `...` trải danh
sách map thành các đối số của `merge`. Splat `[*]` áp lên danh sách, nên với tài nguyên `for_each` (một map) dùng
`values(aws_ssm_parameter.setting)[*].name`. Template dùng `%{ for name, svc in services ~}` ... `%{ endfor ~}`; dấu `~` cắt dòng
trống thừa.

### Gợi ý 2

`sensitive` chỉ che giá trị khi in; giá trị vẫn được ghi vào state nếu bạn gán vào thuộc tính thường như `value`. Biến
`ephemeral` không bao giờ được lưu vào state hay plan, và OpenTofu chỉ cho dùng nó ở chỗ cũng không lưu: thuộc tính write-only
(`value_wo`), provider, khối `ephemeral`. Đổi `value_wo_version` khi muốn ghi mật khẩu mới. Điều kiện dùng `self` chỉ có trong
`postcondition`; `precondition` kiểm trước khi tạo.
