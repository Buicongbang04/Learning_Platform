# Postmortem: API lỗi

## 1. Tóm tắt

API lỗi một lúc, đã rollback.

## 2. Tác động

Khoảng một giờ, nhiều phút khách không đặt được đơn.

## 3. Timeline

| Giờ | Sự kiện |
| --- | --- |
| 21:02 | API lỗi |
| 20:47 | Deploy |
| 21:09 | Alert bắn |
| 21:38 | Khách báo |
| 21:41 | Người trực xem |
| 21:52 | Rollback |
| 21:58 | Hết lỗi |
| 23:00 | Đóng |

## 4. Nguyên nhân gốc và yếu tố góp phần

- Deploy lỗi.
- Pager không rung.
- Người duyệt PR không cẩn thận.

## 5. Phát hiện và xử lý

Khách báo sau nhiều phút, đã rollback.

## 6. Điều chạy tốt và chưa tốt

- Rollback nhanh.
- Alert không tới.
- Khách báo sớm.

## 7. Bài học

- Cẩn thận hơn.

## 8. Action items

| Việc | Người phụ trách | Hạn | Loại |
| --- | --- | --- | --- |
| Cẩn thận khi deploy | | sớm | phòng ngừa |
| Duyệt PR kỹ hơn | Search | tuần sau | phòng ngừa |
| Thêm alert | SRE | 2026-11-01 | phát hiện |
| Viết runbook | SRE | 2026-11-01 | xử lý |
| Kiểm pager | SRE | 2026-11-01 | phát hiện |
