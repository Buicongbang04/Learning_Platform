# Lời giải: import, moved, removed và drift

Lời giải: `infra/state.tf` (moved, import, removed), `infra/legacy.tf` (cấu hình của bucket import), và
`lifecycle { ignore_changes = [tags["cost-center"]] }` trong `infra/modules/documents/main.tf`.

## Vì sao từng khối

- **`moved`** cho 4 địa chỉ. OpenTofu so khớp state với cấu hình theo **địa chỉ**. `aws_s3_bucket.invoices` không còn trong cấu hình
  và `module.documents.aws_s3_bucket.this["invoices"]` chưa có trong state, nên không có `moved` thì plan là destroy cái cũ, create
  cái mới: bucket cũ bị xoá (bucket có object thì destroy lỗi giữa chừng, để state nửa vời), rồi tạo bucket rỗng cùng tên. `moved`
  được review trong PR và tự áp dụng ở mọi state khi plan; `tofu state mv` làm cùng việc nhưng bằng tay trên từng state.
- **`import`** với `id = "${var.prefix}-legacy-exports"`. Khối import đi qua plan (thấy trước kết quả), lặp lại được, và cho phép
  `for_each` khi nhập nhiều thứ. `tofu import` CLI ghi thẳng vào state, không qua review. Cấu hình phải **khớp** thực tế (tag
  `Owner = data-team`), nếu không plan sẽ import rồi update ngay. Cách nhanh: `tofu plan -generate-config-out=generated.tf`.
- **`removed`** với `lifecycle { destroy = false }`: action `forget`, bucket ở lại. Tương đương `tofu state rm`, nhưng có review.
  Ghi `lifecycle` tường minh: OpenTofu (1.13.2, đã thử) thiếu `lifecycle` thì mặc định cũng là forget và in cảnh báo "Missing
  lifecycle from the removed block", còn Terraform thiếu nó thì mặc định destroy. `destroy = true` nghĩa là xoá thật (và chạy
  provisioner `when = destroy` trong khối, OpenTofu 1.10).
- **`ignore_changes = [tags["cost-center"]]`**: chỉ bỏ qua đúng một khoá tag do công cụ khác quản. `ignore_changes = [tags]` sẽ
  che luôn drift của tag `Project` mà bạn quản.

## Drift: thấy, phân loại, xử lý

1. `plan -refresh-only` cho biết thực tế khác state chỗ nào, không đề xuất sửa. Mã 2 nghĩa là có khác. Lưu ý LocalStack và
   provider thật đôi khi báo khác biệt "thẩm mỹ" (giá trị mặc định được điền); đọc kỹ trước khi kết luận.
2. Phân loại từng thay đổi: **(a)** sửa tay sai (tắt versioning) → để plan thường đưa về đúng cấu hình; **(b)** thay đổi hợp lệ từ
   công cụ khác (tag FinOps) → `ignore_changes` đúng thuộc tính; **(c)** thay đổi hợp lệ nên trở thành cấu hình (ai đó tăng
   capacity khi sự cố) → sửa cấu hình cho khớp rồi `apply -refresh-only` hay plan không đổi gì.
3. Phòng: job theo lịch chạy `plan -detailed-exitcode` (hay `-refresh-only`) và mở issue khi mã 2; quyền console production chỉ đọc.

## Các lệnh state tương đương (khi cần làm tay)

```bash
tofu state list
tofu state show 'module.documents.aws_s3_bucket.this["invoices"]'
tofu state mv aws_s3_bucket.invoices 'module.documents.aws_s3_bucket.this["invoices"]'
tofu state rm aws_s3_bucket.scratch
tofu import aws_s3_bucket.legacy_exports devops-ex-xxxxxxxx-legacy-exports
tofu state pull > backup.tfstate
```

Luôn `state pull` ra một bản sao trước khi sửa state bằng tay; backend có versioning (S3) là lưới an toàn thứ hai. `state push`
chỉ dùng để khôi phục bản sao đó, và OpenTofu từ chối push khi lineage hay serial không khớp trừ khi `-force`.

## Postmortem mẫu (một đoạn)

Refactor đưa bucket vào module là thay đổi **chỉ về địa chỉ**; nó an toàn khi và chỉ khi plan không có create/delete. Quy ước team:
mọi PR refactor phải có khối `moved` và plan đính kèm với `0 to add, 0 to destroy`; tài nguyên tạo tay được nhận bằng khối
`import`, không bằng CLI.
