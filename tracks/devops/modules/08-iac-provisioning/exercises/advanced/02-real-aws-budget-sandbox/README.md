---
title: Sandbox trên AWS thật có budget alarm và kế hoạch dọn, bản kiểm local trên LocalStack
level: advanced
services: [localstack-devops]
files:
  - path: starter/aws/versions.tf
    note: Provider, thêm default_tags
  - path: starter/aws/variables.tf
    note: Thêm biến và validation
  - path: starter/aws/main.tf
    note: Budget, VPC, subnet, EC2
  - path: starter/aws/outputs.tf
    note: Output tuỳ bạn
  - path: starter/COST.md
    note: Ước tính chi phí và kế hoạch dọn
  - path: tests/test_budget_sandbox.py
    note: Không sửa; chỉ plan trên LocalStack, không bao giờ gọi AWS thật
run:
  - docker compose -f setup/docker-compose.yml --profile devops up -d --wait localstack-devops
  - uv run pytest tracks/devops/modules/08-iac-provisioning/exercises/advanced/02-real-aws-budget-sandbox -q
---

## Mục tiêu

Dựng hạ tầng trên tài khoản AWS thật một cách có trách nhiệm: ước tính chi phí trước, đặt budget alarm, gắn tag hạn dùng, chọn cấu
hình rẻ và an toàn, chạy `tofu destroy` đúng hạn và kiểm không còn gì phát sinh. Phần nào LocalStack bản miễn phí không chạy được
(EC2, VPC, Budgets) thì kiểm bằng plan trên LocalStack.

## Đề bài

Viết cấu hình trong `starter/aws/` cho một sandbox để thử Olist Shop API trên EC2:

- `default_tags` của provider: `Project = "olist-shop-sandbox"`, `Owner = var.owner`, `ExpiresOn = var.expires_on` (dạng
  `YYYY-MM-DD`, có validation), thêm tag khác tuỳ bạn.
- `aws_budgets_budget` loại `COST`, `MONTHLY`, đơn vị `USD`, hạn mức `var.monthly_budget_usd` (mặc định 5, validation 0 < x ≤ 10),
  một cảnh báo `ACTUAL` theo phần trăm ở ngưỡng ≤ 80 và một cảnh báo `FORECASTED` theo phần trăm ở ngưỡng ≤ 100, gửi tới
  `var.alert_email`.
- Một VPC và **subnet private** (`map_public_ip_on_launch = false`). Không internet gateway, NAT gateway, Elastic IP, load
  balancer hay RDS: những thứ tính tiền theo giờ dù không dùng.
- Một `aws_instance`: `instance_type` từ biến có validation chỉ `t4g.nano` hay `t4g.micro`, `ami_id` từ biến có validation
  `^ami-[0-9a-f]{8,17}$`, `associate_public_ip_address = false`, IMDSv2 bắt buộc (`http_tokens = "required"`), ổ root mã hoá và
  không quá 8 GiB.
- `starter/COST.md`: giả định (region, thời gian chạy, Free Tier có áp dụng không), bảng chi phí ít nhất 3 dòng đủ 4 cột
  (`Tài nguyên`, `Đơn giá`, `Thời gian`, `Thành tiền`), một dòng có chữ `Tổng` và số tiền `... USD` không quá 10, phần budget, và
  phần dọn dẹp có lệnh `tofu destroy`.

**Chạy trên AWS thật (tuỳ chọn, không chấm).** Cần một tài khoản sandbox riêng trong AWS Organization (không dùng chung tài khoản có
production) và credential **ngắn hạn**:

- Không bao giờ dùng user root, kể cả để "thử nhanh". Root chỉ để thiết lập ban đầu, có MFA phần cứng, rồi cất đi.
- Không tạo access key dài hạn cho IAM user (`aws configure` với `AKIA...`). Key dài hạn bị lộ qua shell history, dotfile, ảnh
  chụp màn hình và không tự hết hạn.
