# Câu hỏi phỏng vấn: IaC với OpenTofu và Terraform

## State dùng để làm gì? Nếu mất state thì sao?

State ánh xạ địa chỉ trong cấu hình (`module.storage.aws_s3_bucket.this["media"]`) sang đối tượng thật (bucket có tên và ID cụ
thể), lưu thuộc tính đã biết, phụ thuộc giữa tài nguyên, và `lineage`/`serial` để phát hiện ghi đè. Nhờ nó OpenTofu biết tài nguyên
nào là "của mình", tính được diff, biết thứ tự xoá, và không phải liệt kê toàn bộ tài khoản mỗi lần plan.

Mất state thì hạ tầng vẫn chạy nhưng OpenTofu coi như chưa có gì: plan đòi tạo mới mọi thứ (và lỗi vì tên trùng). Khôi phục: lấy
bản trước từ versioning của bucket state (lý do bật versioning), hoặc import lại từng tài nguyên bằng khối `import`. Phòng: backend
remote có versioning, quyền xoá hẹp, `state pull` trước mọi thao tác tay.

## `count` và `for_each` khác nhau thế nào? Khi nào dùng cái nào?

`count` tạo N bản, địa chỉ theo vị trí (`[0]`, `[1]`); `for_each` nhận map hay set, địa chỉ theo khoá (`["orders"]`). Với danh sách
có thể thay đổi, `count` nguy hiểm: bỏ phần tử ở giữa làm các phần tử sau trượt chỉ số, thuộc tính đổi theo, và thuộc tính
ForceNew (tên bucket) làm chúng bị thay thế. `for_each` chỉ đụng đúng khoá bị thêm hay bỏ.

Dùng `count` cho bật/tắt (`var.enabled ? 1 : 0`, hay `lifecycle { enabled }` của OpenTofu 1.11) hoặc N bản thật sự giống nhau.
Dùng `for_each` cho mọi thứ có danh tính. Khoá của `for_each` phải biết lúc plan, nên không dùng ID do apply sinh ra làm khoá.
Chuyển từ `count` sang `for_each` trên state có sẵn cần khối `moved` cho từng chỉ số.

## `sensitive = true` có giữ mật khẩu khỏi state không? Bạn bảo vệ secret trong IaC thế nào?

Không. `sensitive` chỉ làm CLI in `(sensitive value)` và lan sang mọi biểu thức dùng giá trị đó; giá trị vẫn được ghi rõ vào state
nếu gán vào thuộc tính thường, và `tofu output -json` vẫn in nó. Theo thứ tự ưu tiên:

1. Không đưa secret qua IaC: IaC tạo chỗ chứa (Secrets Manager, Vault) và quyền đọc; ứng dụng hay hệ thống xoay vòng sinh giá trị.
2. Khi IaC phải ghi secret: biến `ephemeral` + thuộc tính write-only (`value_wo`, `password_wo`), hay ephemeral resource đọc secret
   lúc chạy. Không bao giờ vào state hay plan. Đổi giá trị bằng `*_wo_version`.
3. Bảo vệ state: mã hoá phía client (khối `encryption` của OpenTofu với `aws_kms`), mã hoá phía server của backend, quyền đọc state
   hẹp như quyền đọc secret, mã hoá cả tệp plan.
4. Không bao giờ để secret trong `.tfvars` commit vào git; CI lấy từ secret store và đặt `TF_VAR_...`.

## Thay đổi nào sau đây tạo lại tài nguyên, và bạn biết bằng cách nào: đổi tag, đổi tên bucket, đổi tên khối resource?

- Đổi tag: update tại chỗ (`~`).
- Đổi tên bucket: thuộc tính ForceNew, plan in `-/+ destroy and then create replacement` và đánh dấu `# forces replacement` cạnh
  thuộc tính. Muốn giảm downtime với tài nguyên khác (không phải bucket có tên cố định) thì `create_before_destroy`.
- Đổi tên khối (`aws_s3_bucket.a` thành `aws_s3_bucket.b`): với OpenTofu là địa chỉ mới, nên destroy cái cũ và create cái mới, dù
  cấu hình giống hệt. Sửa bằng `moved`.

Cách biết luôn là đọc plan, hay đọc `tofu show -json tfplan` và lọc `change.actions` chứa `delete`. Trong CI, một guard chặn plan
xoá hay thay thế tài nguyên giữ dữ liệu trừ khi được cho phép rõ ràng.

## (Sự cố) Job CI báo `Error acquiring the state lock`, người giữ là một job chạy từ 2 giờ trước. Bạn làm gì?

1. Đọc `ID`, `Who`, `Operation`, `Created` trong lỗi; tìm job đó trong CI.
2. Xác minh nó đã chết hẳn: run đã kết thúc hay bị huỷ, runner không còn tiến trình `tofu`, không ai đang apply tay. Nếu nó **còn
   chạy** (apply dài, chờ API), đợi; mở khoá lúc này là hai bên cùng ghi state.
