# Budget và dọn dẹp cho M11

Phần cloud của capstone chỉ gồm một bucket S3 chứa model (vài MB), một hàm Lambda 128 MB trả `/healthz` và một log group
giữ log 3 ngày. Với lưu lượng thử tay (vài trăm request), cả ba nằm trong free tier của AWS: Lambda miễn phí 1 triệu
request và 400 000 GB-giây mỗi tháng, S3 miễn phí 5 GB trong 12 tháng đầu, CloudWatch Logs miễn phí 5 GB log mỗi tháng.
Tiền chỉ phát sinh khi quên dọn, khi URL công khai bị gọi hàng loạt, hoặc khi tài khoản đã hết 12 tháng free tier.

## Ngưỡng

| Mức | Giá trị | Loại | Hành động |
| --- | --- | --- | --- |
| Trần tháng | 1 USD | `aws_budgets_budget.monthly` | Trần cho cả tài khoản, không lọc theo tag (lọc theo tag cần bật cost allocation tag và trễ 24 giờ) |
| Cảnh báo sớm | 0.5 USD (50% chi phí thực) | `ACTUAL > 50%` | Email: mở Cost Explorer, nhóm theo service, chạy `bash teardown.sh --dry-run` |
| Dự báo vượt trần | 1 USD (100% dự báo) | `FORECASTED > 100%` | Email: dọn ngay bằng `terraform destroy`, rồi `bash teardown.sh --dry-run` phải in 0 dòng |

## Alarm gửi tới đâu

Alarm của AWS Budgets gửi email tới `alert_email` trong `terraform.tfvars` (không commit tệp này). Budget chỉ cập nhật
vài lần mỗi ngày, nên nó là lưới cuối cùng, không phải công cụ theo dõi thời gian thực. Lambda URL dùng
`authorization_type = "NONE"` cho tiện thử; nếu muốn chặn lạm dụng, chuyển sang `AWS_IAM` và gọi bằng request đã ký.

## Dọn

1. `terraform destroy`: đường chính, xoá đúng những gì state biết.
2. `bash teardown.sh --dry-run`: lưới an toàn, liệt kê mọi thứ còn mang tag `project=eta-mlops`.
3. `bash teardown.sh --yes`: xoá phần còn sót (ví dụ khi mất state).
4. `bash teardown.sh --dry-run` lần nữa: phải in 0 dòng `WOULD DELETE`.

`teardown.sh` chỉ chọn tài nguyên có tag `project` bằng đúng `eta-mlops` (phân biệt hoa thường, không khớp tiền tố):
bucket tên `eta-mlops-...` mà không có tag thì không bị đụng tới. Thứ tự xoá: Lambda, log group, bucket, IAM role, budget
cuối cùng để cảnh báo còn hoạt động tới phút chót. Lịch dọn: cuối mỗi buổi thử, không để tài nguyên chạy qua đêm.
