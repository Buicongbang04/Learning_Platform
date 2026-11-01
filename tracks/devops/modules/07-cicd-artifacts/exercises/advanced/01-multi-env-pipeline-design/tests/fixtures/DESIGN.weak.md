# Thiết kế pipeline nhiều môi trường cho Olist Shop

## 1. Bối cảnh và mục tiêu

Olist Shop đang deploy bằng tay mỗi tuần một lần, mỗi lần mất khoảng nửa ngày và hay lỗi. Mục tiêu là tự động hoá hoàn toàn để
deploy nhanh hơn, giảm lead time từ commit tới production, giảm change failure rate và rút MTTR khi có sự cố. Team có ba kỹ sư
backend và một người vận hành, dùng GitHub Actions và registry GHCR, chạy trên một cluster Kubernetes duy nhất chia namespace.

## 2. Môi trường và promotion

| Môi trường | Trigger | Phê duyệt | Artifact | Dữ liệu |
| --- | --- | --- | --- | --- |
| dev | Push mọi nhánh | không | olist-api:dev | Dữ liệu giả |
| staging | Merge vào main | không | olist-api:sha-<commit> theo digest | Bản sao đã ẩn danh |
| production | Merge vào main | không | olist-api:latest | Dữ liệu thật |

## 3. Sơ đồ pipeline

```mermaid
flowchart LR
  commit --> test --> build --> staging --> production
```

## 4. Chiến lược deploy theo service

| Service | Chiến lược | Lý do | Tín hiệu rollback |
| --- | --- | --- | --- |
| api | rolling | Mặc định của Kubernetes | Người dùng báo lỗi |
| worker | rolling | Mặc định của Kubernetes | Hàng đợi dồn |
| seed | rolling | Cho đồng bộ | Không có |

## 5. Rollback và migration cơ sở dữ liệu

- Khi lỗi thì build lại commit cũ và deploy lại.
- Migration chạy trước khi deploy bản mới.
- Có lỗi migration thì khôi phục backup.
- Theo dõi dashboard sau deploy.
- Báo lên kênh chat của team.

## 6. Bí mật và quyền

- Lưu access key cloud trong secrets của repo.
- Mọi job dùng chung một token.
- Dùng environment cho production.
- Đặt permissions write-all cho tiện.

## 7. Gate tự động và quan sát

| Gate | Ngưỡng | Hành động |
| --- | --- | --- |
| Unit test | Phải xanh | Dừng pipeline |
| Quét lỗ hổng | Không có CRITICAL | Dừng pipeline |
| Tỉ lệ lỗi sau deploy | Thấp | Rollback |
| Smoke test | 3 endpoint chính trả 200 | Rollback |

## 8. Rủi ro và lộ trình triển khai

- Tuần 1 làm pipeline dev.
- Tuần 2 làm staging.
- Tuần 3 làm production.
- Rủi ro: team chưa quen.
