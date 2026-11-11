# Lời giải: VPC ba tầng

Lời giải nằm trong `infra/network.tf`, `infra/security.tf`, `infra/database.tf`.

## Năm chỗ sửa

| TODO | Starter | Lời giải | Vì sao |
| --- | --- | --- | --- |
| 1 | Tầng app không có route ra ngoài, và subnet app tự nhận IP public | `aws_route.app_nat` tới NAT gateway; `map_public_ip_on_launch = false` | App cần gọi ra (API thanh toán, kéo image, gọi API AWS) nhưng không được nhận kết nối từ Internet. NAT chỉ cho chiều ra |
| 2 | Subnet db gắn route table public | Gắn `aws_route_table.db`, không có route mặc định | Một instance db lỡ có IP public sẽ đi thẳng ra Internet qua IGW. Tầng db không cần ra ngoài VPC |
| 3 | App mở 8000 cho `0.0.0.0/0` | Ingress 8000 từ `aws_security_group.alb` | Mọi traffic phải qua ALB (TLS, WAF, health check); tham chiếu security group không phụ thuộc IP của ALB |
| 4 | DB mở mọi giao thức cho cả dải VPC | Ingress TCP 5432 từ `aws_security_group.app` | Dải VPC gồm cả subnet public; "mọi giao thức" mở cả SSH và các cổng không ai nghĩ tới |
| 5 | `publicly_accessible = true`, không mã hoá, mật khẩu trong code | Private, `storage_encrypted`, `manage_master_user_password` | Mật khẩu ghi trong `.tf` nằm trong git và trong state; RDS quản lý mật khẩu trong Secrets Manager và xoay được |

## Các quyết định khác

- **Một NAT gateway** ở AZ đầu tiên cho rẻ (khoảng 33 USD/tháng cộng tiền dữ liệu). Production cần một NAT mỗi AZ: AZ chứa NAT chết thì
  app ở AZ kia mất đường ra, và traffic chéo AZ cũng tính tiền.
- **Security group không có rule egress mặc định.** Provider AWS xoá rule "allow all egress" khi tạo security group, nên egress được
  khai báo tường minh: ALB chỉ ra tới app 8000, app ra db 5432 và HTTPS ra ngoài; db không ra đâu cả.
- **NACL để mặc định.** NACL là stateless, theo subnet, cần mở cả cổng ephemeral cho chiều về; dùng để chặn thô (ví dụ cấm cả dải IP)
  chứ không thay security group. Thiết kế ba tầng hay gặp lỗi khi NACL quá chặt mà quên cổng 1024-65535.
- **CIDR bằng `cidrsubnet`** với độ lệch theo tầng (0, 10, 20): thêm AZ thứ ba không đổi dải của subnet cũ.

## Đọc thêm

- Muốn app gọi S3, DynamoDB không qua NAT (và không trả tiền dữ liệu NAT): gateway VPC endpoint cho S3, DynamoDB miễn phí.
- Tạo thật trên AWS: chạy plan này với profile sandbox như bài Advanced 02, chỉ khi đã có budget alarm, và destroy trong ngày.
