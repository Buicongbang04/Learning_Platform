# Lời giải: ôn thi Associate và OpenTofu khác Terraform

| Câu | Đáp án | Ý chính |
| --- | --- | --- |
| `lock-file-role` | c. 6.12.0 | Lock file giữ bản đã chọn; `init -upgrade` mới chọn lại trong ràng buộc |
| `count-vs-for-each` | d. Thay thế chỉ số 1, xoá chỉ số 2 | `count` gắn địa chỉ với vị trí; `for_each` gắn với khoá |
| `data-vs-resource` | a. `data "aws_vpc"` | Đọc thứ người khác quản; không đưa vào state của mình |
| `refresh-only` | c. `plan -refresh-only` | Chỉ so thực tế với state, không đề xuất sửa hạ tầng |
| `rename-without-recreate` | a. Khối `moved` | Refactor đi qua review, chạy ở mọi môi trường |
| `sensitive-in-state` | d. Vẫn nằm rõ trong state | `sensitive` chỉ che output; dùng write-only, `ephemeral`, bảo vệ state |
| `lock-stuck` | c. Xác nhận rồi mới force-unlock | Mở khoá khi còn tiến trình ghi là hỏng state |
| `s3-native-lock` | b. `<key>.tflock` bằng PUT có điều kiện | OpenTofu 1.10, Terraform 1.11; không cần DynamoDB |
| `tofu-only-features` | a, b, d | Encryption, early evaluation, `-exclude`, provider `for_each` |
| `workspaces-vs-dirs` | d. Thư mục mỗi môi trường | Khác tài khoản, người duyệt, version: cần ranh giới thật |
| `hcp-terraform` | c. Policy set | Sentinel/OPA chạy giữa plan và apply |
| `tool-choice` | b. AWS CDK | Một cloud, TypeScript, construct cấp cao, AWS giữ state |
| `plan-encryption-ci` | a. Plan chứa giá trị nhạy cảm | Mã hoá plan, hạn giữ ngắn, quyền đọc hẹp |

## Giải thích từng câu

### `lock-file-role`: lock file thắng

`version = "~> 6.0"` là **ràng buộc**: các bản được phép. `.terraform.lock.hcl` là **lựa chọn** đã ghi lại cùng checksum (`h1:`,
`zh:`) của từng nền tảng. `init` khi có lock file luôn cài đúng bản đã khoá nếu nó thoả ràng buộc; muốn lên 6.20.0 thì chạy
`tofu init -upgrade`, xem diff của lock file trong PR, chạy plan ở dev trước. Phương án (a) là cách hoạt động khi **không** có
lock file. Không có mâu thuẫn (b) vì 6.12.0 thoả `~> 6.0`; mâu thuẫn chỉ xảy ra khi ràng buộc loại trừ bản đã khoá, lúc đó
`init` báo lỗi và đòi `-upgrade`. Xoá `.terraform` (d) không đụng lock file.

### `count-vs-for-each`: địa chỉ theo vị trí hay theo khoá

Với `count`, địa chỉ là `aws_s3_bucket.exports[0]`, `[1]`, `[2]`. Bỏ `payments` (vị trí 1) thì `reviews` trượt từ `[2]` xuống
`[1]`: tên bucket của `[1]` đổi từ `...-payments` thành `...-reviews`, mà `bucket` là thuộc tính buộc thay thế, nên `[1]` bị
destroy rồi create, còn `[2]` bị destroy. Kết quả: mất dữ liệu của cả `payments` lẫn `reviews` cũ. `for_each = toset(...)` gắn
địa chỉ với khoá (`exports["reviews"]`), bỏ một khoá chỉ xoá đúng khoá đó. Chuyển từ `count` sang `for_each` trên state có sẵn cần
khối `moved` (bài Intermediate 03).

### `data-vs-resource`: đọc, đừng chiếm

Khai báo `resource` (b) nghĩa là state của bạn sẽ quản vòng đời VPC: nếu VPC đã có, apply cố tạo cái mới. Import (c) đưa VPC vào
**hai** state, hai bên sẽ giành nhau sửa, và một bên destroy là mất VPC của mọi người. Data source đọc thuộc tính lúc plan, không
ghi vào danh sách tài nguyên được quản. Lựa chọn khác cùng tinh thần: `terraform_remote_state` đọc output của state kia (cần quyền
đọc cả state, nên nhiều tổ chức publish ID qua SSM Parameter Store và đọc bằng `data "aws_ssm_parameter"`). Chép cứng ID (d) làm
cấu hình hỏng lặng lẽ khi VPC đổi.

### `refresh-only`: nhìn drift mà không sửa

`plan -refresh-only` đọc lại mọi tài nguyên, so với state và in "Objects have changed outside of OpenTofu"; `apply -refresh-only`
ghi nhận thay đổi đó vào state mà không đụng hạ tầng. `plan` thường sẽ **đề xuất sửa** hạ tầng về đúng cấu hình. `-refresh=false`
(a) bỏ qua bước đọc, ngược với điều cần. `state rm` rồi `import` (b) là thao tác sửa state, không phải xem drift. `validate` (d)
không gọi provider.

### `rename-without-recreate`: `moved` là refactor có review

Khối `moved { from = aws_s3_bucket.assets; to = module.storage.aws_s3_bucket.this["assets"] }` nằm trong code, được review, và
mỗi môi trường tự áp dụng khi plan lần tới (plan in "has moved to"). `state mv` (b) đúng về kết quả nhưng phải chạy tay trên mọi
state, đúng thời điểm, không có review, và rất dễ quên một môi trường. `prevent_destroy` (c) chỉ làm plan lỗi chứ không đổi địa
chỉ. Giữ khối `moved` ít nhất tới khi mọi state đã áp dụng; với module dùng chung, giữ lâu hơn vì người dùng module có thể nâng
bản muộn.

