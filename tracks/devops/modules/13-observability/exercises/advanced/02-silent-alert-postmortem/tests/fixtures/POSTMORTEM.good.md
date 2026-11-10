# Postmortem: worker dừng 3 giờ, báo cáo doanh thu sai, không có alert (2026-09-30)

## 1. Tóm tắt

Từ 13:20 tới 16:25 ngày 2026-09-30, worker của Olist Shop không xử lý job nào vì kết nối Redis bị treo sau khi Redis được nâng cấp. Báo
cáo doanh thu theo bang trên trang quản trị đứng yên ở số liệu buổi trưa, đội kinh doanh dùng số đó để chốt khuyến mãi. Alert
`OlistWorkerNoProgress` đã có từ tháng 8 nhưng chưa bao giờ được Prometheus nạp: tệp rule được đổi tên sang đuôi `.yaml` trong một lần dọn
repo, còn `rule_files` chỉ đọc `*.yml`. Phát hiện nhờ đội kinh doanh hỏi trong kênh chung; khởi động lại worker và sửa glob trong ngày.

## 2. Tác động

- 185 phút báo cáo doanh thu không cập nhật; khoảng 6.300 đơn không được tính vào báo cáo trong thời gian đó.
- Đội kinh doanh chốt một khuyến mãi dựa trên số liệu cũ; khách không bị ảnh hưởng trực tiếp, API vẫn trả đơn bình thường.
- Không mất dữ liệu: job còn trong hàng đợi và được xử lý sau khi worker chạy lại.

## 3. Timeline

| Giờ | Sự kiện |
| --- | --- |
| 13:05 | Nâng cấp Redis theo kế hoạch, failover 20 giây |
| 13:20 | Worker treo trên kết nối cũ, không lấy job |
| 14:00 | Dashboard worker cho thấy jobs_processed_total đứng yên; không ai xem |
| 15:50 | Đội kinh doanh hỏi vì sao doanh thu bang SP không đổi từ trưa |
| 16:02 | Người trực xác nhận worker không xử lý job |
| 16:10 | Khởi động lại worker, hàng đợi bắt đầu giảm |
| 16:25 | Hàng đợi về 0, báo cáo cập nhật |
| 17:30 | Tìm ra rule không được nạp, sửa glob, kiểm trên Prometheus |

## 4. Nguyên nhân gốc và yếu tố góp phần

- Worker không có timeout đọc và không tự kết nối lại sau failover của Redis.
- Tệp rule đổi đuôi `.yaml`; `rule_files` chỉ khớp `*.yml`, Prometheus không báo lỗi khi glob không khớp tệp nào.
- CI chạy `promtool check rules` trên tệp, không kiểm rule đã được nạp trên Prometheus thật.
- Không có alert về chính số rule đã nạp.

## 5. Phát hiện và xử lý

Con người biết sau 150 phút, qua câu hỏi của đội kinh doanh, không phải qua alert. Không cần quay lại bản trước; khởi động lại worker là đủ.

## 6. Điều chạy tốt và chưa tốt

- Tốt: hàng đợi giữ job, không mất dữ liệu.
- Chưa tốt: Watchdog vẫn bắn đều nên mọi người tin hệ thống alert ổn, dù một nhóm rule không tồn tại.
- Chưa tốt: dashboard có tín hiệu từ 14:00 nhưng không ai xem.

## 7. Bài học

- Alert chưa từng bắn là alert chưa được chứng minh.
- Kiểm cấu hình trên hệ thống thật, không chỉ cú pháp.
- Theo dõi chính hệ thống alert ở mức từng rule.

## 8. Action items

| Việc | Người phụ trách | Hạn | Loại |
| --- | --- | --- | --- |
| Timeout và reconnect cho worker | Minh | 2026-10-07 | phòng ngừa |
| Glob `*.y*ml` và test CI hỏi `/api/v1/rules` của Prometheus staging | Lan | 2026-10-10 | phát hiện |
| Alert khi số rule đã nạp giảm | Lan | 2026-10-10 | phát hiện |
| Diễn tập alert hằng tháng: bắn thử từng alert page | Huy | 2026-10-31 | phát hiện |
| Thêm báo cáo "cập nhật lần cuối" lên trang quản trị | Mai | 2026-10-15 | giảm thiểu |
