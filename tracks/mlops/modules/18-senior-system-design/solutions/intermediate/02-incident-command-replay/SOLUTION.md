# Lời giải: hồ sơ sự cố ETA 2026-10-14

`incident.yaml` cạnh tệp này là bản mẫu đã qua test.

## Các giá trị đo được

- `started_at` **13:05**: phút đầu tiên tỉ lệ lỗi vượt 2% (14.6%). 12:41 có 1.8% và 13:04 có 1.6%, đều dưới ngưỡng: một spike đơn lẻ và
  lúc bản mới mới lên một phần pod.
- `detected_at` **13:09**: `ETAErrorBudgetFastBurn` firing. `DiskSpaceLow` lúc 12:10 là của `batch-scoring`, không liên quan.
- `mitigated_at` **13:49**: 13:47 còn 6.1%, 13:48 còn 2.4% (rollout ngược đang chạy), từ 13:49 luôn dưới 1%.
- TTD 4 phút, TTM 44 phút. `failed_requests` 6 385, tức 2.96% của budget 216 000 yêu cầu lỗi trong 30 ngày, nên **SEV2** (phút tệ
  nhất là đợt restart 13:21-13:22, khoảng 31%, dưới 50%).
- `trigger` **mdl-207** (model v41 sang v42 lúc 13:03), `decision` **rollback** (mdl-208 lúc 13:46).
- Vai trò: IC `my`, comms `son`, ops `hai`.

## Những điều cần thấy trong kênh chat

- **Giả thuyết sai có lý:** bảo trì feature store 13:00-13:15 trùng giờ. Hỏi chủ store và nhận câu trả lời có bằng chứng trong 5 phút là
  cách đúng để loại nó. Dấu hiệu khác: store xong lúc 13:12 mà lỗi vẫn giữ nguyên.
- **Hành động không tác dụng nhưng rẻ:** restart lúc 13:21 làm tình hình tệ hơn trong hai phút (mất 40% traffic, lỗi tăng) rồi về như cũ.
  Restart loại được giả thuyết "trạng thái bẩn" nhanh; nó nên được làm *sau* khi đã đối chiếu `deploys.log`, vì một deploy model hai phút
  trước khi lỗi bắt đầu là nghi phạm số một. Ở đây đội mất khoảng 15 phút (13:20 tới 13:35) vì thứ tự đó.
- **Phân vai:** người on-call (`hai`) giao IC cho người khác để giữ tay debug. IC điều phối và quyết định (`quay về model trước`), comms
  cập nhật đều đặn kể cả khi chưa có tin mới. Người debug mà làm IC thì không ai nhìn bức tranh chung, và cập nhật cho bên ngoài ngừng đúng
  lúc cần nhất.
- **Giảm thiểu trước, tìm gốc sau:** quyết định rollback lúc 13:37 khi đã thấy `ValueError` từ model mới; không chờ sửa model.

## Rubric cho `next_steps` (tự chấm, 10 điểm)

| Mục | Điểm | Đạt khi |
| --- | --- | --- |
| Ngăn chặn | 3 | cổng promotion hoặc test chặn được input thiếu như `passenger_count` trống |
| Phát hiện hoặc giảm thiệt hại | 3 | canary tự rollback theo tỉ lệ lỗi của bản mới, hay alert theo phiên bản |
| Quy trình | 2 | runbook đối chiếu deploy trước khi restart; postmortem có hạn |
| Có chủ | 2 | mỗi việc có vai trò hay đội chịu trách nhiệm |
