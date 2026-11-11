# Kiến trúc cloud cho Olist Shop

## 1. Bối cảnh và ràng buộc

- Ngân sách 300 USD mỗi tháng.
- RPO 1 giờ.
- Khách ở Brazil.
- Team nhỏ.

## 2. Phương án

| Phương án | Nhà cung cấp | Chi phí/tháng (USD) | Vận hành | Rủi ro |
| --- | --- | --- | --- | --- |
| EKS | AWS | 400 | Nhiều | Đắt |
| Lambda | AWS | 120 | Ít | Cold start |
| ECS | AWS | 250 | Vừa | Ít |

## 3. Quyết định

- Chọn AWS vì phổ biến.
- Dùng EKS cho chuyên nghiệp.
- Region us-east-1 vì rẻ.

## 4. Kiến trúc

Client gọi API trên EKS, EKS gọi RDS.

## 5. Chi phí ước tính

| Hạng mục | Đơn giá | Lượng | Thành tiền (USD) |
| --- | --- | --- | --- |
| EKS control plane | 0,10 USD/giờ | 730 giờ | 73 |
| EC2 node | 0,0832 USD/giờ | 3 node | 182 |
| RDS Multi-AZ | 0,136 USD/giờ | 730 giờ | 99 |
| NAT gateway | 0,045 USD/giờ | 730 giờ | 33 |
| S3 | 0,023 USD/GB | 150 GB | 3,45 |

Tổng: 340 USD.

## 6. Trách nhiệm chung

- AWS lo hết.

## 7. Rủi ro, lock-in và đường lui

- Không có.

## 8. Khi nào xem lại

- Khi có tiền.
