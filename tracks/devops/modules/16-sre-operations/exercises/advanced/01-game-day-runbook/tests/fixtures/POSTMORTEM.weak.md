# Postmortem

## 1. Tóm tắt

Database tắt trong game day, mọi request lỗi trong khoảng hai phút. Người trực xử lý chậm vì cẩu thả không đọc runbook, sau đó
khởi động lại database và hệ thống chạy lại bình thường, không mất dữ liệu nào cả, mọi người đã về nhà an toàn.

## 2. Tác động

Khoảng 2 phút lỗi, tiêu một ít error budget của tháng.

## 3. Timeline

| Giờ | Sự kiện |
| --- | --- |
| 14:04:05 | Hệ thống khoẻ lại |
| 14:02:10 | Bắt đầu |
| 14:02:40 | Bơm lỗi |
| 14:02:52 | Phát hiện |
| 14:02:53 | Khởi động lại |

## 4. Nguyên nhân

- Database tắt.
- Người trực chậm.

## 5. Phát hiện và khôi phục

Phát hiện bằng dashboard, khôi phục bằng tay.

## 6. Bài học

- Đọc runbook.
- Nhanh hơn.
- Cẩn thận hơn.

## 7. Action items

| Việc | Người phụ trách | Hạn |
| --- | --- | --- |
| Đọc lại runbook | Người trực | sớm |
| Thêm healthcheck | Platform | tuần sau |
| Retry | Checkout | tháng sau |