### `sensitive-in-state`: che không phải mã hoá

`sensitive = true` làm CLI in `(sensitive value)` thay cho giá trị, và lan sang mọi biểu thức dùng nó. Giá trị vẫn được ghi rõ vào
state vì provider cần nó để so sánh lần sau. Ba lớp bảo vệ: (1) không lưu: biến `ephemeral` + thuộc tính write-only (`value_wo`,
OpenTofu 1.11, Terraform 1.11) hay ephemeral resource đọc secret lúc chạy; (2) mã hoá state: khối `encryption` của OpenTofu, hay
mã hoá phía server của backend (SSE-KMS); (3) quyền đọc state hẹp vì người đọc được state là đọc được mọi secret còn trong đó.

### `lock-stuck`: force-unlock là phẫu thuật

Thông tin khoá (ID, Who, Operation, Created) cho biết ai đang giữ. Trước khi mở: chắc chắn job đó đã chết hẳn (runner đã dừng,
không còn tiến trình `tofu`), nếu không hai bên cùng ghi state và state hỏng. Sau khi mở, chạy `plan` ngay: apply bị kill giữa
chừng có thể đã tạo tài nguyên mà state chưa ghi (lúc đó cần `import`) hoặc ghi state dở. `-lock=false` (b) bỏ qua khoá cho đúng
lần chạy đó, đúng kiểu hành vi gây ra state hỏng. Khoá không tự hết hạn.

### `s3-native-lock`: khoá bằng chính S3

Từ OpenTofu 1.10 (Terraform 1.11, thử nghiệm từ 1.10), backend `s3` với `use_lockfile = true` ghi object `<key>.tflock` bằng PUT có điều kiện
`If-None-Match: *`: người thứ hai nhận `412 PreconditionFailed` và báo không lấy được khoá. Không cần bảng DynamoDB; `dynamodb_table`
vẫn chạy nhưng đã deprecated ở cả hai công cụ. Có thể bật cả hai trong lúc chuyển đổi.

### `tofu-only-features`: a, b, d

- (a) Mã hoá state và plan phía client (khối `terraform { encryption { ... } }`, OpenTofu 1.7) không có ở Terraform; Terraform chỉ
  dựa vào mã hoá của backend.
- (b) Early evaluation (OpenTofu 1.8) cho dùng biến và local trong `backend`, `source`/`version` của module và `encryption`.
  Terraform đòi giá trị cố định hay `-backend-config`.
- (d) `-exclude` (1.9) và `for_each` trên provider (1.9) chỉ có ở OpenTofu.
- (c) `moved` có ở Terraform từ 1.1; (e) khối `import` có ở Terraform từ 1.5. Hai thứ này đều có thể ra trong đề thi.

### `workspaces-vs-dirs`: ranh giới thật cần thư mục

CLI workspace dùng chung backend, provider, version và bộ quyền; khác nhau chỉ ở state. Khi môi trường khác tài khoản, khác người
duyệt, khác bản provider trong lúc nâng cấp, workspace không biểu diễn được và chọn nhầm workspace là apply nhầm prod. Thư mục
riêng cho mỗi môi trường có backend, quyền, lock file riêng, cùng gọi module có version. Workspace hợp với môi trường tạm giống
hệt nhau (môi trường theo PR). Nhánh git dài hạn (c) làm các môi trường trôi xa nhau. (Workspace của HCP Terraform là khái niệm
khác: mỗi workspace có biến, quyền, lịch sử run riêng, gần với "một thư mục" hơn.)

### `hcp-terraform`: policy as code

HCP Terraform (trước là Terraform Cloud) chạy plan, rồi **policy check** (Sentinel hay OPA, gom trong policy set gắn vào
organization, project hay workspace), rồi mới cho apply; policy mức hard-mandatory chặn hẳn. Run task gọi dịch vụ ngoài (quét bảo
mật, ước tính chi phí) ở cùng chỗ. Private registry (b) chia sẻ module, không chặn plan. Variable set (d) chia sẻ biến. OpenTofu
không có HCP; tương đương là TACOS (Spacelift, env0, Scalr, Harness) hay CI tự dựng với trivy/OPA trên plan JSON.

### `tool-choice`: CDK hợp ràng buộc này

Một cloud, kỹ sư viết TypeScript, muốn construct cấp cao (L2/L3) đóng gói sẵn best practice, chấp nhận CloudFormation giữ state:
AWS CDK khớp từng ràng buộc. OpenTofu (a) mạnh khi đa cloud hay quản cả dịch vụ ngoài AWS (GitHub, Datadog), nhưng phải tự quản
state và tự viết module. Pulumi (d) cũng dùng TypeScript và đa cloud, nhưng tự host backend là thêm việc vận hành mà team 3 người
không cần. Ansible (c) là configuration management, không giữ state hạ tầng.

### `plan-encryption-ci`: plan là dữ liệu nhạy cảm

Tệp plan chứa cấu hình, giá trị biến và một phần state, kể cả giá trị `sensitive`. Artifact CI thường đọc được bởi mọi người có
quyền đọc repo. OpenTofu mã hoá plan bằng khối `plan` trong `encryption` (dùng cùng hay khác key provider với state); Terraform thì
không, nên phải hạn chế artifact. Thêm: hạn giữ ngắn (vài giờ), chỉ job apply được tải, apply đúng plan đã duyệt chứ không plan lại.
