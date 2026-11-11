# Câu hỏi phỏng vấn: Cloud và serverless

## IAM quyết định một request thế nào khi có identity policy, resource policy, permissions boundary và SCP?

Mọi policy liên quan được đánh giá cùng lúc. Có `Deny` khớp ở bất kỳ đâu thì từ chối. Không có thì request phải được cho phép trong mọi lớp chặn
áp dụng: SCP của Organization (trần của cả tài khoản), permissions boundary (trần của principal), session policy (trần của phiên), và phải có ít
nhất một `Allow` từ identity policy (hay resource policy). Không có `Allow` nào thì từ chối ngầm định.

Hai điểm hay hỏi tiếp: SCP và boundary **không cấp quyền**, chỉ giới hạn; quyền hiệu lực là phần giao. Resource policy trong cùng tài khoản có thể
tự cho phép principal mà không cần identity policy; khác tài khoản thì cả hai phía đều phải cho phép. Câu trả lời tốt kèm ví dụ: role có
`s3:*` trong identity policy, boundary chỉ cho `s3:GetObject`, thì role chỉ đọc được.

## Trust policy khác permission policy thế nào? Confused deputy là gì và chống thế nào?

Permission policy: role làm được gì. Trust policy: ai được assume role. Hai nửa này cùng quan trọng; trust policy lỏng (tin `"AWS": "*"`, tin cả
`ec2.amazonaws.com` khi chỉ ECS cần) biến permission policy chặt thành vô nghĩa.

Confused deputy: một bên có quyền (dịch vụ AWS, hay SaaS bên thứ ba) bị người khác lừa dùng quyền đó cho họ, ví dụ khách hàng khác bảo dịch vụ
"ghi log vào bucket của tài khoản X". Chống bằng điều kiện `aws:SourceAccount`, `aws:SourceArn` trong trust policy hay resource policy khi
principal là service, và `sts:ExternalId` khi cho bên thứ ba assume role chéo tài khoản.

## Bạn giao cho các team quyền tự tạo IAM role cho service của họ. Làm sao để họ không tự leo thang thành admin?

Permissions boundary. Admin tạo một managed policy làm trần (chỉ dịch vụ team được dùng, chỉ tài nguyên có tiền tố của team, không IAM), rồi cho
team `iam:CreateRole`, `iam:PutRolePolicy`, `iam:AttachRolePolicy` với điều kiện `iam:PermissionsBoundary` bằng ARN của trần đó, và cấm
`iam:DeleteRolePermissionsBoundary`, sửa chính boundary policy. Mọi role team tạo đều mang boundary; viết policy rộng đến đâu thì quyền hiệu lực
vẫn bị chặn. Thêm SCP ở mức tài khoản cho những điều không ai được làm (tắt CloudTrail, dùng region lạ). `iam:PassRole` cũng cần giới hạn theo
tiền tố role, nếu không team truyền được một role mạnh hơn cho Lambda của họ.

## Thiết kế mạng cho một web app ba tầng trên AWS. Subnet, route, security group, NACL đặt thế nào?

VPC một dải `/16`, ba tầng mỗi tầng một subnet mỗi AZ (ít nhất hai AZ). Public: route mặc định tới Internet gateway, chứa ALB và NAT gateway.
App: route mặc định tới NAT (đi ra được, không ai từ ngoài vào), chứa container hay instance. DB: không route ra ngoài VPC, chứa RDS qua DB subnet
group. Security group xâu chuỗi: ALB nhận 443 từ Internet; app nhận cổng app chỉ từ security group của ALB; DB nhận 5432 chỉ từ security group của
app. NACL để mặc định hoặc chỉ chặn thô, vì stateless và dễ quên cổng ephemeral.

Nói thêm được điểm chi phí và sẵn sàng: một NAT mỗi AZ cho production (NAT chết thì AZ đó mất đường ra); VPC endpoint cho S3, DynamoDB để không
trả tiền NAT; IPv4 public tính tiền theo giờ.

## Security group và NACL khác nhau ở đâu? Khi nào dùng NACL?

Security group: gắn network interface, stateful, chỉ allow, tham chiếu được security group khác, đánh giá mọi rule. NACL: gắn subnet, stateless
(phải mở cả chiều về, thường là cổng 1024-65535), có allow và deny, đánh giá theo số thứ tự rule đầu tiên khớp. Dùng NACL khi cần chặn một dải IP ở
mức subnet (deny list sau một đợt tấn công), làm lớp thứ hai theo yêu cầu tuân thủ, hay cô lập hẳn một subnet. Lỗi hay gặp: NACL chặn cổng
ephemeral nên kết nối ra ngoài "treo" không rõ lý do.

