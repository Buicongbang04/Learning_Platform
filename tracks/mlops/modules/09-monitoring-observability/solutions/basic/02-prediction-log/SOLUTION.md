# Lời giải: log dự đoán và nối nhãn

## Ý chính

- **Log là nơi chứa chi tiết từng yêu cầu.** Metric gom lại và rẻ nhưng không truy ngược được; log giữ từng yêu cầu với
  `request_id`, phiên bản model và feature để sau vài giờ hoặc vài ngày, khi nhãn về, ta tính được MAE thật theo phiên bản
  và slice. Đây là thứ duy nhất đo được chất lượng model trong production khi nhãn về muộn.
- **Allow-list thay vì deny-list.** Danh sách cấm luôn thiếu một trường mới; danh sách cho phép thì trường mới mặc định ra
  ngoài log cho tới khi có người chủ động thêm.
- **UTC và có múi giờ.** Nối log với nhãn thường chéo nhiều hệ thống; `ts` không múi giờ là nguồn của lỗi lệch 7 tiếng.
- **Join có kế toán.** Ba con số `unmatched_predictions`, `orphan_labels`, `bad_lines` là tín hiệu sức khoẻ của pipeline nhãn:
  `orphan_labels` tăng thường nghĩa là log bị mất hoặc `request_id` bị đổi giữa các hệ thống; `unmatched_predictions` giảm dần
  theo thời gian là bình thường. Đừng nuốt im lặng.
- **Dedupe theo `ts` mới nhất.** Retry của client tạo hai dòng cùng `request_id`; đếm cả hai làm lệch MAE.

## Lỗi hay gặp

- So sánh `ts` bằng chuỗi chỉ đúng khi cùng định dạng và cùng UTC; vì hàm ghi luôn ra `...Z`, so chuỗi cũng là so thời gian.
- Ghi log bằng `print(dict)` (dấu nháy đơn, `NaN`): không phải JSON hợp lệ, công cụ parse log hỏng.
- Log cả thân yêu cầu cho tiện: vi phạm quyền riêng tư và làm log phình; chọn trước các trường cần.
