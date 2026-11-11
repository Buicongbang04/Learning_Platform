# Postmortem: game day dịch vụ ví dụ

## 1. Tóm tắt

Game day ngày 2026-11-04 với seed 31 trên môi trường lab. Injector làm database ngừng nhận kết nối, khiến mọi request đọc dữ liệu
trả 500 trong khoảng một phút rưỡi. Runbook phát hiện đúng sau 12 giây và khôi phục bằng một lệnh, nhưng lộ ra rằng dashboard không
cho biết database tắt hay chỉ quá tải, và bước xác nhận của runbook phụ thuộc một người nhớ cách đọc panel.

## 2. Tác động

Khoảng 85 giây, 100% request đọc dữ liệu lỗi, khoảng 400 request. Với SLO 99,5% trong 30 ngày, lần này tiêu khoảng 0,7% error budget
của tháng. Không mất dữ liệu.

## 3. Timeline

| Giờ | Sự kiện |
| --- | --- |
| 14:02:10 | Bắt đầu game day, xác nhận trạng thái ổn định |
| 14:02:40 | Injector bơm lỗi |
| 14:02:52 | Entry `db-down` khớp |
| 14:02:53 | Chạy hành động start postgres |
| 14:04:05 | Traffic khoẻ 10 giây liên tục, kết thúc |

## 4. Nguyên nhân

- Container database dừng đột ngột; ứng dụng không có retry nên lỗi lan ngay ra khách.
- Không có healthcheck và restart policy nên không gì tự khởi động lại.

## 5. Phát hiện và khôi phục

Entry `db-down` của runbook phát hiện qua metric `pg_up`, hành động start postgres khôi phục trong 72 giây, phần lớn là thời gian ứng
dụng mở lại pool kết nối.

## 6. Bài học

- Phát hiện nhanh vì metric đo đúng thứ bị hỏng.
- Bước xác nhận cần số liệu cụ thể chứ không phải "xem dashboard".
- Ứng dụng nên retry có giới hạn khi mất kết nối database.

## 7. Action items

| Việc | Người phụ trách | Hạn |
| --- | --- | --- |
| Thêm healthcheck và restart policy cho database | Team platform | 2026-11-18 |
| Retry có backoff khi mở kết nối | Team checkout | 2026-11-25 |
| Panel "database sống hay chết" trên dashboard RED | Team platform | 2026-11-20 |