- Dùng **IAM Identity Center** (SSO): đăng nhập bằng trình duyệt có MFA, CLI nhận credential sống vài giờ. Không có Identity Center
  thì assume role có điều kiện `aws:MultiFactorAuthPresent` (`aws sts assume-role ... --serial-number ... --token-code ...`).
- Permission set (hay role) chỉ cấp: EC2 (gồm cả API VPC, subnet, instance), AWS Budgets, `ssm:GetParameter` trên
  `arn:aws:ssm:*::parameter/aws/service/*` (đọc ID AMI công khai), trong một region (SCP hay điều kiện `aws:RequestedRegion`).
  `sts:GetCallerIdentity` luôn được phép.

**Tạo profile `olist-sandbox` theo kiểu SSO** (một lần; AWS CLI v2):

```bash
aws configure sso --profile olist-sandbox
```

CLI hỏi tên SSO session (ví dụ `olist`), start URL (`https://<tổ-chức>.awsapps.com/start`), SSO region, rồi mở trình duyệt để
đăng nhập có MFA; chọn tài khoản sandbox và permission set ở trên, region mặc định `us-east-1`. Kết quả trong `~/.aws/config`:

```text
[profile olist-sandbox]
sso_session = olist
sso_account_id = 111122223333
sso_role_name = OlistSandboxIaC
region = us-east-1

[sso-session olist]
sso_start_url = https://olist.awsapps.com/start
sso_region = us-east-1
sso_registration_scopes = sso:account:access
```

Không có access key nào trong tệp. Mỗi phiên làm việc chạy bốn bước dưới từ `starter/aws/`, **mỗi bước một khối, đọc kết quả rồi
mới sang bước sau**. Thay `111122223333` bằng ID tài khoản sandbox của bạn.

**(a) Đăng nhập và xác nhận danh tính.** Dừng nếu account không đúng tài khoản sandbox:

```bash
export AWS_PROFILE=olist-sandbox AWS_REGION=us-east-1 SANDBOX_ACCOUNT_ID=111122223333 &&
unset AWS_ENDPOINT_URL AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN &&
aws sso login &&
aws sts get-caller-identity --query '[Account, Arn]' --output text &&
test "$(aws sts get-caller-identity --query Account --output text)" = "$SANDBOX_ACCOUNT_ID" &&
echo "Đúng tài khoản sandbox"
```

**(b) Plan và lưu ra tệp.** Khối này tự kiểm lại tài khoản, không apply gì:

```bash
test "$(aws sts get-caller-identity --query Account --output text)" = "$SANDBOX_ACCOUNT_ID" &&
AMI_ID="$(aws ssm get-parameter --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64 --query Parameter.Value --output text)" &&
printf 'prefix = "olist-sandbox-%s"\nowner = "%s"\nexpires_on = "%s"\nalert_email = "%s"\nami_id = "%s"\n' \
  "$USER" "you@example.com" "$(date -d '+1 day' +%F)" "you@example.com" "$AMI_ID" > sandbox.tfvars &&
tofu init &&
tofu plan -var-file=sandbox.tfvars -out=sandbox.tfplan
```

**(c) Review plan.** Đọc toàn bộ `tofu show sandbox.tfplan`, rồi tóm tắt hành động:

```bash
tofu show -json sandbox.tfplan | jq -r '.resource_changes[] | "\(.change.actions | join(",")) \(.address)"'
```

Chỉ đi tiếp khi: mọi dòng là `create` và đúng 4 tài nguyên (`aws_budgets_budget.monthly`, `aws_vpc`, `aws_subnet`,
`aws_instance`); `instance_type` là `t4g.nano` hay `t4g.micro`; không có `aws_internet_gateway`, `aws_nat_gateway`, `aws_eip`;
`associate_public_ip_address = false`; `limit_amount` đúng budget bạn định; region `us-east-1`; tag `ExpiresOn` là ngày mai. Có gì
khác thì xoá `sandbox.tfplan`, sửa cấu hình, làm lại (b).

