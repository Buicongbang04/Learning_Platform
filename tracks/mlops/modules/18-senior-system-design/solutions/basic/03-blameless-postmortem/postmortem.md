# Postmortem: feature trip_stats cũ hơn 3 giờ, ETA sai giờ cao điểm

## 1. Tóm tắt

Từ 14:05 đến 17:15 ngày 2026-10-21, feature `trip_stats` mà service ETA dùng không được cập nhật vì job materialize không còn quyền
đọc object store sau một đợt xoay vòng credential định kỳ. Service vẫn trả 200 và nhanh, nhưng dự đoán dựa trên tình trạng đường
xá của buổi trưa nên ETA giờ cao điểm chiều lệch nhiều. Không alert nào bắn; sự cố được biết qua ticket hỗ trợ. Đã khắc phục bằng
cách cấp lại credential và chạy lại job; hiện freshness bình thường và có alert burn rate freshness.

## 2. Tác động

- 190 phút feature cũ hơn ngưỡng 15 phút (14:05 đến 17:15).
- Khoảng 412 000 dự đoán dùng feature cũ; MAE trên nhãn đã về tăng từ 3.1 lên 4.6 phút (+48%), nặng nhất ở Manhattan 16:00-17:00.
- Error budget freshness 30 ngày (SLO 99%, tức 432 phút): tiêu 190/432 = 44% trong một sự cố.
- Không có lỗi HTTP: SLO khả dụng và độ trễ vẫn xanh suốt sự cố.

## 3. Dòng thời gian

| Thời điểm | Sự kiện |
| --- | --- |
| 13:58 | Kỹ sư nền tảng xoay vòng credential object store theo lịch quý; secret của job feature không nằm trong danh sách cập nhật |
| 14:05 | Job materialize `trip_stats` nhận 403, thử lại 3 lần, đánh dấu `skipped` và thoát mã 0; orchestrator hiện xanh. **Bắt đầu tác động** |
| 15:30 | Dashboard MAE (nhãn trễ 1 giờ) bắt đầu đi lên; không có alert trên chỉ số này |
| 16:40 | Ticket hỗ trợ: tài xế báo ETA sai ở Manhattan; on-call nhận |
| 16:52 | On-call thấy log 403 của job, tuyên bố sự cố SEV3, giữ vai trò incident commander; một kỹ sư khác nhận vai trò comms |
| 17:05 | Kỹ sư nền tảng cập nhật secret cho job; job chạy lại |
| 17:15 | `trip_stats` tươi trở lại (tuổi dưới 15 phút). **Hết tác động** |
| 18:30 | MAE trên nhãn mới về trở lại 3.1 phút; IC đóng sự cố |

## 4. Nguyên nhân gốc và yếu tố góp phần

- Nguyên nhân gốc: xoay vòng credential dựa trên một danh sách secret ghi tay; secret của job feature không có trong danh sách,
  nên quy trình không có cách nào biết job sẽ mất quyền.
- Job coi lỗi quyền (403) như lỗi tạm thời, hết retry thì `skipped` và thoát mã 0: orchestrator không phân biệt "không có dữ liệu mới"
  với "không đọc được dữ liệu".
- Không có SLI freshness: SLO chỉ đo khả dụng và độ trễ ở phía service, cả hai đều xanh trong khi người dùng nhận ETA sai.
- Service đọc feature không kiểm tuổi, không có fallback (vd. dùng model không cần `trip_stats` khi feature quá cũ).
- Alert chất lượng không tồn tại; dashboard MAE có tín hiệu từ 15:30 nhưng không ai được gọi.

## 5. Điều đã tốt, điều may mắn

- Điều tốt: job chạy lại idempotent, sửa xong là dữ liệu đúng ngay; on-call phân vai IC và comms trong 12 phút sau khi nhận ticket.
- Điều tốt: log của job ghi rõ mã 403, khoanh vùng nhanh.
- May mắn: sự cố bắt đầu sau giờ cao điểm trưa; nếu xoay vòng lúc 7 giờ sáng thì cả hai giờ cao điểm đều bị ảnh hưởng.

## 6. Hành động

| Hành động | Loại | Chủ sở hữu | Hạn | Cách kiểm |
| --- | --- | --- | --- | --- |
| Sinh danh sách secret cần xoay vòng từ manifest triển khai thay vì danh sách ghi tay | ngăn chặn | Đội nền tảng | 2026-11-15 | Diễn tập xoay vòng trên staging, mọi job vẫn chạy |
| Job trả mã khác 0 khi lỗi 4xx, chỉ retry lỗi 5xx và timeout | ngăn chặn | Chủ pipeline feature | 2026-11-01 | Test tích hợp với object store trả 403 làm job fail |
| Thêm SLI freshness và alert burn rate `ETAFeatureFreshnessFastBurn` | phát hiện | Chủ model ETA | 2026-10-28 | `promtool test rules` với kịch bản ngừng 40 phút bắn trong 30 phút |
| Alert chất lượng burn rate trên MAE theo nhãn | phát hiện | Chủ model ETA | 2026-11-08 | Phát lại dữ liệu ngày 2026-10-21, alert bắn trước 16:00 |
| Service kiểm tuổi feature, quá 30 phút thì dùng model dự phòng không cần `trip_stats` | giảm thiệt hại | Đội serving | 2026-11-22 | Canary với feature giả cũ 1 giờ, MAE không tăng quá 15% |
