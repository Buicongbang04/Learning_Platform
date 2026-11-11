# Runbook

## api-slow

### Triệu chứng

Khách báo tra đơn chậm, p95 latency trên dashboard vượt 300 ms.

### Chẩn đoán

Xem p95 trên Grafana, nếu cao thì xử lý theo bước dưới đây cho nhanh.

### Khôi phục

Khởi động lại dịch vụ cho chắc, rồi theo dõi thêm một lúc trên dashboard.

### Xác nhận

p95 dưới 300 ms trong 10 phút liên tục, không có span nào chậm bất thường.
