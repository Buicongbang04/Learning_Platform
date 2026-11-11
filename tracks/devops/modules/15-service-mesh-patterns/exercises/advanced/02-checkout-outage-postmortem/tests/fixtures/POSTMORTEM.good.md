# Postmortem: game day staging, pool Postgres của payments cạn ngày 2026-10-14

## 1. Tóm tắt

- Game day trên staging: bơm độ trễ 2 giây vào Postgres lúc 10:03, payments lỗi từ 5% trở lên trong 4 phút (10:03 tới 10:06).
- Pool kết nối 10 mỗi pod cạn sau khoảng 20 giây; request chờ pool rồi hết timeout.
- Hệ thống tự hồi phục khi bỏ độ trễ lúc 10:07, không cần can thiệp.

## 2. Tác động

- 591 đơn thử nghiệm thất bại (dữ liệu giả của game day, không có khách thật).
- Phút đỉnh 10:05: checkout gửi 22 request mỗi giây, payments nhận 27 request mỗi giây (retry của api thêm khoảng 20%).
- p99 của payments lên 2900 ms.

## 3. Timeline

| Thời điểm | Sự kiện |
| --- | --- |
| 10:00 | Bắt đầu game day, chỉ số bình thường |
| 10:03 | Bơm độ trễ 2 giây vào Postgres; lỗi payments vượt 5% |
| 10:04 | Alert PaymentsErrorRate firing, người trực nhận |
| 10:05 | Pool kết nối 10/10 trên cả hai pod |
| 10:07 | Bỏ độ trễ theo kịch bản |
| 10:08 | Lỗi về dưới 1%, kết thúc |

## 4. Nguyên nhân

### Vì sao

1. Vì sao payments lỗi? Request chờ kết nối Postgres quá 2 giây rồi hết timeout.
2. Vì sao phải chờ? Pool 10 kết nối mỗi pod bị giữ bởi query chậm.
3. Vì sao query chậm giữ pool lâu? Không có statement timeout ở phía Postgres.

### Yếu tố góp phần

- api retry 503 hai lần không có backoff, thêm tải đúng lúc pool cạn.
- Dashboard chưa có biểu đồ số kết nối đang dùng của pool.

## 5. Review theo pattern

| Pattern | Nhóm | Hiện trạng | Đề xuất |
| --- | --- | --- | --- |
| Retry | Availability | Retry 2 lần, không backoff | Backoff có jitter, retry budget 10% |
| Bulkhead | Availability | Một pool chung cho mọi loại query | Pool riêng cho ghi ledger và cho báo cáo |
| Cache-Aside | Data Management | Đọc phí vận chuyển từ Postgres mỗi lần | Cache phí theo bang trong Redis, TTL 10 phút |
| Strangler Fig | Design & Implementation | Logic thanh toán cũ nằm chung api | Tách dần sang payments qua lớp định tuyến |
| Health Endpoint Monitoring | Management & Monitoring | /readyz không kiểm pool | /readyz báo lỗi khi pool đầy quá 30 giây |
| External Configuration Store | Management & Monitoring | Timeout ghi cứng trong code | Đưa timeout, số retry vào ConfigMap để đổi không cần build |

## 6. Action items

| Việc | Loại | Người phụ trách | Hạn |
| --- | --- | --- | --- |
| Đặt statement_timeout 1s cho user của payments | Phòng ngừa | Team payments | 2026-10-21 |
| Backoff có jitter và retry budget cho client api | Phòng ngừa | Team api | 2026-10-28 |
| Biểu đồ và alert số kết nối pool | Phát hiện | Team platform | 2026-10-21 |
| /readyz kiểm pool | Phát hiện | Team payments | 2026-10-28 |
| Runbook giảm tải: tắt retry qua cấu hình | Giảm thiểu | Team platform | 2026-11-04 |

## 7. Bài học

- Pool nhỏ cộng query chậm cạn rất nhanh; timeout ở database quan trọng ngang timeout ở client.
- Game day trên staging bắt được lỗi trước Black Friday, nên làm mỗi quý.
