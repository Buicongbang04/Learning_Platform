# Lời giải: remote state trên S3 có khoá và mã hoá

Lời giải: `infra/encryption.tf` và `infra/backend.tf`.

## Quyết định

- **Mã hoá phía client (`encryption`) cộng `encrypt = true` của S3.** `encrypt = true` là mã hoá phía server: ai có quyền
  `s3:GetObject` vẫn đọc được state rõ. Khối `encryption` mã hoá trước khi gửi, nên người đọc bucket mà không có passphrase (hay
  quyền KMS) chỉ thấy `encrypted_data`. Áp cho cả `plan` vì tệp plan chứa giá trị nhạy cảm.
- **Key provider.** `pbkdf2` (passphrase) hợp cho bài và cho team nhỏ, passphrase nằm trong secret store của CI. Ở AWS thật, dùng
  `aws_kms` (`kms_key_id`, `key_spec = "AES_256"`): không ai cầm khoá, quyền giải mã là quyền IAM, có audit trong CloudTrail.
  Còn có `gcp_kms`, `azure_vault`, `openbao`, `external`.
- **`enforced = true`.** Cấm ghi state không mã hoá, kể cả khi ai đó thêm `method "unencrypted"`.
- **`use_lockfile = true`** thay vì `dynamodb_table`. Khoá bằng object `<key>.tflock` ghi có điều kiện; bớt một bảng và một quyền.
  Đang có bảng DynamoDB thì bật cả hai một thời gian, rồi bỏ bảng.
- **Key theo môi trường** (`olist/${var.environment}/platform.tfstate`), bucket theo prefix, đều bằng early evaluation. Với
  Terraform: để trống trong khối `backend` và truyền `tofu init -backend-config=env/staging.s3.tfbackend`.
- **Bucket state:** versioning bật (khôi phục bản trước khi state hỏng), chặn public, quyền ghi chỉ cho role apply, bucket không do
  chính stack này quản (con gà quả trứng): tạo bằng một stack bootstrap riêng hay bằng tay có ghi lại.

## Chuyển state và xoay khoá

```bash
tofu init -migrate-state
tofu state list
tofu plan
```

`init` thấy backend đổi và hỏi có chép state cũ sang không (`-force-copy` để trả lời có trong script). Sau khi chắc chắn, xoá
`terraform.tfstate` local còn sót. Thêm mã hoá cho state **cũ chưa mã hoá**: bước 1 `method "unencrypted" "migrate" {}` và
`fallback { method = method.unencrypted.migrate }` trong `state`, **không** `enforced`, apply một lần; bước 2 bỏ fallback, bật
`enforced`. Xoay passphrase: method mới làm chính, method cũ làm `fallback`, apply, rồi bỏ fallback. Biến môi trường
`TF_ENCRYPTION` cho đặt cấu hình mã hoá ngoài code (HCL hay JSON), hữu ích khi CI cấp khoá.

## Khoá bị kẹt: runbook

1. Đọc `ID`, `Who`, `Operation`, `Created` trong thông báo lỗi.
2. Xác nhận người giữ khoá đã dừng hẳn: job CI đó đã kết thúc hay bị huỷ, runner không còn tiến trình `tofu`, không ai đang apply.
3. `tofu force-unlock <ID>` (OpenTofu hỏi xác nhận; `-force` trong script).
4. `tofu plan` ngay: apply bị ngắt có thể đã tạo tài nguyên chưa ghi state (import lại) hay để lại state dở; backend có versioning
   cho phép lấy bản trước.
5. Ghi lại: vì sao job bị kill (timeout của runner ngắn hơn apply?), đặt `-lock-timeout` hợp lý cho CI, và `concurrency` cho job
   apply để hai job không cùng chạy.

Đừng bao giờ dùng `-lock=false` để "đi qua" một khoá mà bạn chưa xác minh.
