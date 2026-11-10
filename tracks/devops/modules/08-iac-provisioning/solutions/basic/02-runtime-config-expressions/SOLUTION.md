# Lời giải: cấu hình runtime bằng biểu thức, template và custom condition

Lời giải nằm trong `infra/`.

## Từng yêu cầu

| Yêu cầu | Cách làm | Vì sao |
| --- | --- | --- |
| Tham số String | `merge([for s, c in var.services : { for k, v in c.settings : "${base}/${s}/${k}" => v }]...)` rồi `for_each` | Map phẳng, khoá là tên tham số: thêm bớt một setting chỉ đụng đúng nó |
| Mật khẩu | `value_wo = var.db_password`, `value_wo_version = 1`, biến `sensitive` và `ephemeral` | Không lưu vào state, plan; đổi mật khẩu bằng cách tăng `value_wo_version` |
| Template | `templatefile("${path.module}/templates/upstreams.conf.tftpl", { services = local.public_services })` | Logic hiển thị nằm trong template, dữ liệu lọc trong `locals` |
| Lifecycle | `dynamic "rule"` trên `var.retention`, `trimsuffix(prefix, "/")` cho `id` | Số rule theo dữ liệu, không lặp khối |
| Precondition | Trên `aws_s3_object.upstreams`: `length(local.public_services) > 0` | Chặn trước khi tạo một tệp cấu hình rỗng làm Nginx không khởi động |
| Postcondition | Trên `data.aws_caller_identity`: `var.expected_account_id == null \|\| self.account_id == var.expected_account_id` | Chặn plan khi credential trỏ nhầm tài khoản |
| Check | `check "prod_redundancy"` với `assert` | Cảnh báo, không chặn: chính sách mềm |
| Output | `sort(values(aws_ssm_parameter.setting)[*].name)` | Splat trên danh sách giá trị của map tài nguyên |

## Chọn loại điều kiện nào

- **Validation** của biến: kiểm **đầu vào**, chạy sớm nhất, thông báo cho người gọi module. Không thấy tài nguyên.
- **Precondition**: kiểm giả định **trước** khi tạo hay đọc một tài nguyên/data source/output, dùng được giá trị của tài nguyên khác.
- **Postcondition**: kiểm **kết quả** (có `self`) sau khi tạo hay đọc; lỗi thì chặn các tài nguyên phụ thuộc. Hay dùng cho data
  source: "AMI tìm được phải là arm64", "tài khoản phải đúng".
- **`check`**: kiểm điều kiện toàn cục, chỉ **cảnh báo**, chạy ở mọi plan và apply; có thể chứa một data source lồng để kiểm sức
  khoẻ (gọi endpoint HTTP sau khi deploy). Hợp cho chính sách mềm và giám sát liên tục.

## Secret: ba mức

1. `sensitive = true`: che khi in. Giá trị vẫn trong state nếu gán vào thuộc tính thường. Test dùng
   `tests/fixtures/sensitive-only` để chứng minh điều này.
2. Biến `ephemeral` + thuộc tính write-only: không bao giờ lưu. Provider nhận giá trị lúc apply rồi quên; OpenTofu ghi
   `value_wo = null` trong state. Giá trị không đọc lại được nên provider không phát hiện drift của nó; đổi mật khẩu bằng
   `value_wo_version`.
3. Không đưa secret qua OpenTofu: ứng dụng đọc thẳng từ Secrets Manager hay Vault, OpenTofu chỉ tạo "chỗ chứa" và quyền đọc.
   Đây thường là lựa chọn tốt nhất cho secret xoay vòng.

## Lỗi thường gặp

- Dùng `value = var.db_password` với biến `ephemeral`: OpenTofu báo lỗi vì giá trị ephemeral không được vào thuộc tính lưu state.
- Viết `values(aws_ssm_parameter.setting).*.name` (splat cũ) vẫn chạy nhưng là cú pháp legacy; `[*]` là chuẩn.
- Quên `~` trong `%{ for ... ~}` sinh dòng trống thừa, test so từng byte sẽ fail.