## Cold start của Lambda là gì, khi nào đáng lo và giảm thế nào?

Cold start là thời gian dựng môi trường thực thi mới: tải code, khởi động runtime, chạy code cấp module. Xảy ra khi chưa có môi trường rảnh: lần
đầu, sau khi deploy, khi concurrency tăng. Đáng lo với API đồng bộ cần p99 thấp; không đáng lo với xử lý hàng đợi.

Giảm bằng: gói nhỏ và ít dependency, import lười phần hiếm dùng, khởi tạo client một lần ở cấp module, runtime nhẹ (Python, Node), arm64. Khi vẫn
không đủ: provisioned concurrency (trả tiền giữ môi trường sẵn, có thể theo lịch) hay SnapStart. Câu trả lời tốt nói được khi nào không cần
Lambda: API tải đều cao chạy container thì không có cold start và rẻ hơn.

## SQS gửi message hai lần, Lambda của bạn cộng tiền hai lần. Thiết kế lại thế nào?

Chấp nhận at-least-once và làm handler idempotent. Khoá là khoá nghiệp vụ (`payment_id`), không phải `messageId` vì message gửi lại có ID mới. Ghi
khoá và tác dụng phụ trong một thao tác nguyên tử: DynamoDB `TransactWriteItems` gồm `Put` khoá với `attribute_not_exists` và `Update ADD` số dư,
hay `INSERT ... ON CONFLICT DO NOTHING` cùng transaction trong Postgres. Khoá có TTL dài hơn thời gian event có thể quay lại.

Đi kèm: `ReportBatchItemFailures` để một record lỗi không kéo cả batch chạy lại; visibility timeout ít nhất 6 lần timeout của function; DLQ sau
vài lần nhận; alarm khi DLQ có message. FIFO và `MessageDeduplicationId` chỉ chống trùng 5 phút phía SQS, không thay được idempotency.

## Sự cố: sau khi đổi role cho Lambda bằng OpenTofu, function báo lỗi khi đọc secret, còn deploy bằng tay hôm trước chạy tốt. Bạn điều tra thế nào?

Đọc thông báo lỗi đầy đủ: `AccessDeniedException` nói rõ principal, action, resource. Rồi kiểm theo thứ tự:

1. Function đang dùng role nào (`aws lambda get-function-configuration`): plan có đổi role mà quên gắn policy, hay đổi tên role?
2. Permission policy của role có `secretsmanager:GetSecretValue` trên đúng ARN secret không (ARN secret có hậu tố ngẫu nhiên; wildcard hay ARN cũ
   sau khi secret được tạo lại)?
3. Secret mã hoá bằng KMS key riêng: role cần `kms:Decrypt` và key policy phải cho phép.
4. Resource policy của secret, permissions boundary, SCP có `Deny` không.
5. Nếu lỗi là "không assume được role" lúc deploy hay lúc chạy: trust policy có `lambda.amazonaws.com` không, điều kiện `aws:SourceAccount` có đúng ID
   tài khoản không.

Dùng `aws iam simulate-principal-policy` để xác nhận, CloudTrail để thấy request bị từ chối. Sửa bằng quyền đúng, không bằng `*`; thêm bước kiểm
quyền vào pipeline (Access Analyzer policy validation, test đánh giá policy).

## API Gateway REST API, HTTP API hay Lambda Function URL: chọn thế nào?

REST API khi cần quản lý API: usage plan, API key và quota theo khách, request validation, mapping template, integration thẳng tới dịch vụ AWS
(SQS, DynamoDB), WAF, cache. HTTP API khi chỉ cần route tới Lambda hay HTTP backend với JWT authorizer: rẻ hơn khoảng 70%, độ trễ thấp hơn. Function
URL khi một function một endpoint (webhook, công cụ nội bộ), không cần gì ngoài auth IAM hay không auth. ALB khi lưu lượng lớn đều và đã có ALB.

Lưu ý bảo mật: integration HTTP proxy tới URL tuỳ ý biến API thành proxy mở nếu cấu hình sai; giới hạn bằng review.

## Khi nào chọn serverless (Lambda), khi nào chọn container (ECS/Fargate, Kubernetes), khi nào chọn VM?

