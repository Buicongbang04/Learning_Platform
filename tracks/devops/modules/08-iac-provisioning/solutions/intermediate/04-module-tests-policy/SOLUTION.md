# Lời giải: tofu test với mock provider và chính sách trivy

Lời giải: `modules/artifact-bucket/tests/artifact_bucket.tftest.hcl` và `modules/upload-bucket/main.tf` (gọi lại
`artifact-bucket`). Các tệp khác của `artifact-bucket` giữ nguyên.

## Test đơn vị

- `mock_provider "aws"` thay provider thật: không credential, không mạng, không LocalStack. Thuộc tính computed nhận giá trị giả;
  `mock_resource "aws_kms_key" { defaults = { arn = ... } }` cố định ARN để so khớp được.
- Mỗi `run` kiểm **một hành vi** có tên rõ (`versioning_enabled`, `public_access_fully_blocked`...), để khi đỏ biết ngay cái gì
  hỏng. Run dùng `command = plan` khi chỉ cần giá trị từ cấu hình; `encrypted_with_module_key` dùng apply (mặc định) vì cần ARN.
- Validation kiểm cả hai biên (0 và 400) bằng `expect_failures = [var.noncurrent_days]`. Chỉ kiểm một phía thì đột biến đổi biên
  (`<= 3650`) lọt.
- Khối lồng kiểu set (`rule`, `apply_server_side_encryption_by_default`) không đánh chỉ số được: dùng `alltrue([for ...])`.

## Vì sao đo bằng đột biến

Test pass trên module đúng chưa nói lên gì: test rỗng cũng pass. Đột biến là các lỗi thật hay gặp (ai đó tắt versioning cho đỡ
tốn, đổi về AES256 vì quên quyền KMS, xoá validation "cho linh hoạt"). Test tốt phải đỏ với từng lỗi đó. Đây là cách review chất
lượng test của module dùng chung trước khi publish.

## Các tầng test của IaC

| Tầng | Công cụ | Chạy ở đâu | Bắt được |
| --- | --- | --- | --- |
| Tĩnh | `tofu fmt -check`, `tofu validate`, tflint, trivy/checkov | Mọi PR, vài giây | Cú pháp, kiểu, quy ước, cấu hình sai chính sách |
| Đơn vị | `tofu test` + `mock_provider`, `override_resource` | Mọi PR, vài giây | Logic của module: điều kiện, for_each, validation |
| Contract | `validation`, `precondition`, `postcondition` trong module | Mỗi lần plan | Người gọi truyền sai, giả định về môi trường sai |
| Tích hợp | `tofu test` với provider thật (`command = apply`) hay apply trên LocalStack | PR của module, vài phút | Tương tác thật với API: tên hợp lệ, quyền, mặc định của provider |
| End-to-end | Dựng môi trường tạm, chạy smoke test của ứng dụng, destroy | Trước khi phát hành module, theo lịch | Hệ thống chạy được thật |

## Chính sách bằng trivy

- `trivy config` có sẵn bộ kiểm Terraform/OpenTofu (AWS, GCP, Azure, Kubernetes) nhúng trong binary; `--skip-check-update` dùng
  bộ nhúng nên chạy offline. Bộ kiểm cập nhật nằm trên registry OCI (`trivy-checks`) khi có mạng.
- `upload-bucket` gốc thiếu public access block (AWS-0086, 0087, 0091, 0093) và không dùng khoá KMS do khách hàng quản (AWS-0132).
  Gọi `module "bucket" { source = "../artifact-bucket" }` sửa cả năm lỗi bằng một chỗ dùng chung; sau này siết chuẩn ở
  `artifact-bucket` là mọi nơi được hưởng.
- Ngoại lệ có thật thì ghi bằng `.trivyignore` hay chú thích `trivy:ignore:<ID>` **kèm lý do và hạn**, được review như code. Bài
  này cấm ngoại lệ để buộc sửa gốc.
- Các công cụ tương đương: checkov (Python, nhiều framework), KICS, Terrascan (ít được phát triển gần đây, kiểm trạng thái repo trước khi chọn), tflint (lint theo provider, có
  plugin AWS). Policy trên **plan JSON** (OPA/Conftest, Sentinel) thấy được giá trị sau khi tính, còn quét tĩnh thì không.
