# Runbook: lab serverless

## 1. Chi phí ước tính

| Tài nguyên | Đơn giá | Lượng dùng | Thành tiền |
| --- | --- | --- | --- |
| Lambda | 0,20 USD / 1 triệu request | ít | 0 USD |
| API Gateway | 3,50 USD / 1 triệu request | ít | 0 USD |

Tổng: khoảng 20 USD.

## 2. Budget và cảnh báo

Có budget.

## 3. Triển khai

```bash
tofu init && tofu apply -auto-approve
```

## 4. Kiểm tra

Mở console xem Lambda có chạy không.

## 5. Dọn dẹp

Xoá stack trên console khi xong.

## 6. Bản chạy local tương đương

Không cần.

## 7. Khi có sự cố

- Gọi người trực.