Lambda: tải theo đợt hay thấp, xử lý event (hàng đợi, file mới, lịch), glue code, team nhỏ không muốn vận hành; giới hạn 15 phút, cold start, chi phí
tăng nhanh khi tải cao và đều. Container: tải đều, service chạy lâu, cần kiểm soát runtime, dùng lại image ở mọi môi trường; Fargate bỏ việc quản
máy, Kubernetes khi có nhiều service và team platform. VM: phần mềm cần hệ điều hành đầy đủ, license theo máy, tải đều lớn tối ưu giá (Reserved,
Savings Plans, Spot), hay nhà cung cấp chỉ có VM (Hetzner, Contabo).

Câu trả lời tốt đặt số vào: 3 triệu request/tháng 200 ms gần như miễn phí trên Lambda; 200 request/giây đều cả ngày thì Lambda đắt hơn vài container
nhỏ nhiều lần.

## Startup của bạn có 300 USD/tháng, khách ở Brazil, 3 dev. Chọn nhà cung cấp nào và vì sao?

Loại theo ràng buộc trước: độ trễ và luật dữ liệu (LGPD) đòi region ở Brazil, loại Hetzner, DigitalOcean, Contabo, Heroku. Còn AWS `sa-east-1`, GCP
`southamerica-east1`, Azure Brazil South. Với 3 dev không trực đêm: dịch vụ quản lý (container serverless như Fargate hay Cloud Run, Postgres
quản lý), Lambda cho event. Ước tính thứ chạy cả ngày (database, load balancer, mạng, log), nhớ region São Paulo đắt hơn us-east-1, còn chỗ cho
staging và mùa cao điểm. Chọn giữa AWS và GCP bằng kỹ năng sẵn có và dịch vụ cần, rồi ghi đường lui: container và Postgres là chuẩn mở, phần khoá
chặt là IAM, hàng đợi, event bus.

## Hoá đơn AWS tháng này tăng gấp ba. Bạn làm gì trong giờ đầu tiên và tuần sau đó?

Giờ đầu: Cost Explorer theo service, rồi theo usage type và region, rồi theo tag để tìm khoản tăng; Cost Anomaly Detection nếu đã bật. Nghi phạm quen
thuộc: NAT gateway (dữ liệu đi qua tăng), egress, log CloudWatch không retention, Lambda bị vòng lặp (function ghi S3 kích hoạt chính nó, retry vô
hạn), máy hay cluster quên tắt, snapshot. Nếu đang chảy máu thì chặn trước khi điều tra: throttling hay xoá API key, reserved concurrency 0, tắt
event source mapping.

Tuần sau: tag bắt buộc (`Owner`, `Environment`) và bật cost allocation tag; budget theo team có cảnh báo dự báo; retention mặc định cho log; VPC
endpoint thay NAT cho S3/DynamoDB; lịch tắt môi trường không phải production; Savings Plans cho phần tải ổn định. Báo cáo chi phí theo đơn hàng
(unit cost) để thấy chi phí có tăng tương ứng doanh thu không.

## Shared responsibility model áp vào Lambda, RDS và EC2 khác nhau thế nào?

Càng được quản lý, AWS nhận càng nhiều tầng. EC2: AWS lo phần cứng và hypervisor; bạn lo hệ điều hành, vá, runtime, mạng, code, dữ liệu. RDS: AWS
thêm hệ điều hành và vá engine trong maintenance window, backup tự động, failover Multi-AZ; bạn lo chọn phiên bản và thời điểm nâng cấp lớn, mạng,
quyền, mã hoá, kiểm restore. Lambda: AWS thêm cả runtime và môi trường thực thi; bạn lo code và thư viện đóng gói, IAM của function, cấu hình dữ
liệu, chuyển runtime khi hết hạn hỗ trợ. Không bao giờ chuyển giao: quyền truy cập, dữ liệu và việc kiểm chứng backup.

## LocalStack thay được AWS thật đến đâu trong CI và học tập?

Thay được cho phần lớn API dữ liệu và tích hợp: S3, SQS, SNS, DynamoDB, IAM, Secrets Manager, EventBridge, API Gateway REST; đủ để test IaC (`tofu
apply` thật) và code gọi SDK mà không tốn tiền, không cần credential thật. Không thay được: IAM không được thực thi ở bản community (policy sai vẫn
chạy), hành vi cụ thể về độ trễ, giới hạn, eventual consistency, giá; một số dịch vụ chỉ có ở bản Pro hay chỉ là mock (EC2, RDS, API Gateway v2). Vì
vậy kết hợp: LocalStack cho test nhanh và vòng phản hồi, `tofu plan` cho phần không có, policy kiểm tĩnh hay bằng simulator, và một môi trường AWS
thật (sandbox) cho test tích hợp trước production.