3. `tofu state pull > before-unlock.tfstate` để có bản sao, rồi `tofu force-unlock <ID>`.
4. `tofu plan` ngay: apply bị ngắt có thể đã tạo tài nguyên mà state chưa ghi (lỗi "already exists" lần sau, cần import), hay ghi
   state dở. Bucket state có versioning cho phép quay về bản trước nếu state hỏng.
5. Sau sự cố: vì sao job bị kill (timeout của runner ngắn hơn thời gian apply, runner spot bị thu hồi)? Đặt timeout hợp lý,
   `concurrency` cho job apply, `-lock-timeout` để job sau chờ thay vì lỗi ngay. Không bao giờ dùng `-lock=false` làm cách đi vòng.

## (Sự cố) Plan của một PR "chỉ refactor" báo `6 to add, 6 to destroy` cho các bucket có dữ liệu. Bạn xử lý thế nào?

Dấu hiệu: tên bucket ở nhóm destroy và nhóm create giống hệt nhau, chỉ khác địa chỉ (`exports[0]` và `exports["orders"]`). Đây là
thay đổi địa chỉ, không phải thay đổi hạ tầng: PR đổi `count` sang `for_each`, hay đổi tên khối, hay đưa vào module. Sửa bằng khối
`moved` cho từng địa chỉ (đọc `tofu state show` để biết chỉ số nào là bucket nào), plan lại phải ra `0 to add, 0 to destroy` và
`has moved to`. Không dùng `-target` từng bucket: vẫn destroy rồi create, chỉ chậm hơn.

Phòng lần sau: guard trong CI đọc plan JSON chặn delete trên bucket, bảng, khoá KMS; `prevent_destroy` cho tài nguyên dữ liệu ở prod;
quy ước "PR refactor phải kèm plan 0 add/0 destroy".

## Drift là gì? Bạn phát hiện và xử lý drift thế nào?

Drift là thực tế khác cấu hình vì ai đó (hay công cụ khác) sửa ngoài OpenTofu. `tofu plan` luôn refresh và đề xuất đưa thực tế về
cấu hình; `tofu plan -refresh-only` chỉ cho thấy thực tế khác state ở đâu mà không đề xuất sửa, `apply -refresh-only` chấp nhận thực
tế vào state.

Phát hiện liên tục: job theo lịch chạy `plan -detailed-exitcode` (mã 2 là có khác) cho từng stack, mở issue cho chủ stack. Xử lý
theo loại: sửa tay sai thì apply đưa về đúng; thuộc tính do công cụ khác quản (tag FinOps, số replica do autoscaler) thì
`ignore_changes` đúng thuộc tính đó, không cả khối; thay đổi khẩn cấp hợp lý thì đưa vào code trong 24 giờ. Phòng: quyền console
production chỉ đọc, thay đổi khẩn cấp qua một đường có ghi lại.

## `moved`, `import`, `removed` khác các lệnh `state mv`, `import`, `state rm` thế nào? Bạn chọn cái nào?

