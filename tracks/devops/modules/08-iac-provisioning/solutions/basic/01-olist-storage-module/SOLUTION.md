# Lời giải: module lưu trữ S3 và IAM cho Olist Shop

Lời giải nằm trong `infra/modules/olist-storage/` (root `infra/main.tf` giữ nguyên như starter).

## Các quyết định

- **`for_each` theo map, không `count`.** Địa chỉ `aws_s3_bucket.this["media"]` gắn với khoá, nên thêm hay bớt một bucket chỉ đụng
  đúng nó. Tài nguyên phụ (versioning, public access block) cũng `for_each` cùng khoá và tham chiếu `aws_s3_bucket.this[each.key]`.
- **Lọc bằng biểu thức `for` có `if`.** `local.versioned = { for k, v in var.buckets : k => v if v.versioning }`: bucket tắt
  versioning không có tài nguyên versioning nào (khác với `status = "Suspended"`, vốn là trạng thái riêng của S3 và không trả bucket
  về "chưa từng bật").
- **Validation ở module, không ở root.** Module là thứ được dùng lại; chặn đầu vào sai ở đó thì mọi root đều được bảo vệ.
  Validation của `services` tham chiếu `var.buckets` (cross-variable validation: Terraform từ 1.9; OpenTofu 1.13 của track chạy được, đã kiểm).
- **Policy sinh từ dữ liệu.** `data "aws_iam_policy_document"` với ba `dynamic "statement"` (đọc object, list bucket, ghi object),
  mỗi cái bỏ hẳn khi danh sách rỗng; không bao giờ có `s3:*` hay `Resource = "*"`.
- **ARN dựng từ tên, không từ tài nguyên.** Đây là chỗ dễ sai nhất. Nếu policy lấy `aws_s3_bucket.this[key].arn`, data source
  phụ thuộc cả tài nguyên `aws_s3_bucket.this`; khi thêm một bucket, tài nguyên đó có thay đổi đang chờ nên OpenTofu hoãn đọc data
  source tới lúc apply, JSON policy thành "known after apply" và plan báo **update mọi role policy** dù quyền không đổi. ARN của
  bucket S3 suy ra được từ tên (`arn:${partition}:s3:::${name}`), nên `local.names` và `local.arns` tách policy khỏi vòng đời
  bucket. `data "aws_partition"` giữ cấu hình đúng ở GovCloud hay Trung Quốc.
- **Tag chung một chỗ.** `local.tags` cho mọi tài nguyên. Ở repo thật có thể dùng `default_tags` của provider ở root; trong module
  thì không, vì module không nên khai báo provider.

## Đọc thêm

- Đổi tên một khoá trong `buckets` vẫn là destroy rồi create (tên bucket đổi). Đổi tên khoá mà giữ bucket thì thêm `moved`.
- Muốn module dùng được với nhiều account hay region: module không có khối `provider`, root truyền provider bằng `providers = {
  aws = aws.eu }`.
- Thứ tự tạo: IAM policy không còn phụ thuộc bucket, nên có thể được tạo trước bucket. IAM không kiểm resource tồn tại, nên không
  sao; nếu cần thứ tự (ví dụ bucket policy), dùng tham chiếu trực tiếp hoặc `depends_on`.
