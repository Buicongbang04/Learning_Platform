# Ước tính chi phí sandbox Olist Shop trên AWS

## Giả định

- Region `us-east-1`, giá on-demand niêm yết tháng 11/2026 (kiểm lại trên AWS Pricing Calculator trước khi chạy).
- Chạy thử tối đa 8 giờ trong một ngày rồi `tofu destroy`; tài khoản sandbox riêng, không dùng chung với production.
- Free Tier: tài khoản mở sau 15/7/2025 nhận credit thay vì 750 giờ t2/t3.micro; bảng dưới tính như không có Free Tier để không
  bị bất ngờ.

## Bảng chi phí

| Tài nguyên | Đơn giá | Thời gian | Thành tiền |
| --- | --- | --- | --- |
| EC2 `t4g.nano` | 0,0042 USD/giờ | 8 giờ | 0,034 USD |
| EBS gp3 8 GiB | 0,08 USD/GiB-tháng | 8 giờ (khoảng 0,011 tháng) | 0,007 USD |
| VPC, subnet, IMDS | 0 USD | 8 giờ | 0 USD |
| AWS Budgets (2 budget đầu miễn phí) | 0 USD | 1 tháng | 0 USD |
| Truyền dữ liệu ra Internet | Không có IP public, không NAT | 0 GB | 0 USD |

Tổng ước tính: 0,05 USD cho một lần thử 8 giờ; quên destroy cả tháng thì khoảng 3,7 USD, vẫn dưới budget 5 USD.

## Budget và cảnh báo

- `aws_budgets_budget` loại COST, 5 USD mỗi tháng, gửi email khi chi phí thật vượt 80% và khi dự báo vượt 100%.
- Budget chỉ cảnh báo, không tự tắt tài nguyên; dữ liệu chi phí trễ tới 24 giờ, nên budget là lưới an toàn cuối, không thay cho
  việc destroy đúng hạn.
- Tag `ExpiresOn` trên mọi tài nguyên để người khác (hay script dọn) biết khi nào được xoá.

## Dọn dẹp

```bash
tofu destroy -var-file=sandbox.tfvars &&
aws ec2 describe-instances --filters "Name=tag:Project,Values=olist-shop-sandbox" "Name=instance-state-name,Values=running" \
  --query 'Reservations[].Instances[].InstanceId' --output text
```

Lệnh thứ hai phải in rỗng. Hôm sau mở Cost Explorer, lọc theo tag `Project=olist-shop-sandbox` để xác nhận không còn phát sinh.