Kết quả giống nhau; khác ở quy trình. Khối trong cấu hình đi qua PR, xuất hiện trong plan (thấy trước "has moved to", "will be
imported", "will be forgotten"), và tự áp dụng ở **mọi** state khi plan lần tới: dev, staging, prod, và cả người dùng module của bạn.
Lệnh CLI sửa thẳng một state, không review, phải chạy tay đúng lúc trên từng môi trường; quên một môi trường là lệch.

Chọn khối trong code cho mọi thay đổi định kỳ. Lệnh CLI cho cứu hộ một lần (state hỏng, tách state), luôn kèm `state pull` sao lưu
trước. `import` block còn hỗ trợ `for_each` và `-generate-config-out` để viết nháp cấu hình; với `removed`, luôn
ghi rõ `lifecycle { destroy = false }` (bỏ quản lý) hay `destroy = true` (xoá thật): OpenTofu mặc định chỉ bỏ khỏi state (và cảnh
báo vì thiếu `lifecycle`), còn Terraform mặc định là destroy, nên cùng một khối không `lifecycle` cho hai kết quả ngược nhau.

## (Vì sao chọn công cụ này) Vì sao bạn chọn OpenTofu thay vì Terraform, hay ngược lại?

Chọn OpenTofu khi: muốn giấy phép mã nguồn mở thật (MPL, Linux Foundation) để không lo điều khoản BSL nếu sản phẩm của bạn có thể
bị coi là cạnh tranh, hay để xây nền tảng nội bộ trên nó; cần mã hoá state và plan phía client (yêu cầu tuân thủ, state chứa dữ liệu
nhạy cảm); muốn early evaluation (biến trong backend và nguồn module) để bớt wrapper; dùng TACOS hay pipeline tự dựng.

Chọn Terraform khi: tổ chức đã đầu tư vào HCP Terraform hay Enterprise (Sentinel, private registry, run task, workspace có quyền),
cần hỗ trợ thương mại của HashiCorp/IBM, hay phụ thuộc tính năng chỉ Terraform có (Stacks, `cloud` block). Kỹ năng chuyển qua lại
gần như hoàn toàn; tôi viết cấu hình không dùng tính năng riêng khi module dùng chung cho cả hai (tệp `.tofu` cho phần riêng của
OpenTofu).

So với CloudFormation hay CDK: tôi chọn chúng cho tổ chức chỉ dùng AWS muốn AWS giữ state và rollback stack; chọn OpenTofu khi đa
cloud hay quản cả GitHub, Cloudflare, Datadog bằng cùng quy trình.

## (Thiết kế) Thiết kế repo và pipeline IaC cho 3 môi trường, 3 tài khoản AWS, 5 kỹ sư.

- **Cấu trúc:** `modules/` (network, data-store, app-runtime, có `tofu test`, phát hành bằng tag) và `live/<env>/<stack>/`; mỗi thư
  mục lá là một root module có backend, provider, role và lock file riêng, chỉ gọi module có `ref=`. Không dùng CLI workspace cho
  môi trường lâu dài.
- **State:** bucket ở tài khoản shared, versioning, chặn public, `use_lockfile`, key `olist/<env>/<stack>.tfstate`, quyền theo prefix;
  mã hoá bằng khối `encryption` với `aws_kms` mỗi môi trường một khoá. Chia theo blast radius: data tách khỏi app.
- **Pipeline:** PR chạy fmt, validate, trivy, `tofu test`, `plan -out` cho stack bị đổi, đăng tóm tắt lên PR, guard chặn xoá tài
  nguyên dữ liệu; merge thì apply dev, rồi staging; prod qua environment có người duyệt, apply đúng tệp plan đã duyệt. OIDC, mỗi
  môi trường một role. `concurrency` theo stack.
- **Promotion:** nâng module bằng PR đổi `ref=` lần lượt dev, staging, prod.
- **Drift:** job hằng đêm `plan -detailed-exitcode` mỗi stack.
- **Secret:** write-only/ephemeral, không secret trong tfvars.

Đánh đổi chấp nhận: lặp vài dòng backend mỗi thư mục (sinh bằng script hay Terragrunt khi số thư mục lớn).

## Khi nào bạn dùng workspace của CLI, khi nào tách thư mục? Workspace của HCP Terraform có phải là một thứ không?

CLI workspace là nhiều state cho **cùng một** cấu hình trên **cùng** backend và credential, chọn bằng `workspace select`. Hợp cho bản
sao tạm giống hệt nhau: môi trường theo PR, thử nghiệm song song. Không hợp cho dev/staging/prod: không phân quyền được, không khác
version provider được, chọn nhầm là apply nhầm.

Workspace của HCP Terraform là thứ khác: một đơn vị có state, biến, quyền, lịch sử run và cấu hình VCS riêng, tương đương một thư mục
root của mô hình thư mục, gom vào project để gán quyền theo team. Đề Associate hay hỏi đúng sự khác biệt này.

## Bạn test một module OpenTofu thế nào?

Theo tầng, rẻ trước:

1. Tĩnh: `fmt -check`, `validate`, tflint, trivy/checkov trên mọi PR.
2. Contract: `validation`, `precondition`, `postcondition` trong module, chạy ở mọi plan của người dùng module.
3. Đơn vị: `tofu test` với `mock_provider` (không cần cloud, vài giây): mỗi `run` kiểm một hành vi, `expect_failures` cho validation.
   Đo chất lượng test bằng đột biến: làm hỏng module (tắt versioning, đổi mã hoá) và đòi test đỏ.
4. Tích hợp: `tofu test` với provider thật hay apply trên LocalStack/tài khoản sandbox, kiểm bằng API, destroy.
5. End-to-end: dựng môi trường tạm, chạy smoke test ứng dụng (Terratest), destroy; trước khi phát hành bản chính.

## Lock file `.terraform.lock.hcl` để làm gì? Có nên commit không?

Có. Nó ghi bản provider **đã chọn** và checksum của gói cho từng nền tảng. Ràng buộc `~> 6.12` trong `required_providers` chỉ nói
bản nào được phép; không có lock file, mỗi người và mỗi lần CI có thể nhận bản khác nhau, và một gói bị tráo trên registry sẽ không
bị phát hiện. Lên bản bằng `tofu init -upgrade`, review diff của lock file, chạy plan ở dev trước. Nhóm có nhiều hệ điều hành chạy
`tofu providers lock -platform=...` cho đủ checksum. Module dùng chung không commit lock file (root quyết định); root module thì có.

## Một kỹ sư đề xuất bỏ remote backend, commit `terraform.tfstate` vào git cho "đơn giản". Bạn trả lời thế nào?

Không. Git không khoá: hai người apply cùng lúc rồi merge sẽ làm mất thay đổi của một người, và merge conflict trên JSON state là
cách nhanh nhất làm hỏng state. State chứa mọi thuộc tính kể cả secret, nên commit state là đưa secret vào lịch sử git vĩnh viễn.
Người quên `git pull` trước khi apply sẽ apply trên state cũ. Backend `s3` với `use_lockfile`, versioning và mã hoá tốn vài dòng cấu
hình và một bucket; lợi ích về an toàn lớn hơn nhiều.
