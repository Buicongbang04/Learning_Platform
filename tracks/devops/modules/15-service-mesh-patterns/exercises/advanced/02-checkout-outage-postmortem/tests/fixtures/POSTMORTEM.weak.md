# Postmortem: game day staging ngày 2026-10-14

## 1. Tóm tắt

- Payments lỗi một lúc.
- Đã hồi phục.
- Do Postgres chậm.

## 2. Tác động

- Một số đơn lỗi.

## 3. Timeline

| Thời điểm | Sự kiện |
| --- | --- |
| 10:00 | Bắt đầu |
| 10:05 | Pool cạn |
| 10:03 | Bơm độ trễ |
| 10:04 | Alert |
| 10:07 | Bỏ độ trễ |
| 10:08 | Xong |

## 4. Nguyên nhân

### Vì sao

1. Postgres chậm.
2. Pool cạn.
3. Không có timeout.

### Yếu tố góp phần

- Retry.
- Thiếu dashboard.

## 5. Review theo pattern

| Pattern | Nhóm | Hiện trạng | Đề xuất |
| --- | --- | --- | --- |
| Retry | Availability | Có | Thêm backoff |
| Circuit Breaker | Availability | Không có | Thêm |
| Bulkhead | Availability | Không có | Thêm |
| Cache-Aside | Availability | Không có | Thêm |
| Throttling | Availability | Không có | Thêm |
| Health Endpoint Monitoring | Availability | Có | Giữ |

## 6. Action items

| Việc | Loại | Người phụ trách | Hạn |
| --- | --- | --- | --- |
| statement_timeout | Phòng ngừa | Team payments | 2026-10-21 |
| Backoff | Phòng ngừa | Team api | 2026-10-10 |
| Alert pool | Phòng ngừa | Team platform | 2026-10-21 |
| Bulkhead | Phòng ngừa | Team payments | 2026-10-28 |
| Runbook | Phòng ngừa | Team platform | 2026-11-04 |

## 7. Bài học

- Cần timeout.
- Nên game day thường xuyên.
