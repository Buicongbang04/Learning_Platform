# Lời giải: PR refactor đòi xoá và tạo lại bucket export

Lời giải: `infra/moved.tf` (6 khối `moved`) và `ci/plan-guard.sh`. `infra/main.tf` giữ nguyên như PR.

## Nguyên nhân gốc

Production tạo bucket bằng `count`, nên state ghi địa chỉ **theo vị trí**: `aws_s3_bucket.exports[0]`, `[1]`, `[2]`. PR đổi sang
`for_each` trên một set, địa chỉ mới **theo khoá**: `aws_s3_bucket.exports["orders"]`... OpenTofu so khớp state với cấu hình theo
địa chỉ, không theo tên bucket, nên với nó `exports[0]` "không còn trong cấu hình" (destroy) và `exports["orders"]` "chưa có trong
state" (create). Tên bucket giống nhau trong cả hai nhóm chính là manh mối: không có gì thật sự đổi ngoài địa chỉ.

- `tofu validate` không bắt được vì cấu hình mới hợp lệ; validate không đọc state.
- `-target` từng bucket chỉ chia nhỏ cùng một thảm hoạ: mỗi lần vẫn destroy rồi create, mất dữ liệu export; còn để state ở trạng
  thái nửa cũ nửa mới.
- Sự cố tháng trước cùng gốc: với `count`, bỏ phần tử ở giữa làm mọi phần tử sau trượt chỉ số, tên của `[1]` đổi thành tên của
  `reviews`, thuộc tính `bucket` buộc thay thế nên `reviews` bị tạo lại. Đó chính là lý do đúng để chuyển sang `for_each`.

## Sửa

```hcl
moved {
  from = aws_s3_bucket.exports[0]
  to   = aws_s3_bucket.exports["orders"]
}
```

Một khối cho mỗi chỉ số của cả `aws_s3_bucket` và `aws_s3_bucket_versioning` (6 khối). Thứ tự phần tử phải khớp danh sách cũ
(`orders`, `payments`, `reviews`): đọc `tofu state show 'aws_s3_bucket.exports[1]'` để chắc bucket nào ở chỉ số nào thay vì đoán.
Plan sau đó in `has moved to` cho từng địa chỉ và `0 to add, 0 to change, 0 to destroy`. Giữ các khối `moved` trong repo ít nhất
tới khi mọi môi trường đã apply.

Cách khác: `tofu state mv 'aws_s3_bucket.exports[0]' 'aws_s3_bucket.exports["orders"]'` trên từng state; đúng, nhưng làm tay,
không review, dễ sót môi trường. Không nên: `lifecycle { prevent_destroy = true }` một mình, vì nó chỉ biến plan nguy hiểm thành
plan lỗi chứ không sửa địa chỉ (nhưng nên có cho bucket dữ liệu như một lớp phòng thủ, kèm guard bên dưới).

## Guard trong CI

`ci/plan-guard.sh` đọc `tofu show -json tfplan`, lọc `resource_changes` có `type` thuộc danh sách tài nguyên giữ dữ liệu và
`change.actions` chứa `delete` (gồm cả thay thế `["delete","create"]` và `["create","delete"]`), trừ địa chỉ trong
`ALLOW_DESTROY`, in ra và thoát 1. Danh sách cho phép đọc bằng `jq -n --arg list "$ALLOW_DESTROY" '$list | split(" ")'`: không để
shell tách chữ hay mở rộng glob trên `exports["payments"]`. Trong pipeline, guard chạy sau `plan -out` và trước bước approve;
`ALLOW_DESTROY` đặt từ label hay mô tả PR đã được duyệt, không từ biến tự do.

Bản chính sách đầy đủ hơn: OPA/Conftest trên plan JSON, hay policy set của HCP Terraform (Sentinel), hay run task của TACOS.

## Postmortem mẫu

- **Tác động:** không có (plan bị chặn ở review). Nguy cơ: mất 3 bucket export, BI không có số liệu.
- **Nguyên nhân gốc:** đổi `count` sang `for_each` đổi địa chỉ state; thiếu `moved`.
- **Vì sao lọt tới review:** CI không có bước nào hiểu plan; reviewer phải tự đọc 300 dòng.
- **Hành động:** guard chặn xoá tài nguyên dữ liệu trong CI; quy ước "PR refactor phải có plan 0 add/0 destroy"; `prevent_destroy`
  cho bucket dữ liệu ở prod; tài liệu nội bộ về `count` và `for_each`.
