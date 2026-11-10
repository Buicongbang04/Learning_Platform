---
title: Thiết kế VPC ba tầng bằng OpenTofu, kiểm bằng plan
level: basic
services: [localstack-devops]
files:
  - path: starter/infra/network.tf
    note: 2 TODO (route tầng app, route table tầng db)
  - path: starter/infra/security.tf
    note: 2 TODO (security group tầng app, db)
  - path: starter/infra/database.tf
    note: 1 TODO (RDS)
  - path: starter/infra/variables.tf
    note: Giữ nguyên
  - path: starter/infra/versions.tf
    note: Giữ nguyên
  - path: tests/test_vpc_plan.py
    note: Không sửa; chỉ plan, không apply
run:
  - docker compose -f setup/docker-compose.yml --profile devops up -d --wait localstack-devops
  - uv run pytest tracks/devops/modules/14-cloud-serverless/exercises/basic/02-three-tier-vpc-plan -q -rs
---

## Mục tiêu

Đọc và sửa một VPC ba tầng (public, app, db) trên hai AZ: subnet nào ra Internet bằng đường nào, security group nào được nói chuyện với
security group nào, database nằm đâu và giữ mật khẩu ở đâu. Kiểm thiết kế bằng `tofu plan`, không tốn đồng nào.

## Đề bài

`starter/infra/` mô tả mạng cho Olist Shop trên AWS: ALB ở tầng public, API ở tầng app, Postgres (RDS) ở tầng db, mỗi tầng một subnet trong
mỗi AZ của `var.azs`. Một đồng nghiệp viết xong nhưng review phát hiện năm chỗ sai (năm TODO). Sửa để:

- **Subnet**: ba tầng, mỗi tầng một subnet mỗi AZ, dải không chồng nhau, nằm trong VPC; subnet app và db `map_public_ip_on_launch = false`.
- **Route** (khai báo bằng `aws_route`, không dùng khối `route` lồng): route table public có `0.0.0.0/0` tới Internet gateway; route table
  app có `0.0.0.0/0` tới NAT gateway (NAT nằm ở subnet public); route table db không có route nào ra ngoài VPC. Mỗi subnet gắn đúng route
  table của tầng mình.
- **Security group** (rule bằng `aws_vpc_security_group_ingress_rule`/`egress_rule`, không dùng `ingress`/`egress` lồng): chỉ ALB mở cho
  Internet (TCP 443); app chỉ nhận TCP 8000 từ security group của ALB; db chỉ nhận TCP 5432 từ security group của app. Không rule nào mở
  mọi giao thức hay một dải cổng.
- **RDS**: `publicly_accessible = false`, `storage_encrypted = true`, không có `password` trong cấu hình mà dùng
  `manage_master_user_password = true` (RDS tự tạo và xoay mật khẩu trong Secrets Manager), gắn đúng security group db và một DB subnet
  group chỉ gồm subnet tầng db.

Giữ nguyên tên tài nguyên (`aws_subnet.public/app/db`, `aws_route_table.public/app/db`, `aws_security_group.alb/app/db`...): test đọc
quan hệ giữa chúng từ phần `configuration` của plan JSON (thuộc tính nào tham chiếu tài nguyên nào), vì ID thật chỉ có sau apply.

**Cách test chấm.** `tofu init` rồi `tofu plan -out` + `show -json` trên `localstack-devops` qua `TofuLab`. LocalStack community không
có EC2, VPC hay RDS thật, nhưng plan tạo mới không gọi API của chúng nên vẫn chạy; test **không apply**. Không có tài khoản AWS nào bị
gọi. Muốn có "RDS" chạy thật trên máy, dùng container Postgres như module 06 (`postgres:16`): cùng engine, cùng cổng 5432, khác ở chỗ
backup, failover, vá lỗi là việc của bạn. Hướng dẫn tạo thật trên AWS (tốn tiền, giá tham khảo 11/2026 ở us-east-1: NAT gateway khoảng 33 USD/tháng, RDS `db.t4g.micro` khoảng
14 USD/tháng kể cả 20 GB ổ) xem bài Advanced 02 và mục 7 của README module.

## Tiêu chí đạt

- Plan chỉ có `create`.
- Ba tầng, hai AZ, CIDR hợp lệ; app và db không tự nhận IP public.
- Route và route table đúng như trên; NAT ở subnet public.
- Chuỗi security group ALB → app → db, chỉ ALB mở cho Internet.
- RDS private, mã hoá, mật khẩu do RDS quản lý trong Secrets Manager.

## Gợi ý

### Gợi ý 1

Trong plan JSON, `configuration.root_module.resources[].expressions.<thuộc tính>.references` liệt kê tài nguyên mà thuộc tính đó tham
chiếu, ví dụ `["aws_security_group.alb.id", "aws_security_group.alb"]`. Chạy tay `tofu show -json plan.tfplan | jq '.configuration'` để
xem test nhìn thấy gì.

### Gợi ý 2

Security group là stateful: cho vào thì response tự được ra. Rule tham chiếu security group (`referenced_security_group_id`) thay cho dải
IP giữ đúng ý "chỉ ALB gọi được API" kể cả khi IP của ALB đổi. `manage_master_user_password` và thuộc tính `password` loại trừ nhau.
