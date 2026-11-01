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

**Chạy trên AWS thật (tuỳ chọn, không chấm).** Cần một tài khoản sandbox riêng (không dùng chung tài khoản có production), user hay
role chỉ có quyền EC2, VPC, Budgets trong một region. Từ `starter/aws/`:

```bash
export AWS_PROFILE=olist-sandbox AWS_REGION=us-east-1 &&
unset AWS_ENDPOINT_URL &&
aws sts get-caller-identity &&
AMI_ID="$(aws ssm get-parameter --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64 --query Parameter.Value --output text)" &&
printf 'prefix = "olist-sandbox-%s"\nowner = "%s"\nexpires_on = "%s"\nalert_email = "%s"\nami_id = "%s"\n' \
  "$USER" "you@example.com" "$(date -d '+1 day' +%F)" "you@example.com" "$AMI_ID" > sandbox.tfvars &&
tofu init &&
tofu plan -var-file=sandbox.tfvars -out=sandbox.tfplan &&
tofu apply sandbox.tfplan
```

Kiểm `aws sts get-caller-identity` in đúng tài khoản sandbox **trước** khi apply. Email xác nhận của AWS Budgets tới trong vài phút.
Dùng xong (cùng ngày):

```bash
tofu destroy -var-file=sandbox.tfvars &&
aws ec2 describe-instances --filters "Name=tag:Project,Values=olist-shop-sandbox" "Name=instance-state-name,Values=pending,running,stopping,stopped" \
  --query 'Reservations[].Instances[].InstanceId' --output text
```

Lệnh cuối phải in rỗng. Budget cũng bị destroy; nếu muốn giữ budget cho cả tài khoản, đặt nó ở một stack riêng không bao giờ destroy.

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
- (Tự đánh giá) Nếu chạy thật: budget gửi email xác nhận, destroy xong không còn instance, hôm sau Cost Explorer lọc theo tag
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