**(d) Apply đúng plan đã review:**

```bash
test "$(aws sts get-caller-identity --query Account --output text)" = "$SANDBOX_ACCOUNT_ID" &&
tofu apply sandbox.tfplan
```

`tofu apply sandbox.tfplan` không hỏi lại và chỉ thực thi đúng plan đã lưu; state đổi từ lúc plan thì OpenTofu từ chối (plan cũ),
phải làm lại (b). Từ 30/9/2026, AWS Budgets gửi **email xác minh** tới mỗi địa chỉ mới; cảnh báo chỉ tới sau khi người nhận bấm
link trong email đó (trạng thái `Pending` trên console Budgets cho tới lúc đó). Dùng xong (cùng ngày):

```bash
test "$(aws sts get-caller-identity --query Account --output text)" = "$SANDBOX_ACCOUNT_ID" &&
tofu destroy -var-file=sandbox.tfvars &&
aws ec2 describe-instances --filters "Name=tag:Project,Values=olist-shop-sandbox" \
  "Name=instance-state-name,Values=pending,running,shutting-down,stopping,stopped" \
  --query 'Reservations[].Instances[].InstanceId' --output text
```

Lệnh cuối phải in rỗng (mọi trạng thái trừ `terminated`). Budget cũng bị destroy; nếu muốn giữ budget cho cả tài khoản, đặt nó ở
một stack riêng không bao giờ destroy.

**Cách test chấm (bản local).** Test không bao giờ gọi AWS thật: qua `TofuLab`, `tofu init` và `tofu plan -out` + `show -json` trên
`localstack-devops` với `ci.auto.tfvars.json` (owner, `expires_on`, `alert_email`, `ami_id` giả). LocalStack community không có
EC2, VPC hay Budgets, nhưng plan tạo mới không gọi API của các service đó nên vẫn chạy; test **không apply**. Rồi đọc
`planned_values` để kiểm các yêu cầu trên. Muốn thử "chạy" Olist Shop API như trên EC2 mà không tốn tiền, dùng container ở module 06.

## Tiêu chí đạt

- Plan chỉ có hành động `create`; đúng một `aws_budgets_budget`, đúng một `aws_instance`.
- Budget, cảnh báo, instance, subnet đúng như đề; không có tài nguyên thuộc loại bị cấm.
- Mọi tài nguyên có `tags_all` mang đủ `Project`, `Owner`, `ExpiresOn`.
- `monthly_budget_usd = 50`, `instance_type = "m5.large"`, `ami_id = "ubuntu-latest"`: lỗi `Invalid value for variable`.
- `COST.md` đạt các yêu cầu cấu trúc trên; một test đưa khung trống vào phép kiểm và đòi nó bị bắt.
- (Tự đánh giá) Nếu chạy thật: email xác minh của Budgets đã được bấm (subscriber `Active`/đã xác minh), destroy xong không còn instance, hôm sau Cost Explorer lọc theo tag
  không còn phát sinh. Rubric trong `solutions/advanced/02-real-aws-budget-sandbox/SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`default_tags` đặt ở provider được gộp vào `tags_all` của mọi tài nguyên hỗ trợ tag; tag riêng của tài nguyên ghi đè khi trùng
khoá. `limit_amount` của budget là chuỗi (`format("%.2f", var.monthly_budget_usd)`). Trong `planned_values`, `metadata_options` và
`root_block_device` là danh sách một phần tử.

### Gợi ý 2

Tiền của một sandbox nhỏ thường không nằm ở instance mà ở thứ bị quên: NAT gateway (khoảng 0,045 USD/giờ, cộng tiền dữ liệu), IPv4
public (0,005 USD/giờ mỗi địa chỉ), snapshot, log. Budget chỉ cảnh báo, chậm tới 24 giờ, không tự tắt gì; tag `ExpiresOn` và
`tofu destroy` theo lịch mới là thứ dừng chi phí.
