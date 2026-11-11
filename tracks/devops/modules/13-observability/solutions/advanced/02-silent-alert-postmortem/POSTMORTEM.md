# Postmortem: API Olist Shop lỗi 503, không có page (2026-10-21)

## 1. Tóm tắt

Tối 2026-10-21, bản API v2.14 giảm pool kết nối Postgres, làm khoảng 35% request đặt hàng và tra đơn trả 503 từ 21:02 tới 21:58. Prometheus
phát hiện đúng: `OlistApiHighErrorRate` bắn lúc 21:09 và `OlistCheckoutLatencyHigh` lúc 21:14. Nhưng Alertmanager chặn cả hai, vì một luật
inhibit do team Search thêm ba tuần trước biến alert `MaintenanceMode` (đang bắn cho đợt reindex của `olist-search`) thành nguồn chặn mọi
alert page và ticket của **mọi** service: luật thiếu `equal`. Người trực chỉ biết khi team chăm sóc khách hàng báo lúc 21:38, rollback lúc
21:52. Luật inhibit đã được thay bằng silence có phạm vi, và từ nay mọi thay đổi `inhibit_rules` được kiểm trên một Alertmanager thật.

## 2. Tác động

- 56 phút (21:02 tới 21:58) khoảng 35% request tới API trả 503; trang đặt hàng và tra đơn bị ảnh hưởng.
- Khoảng 1.900 đơn đặt hàng thất bại (95 lượt đặt mỗi phút × 56 phút × 35%); khoảng 60% khách thử lại thành công sau 22:00, ước tính
  760 đơn mất hẳn. 32 ticket khách hàng trong nửa giờ.
- Không mất dữ liệu đơn đã ghi. Không ảnh hưởng `olist-search` hay worker.
- Ảnh hưởng ngầm: trong mọi đợt bảo trì của Search từ 2026-09-30, mọi alert page và ticket của mọi service đều bị chặn. Đã xác nhận một lần
  (2026-10-08, ticket đĩa Postgres không được tạo).

## 3. Timeline

| Giờ | Sự kiện |
| --- | --- |
| 18:02 | `MaintenanceMode{service="olist-search"}` bắt đầu bắn (reindex có kế hoạch tới 02:00) |
| 20:47 | Deploy API v2.14 (đổi pool kết nối Postgres), canary 5 phút không lỗi |
| 21:02 | API bắt đầu trả 503 cho khoảng 35% request (`QueuePool limit ... reached`) |
| 21:09 | `OlistApiHighErrorRate` firing, tới Alertmanager, bị inhibit bởi `MaintenanceMode`; không có page |
| 21:14 | `OlistCheckoutLatencyHigh` firing, cũng bị inhibit |
| 21:38 | CSKH báo 32 ticket "không đặt được hàng" trong #olist-ops |
| 21:41 | Người trực mở Grafana: 5xx 34,8%; Alertmanager hiện alert `suppressed` |
| 21:52 | Rollback API về v2.13 |
| 21:58 | Tỉ lệ 5xx dưới 1%, hết ảnh hưởng |
| 22:10 | Đọc cấu hình Alertmanager, tìm ra luật inhibit thứ hai không có `equal` |
| 22:25 | Thay luật đó bằng silence `service="olist-search"` có hạn tới 02:30; reload Alertmanager |
| 22:40 | `amtool alert add` một alert thử: pager rung |
| 23:00 | Đóng sự cố |

## 4. Nguyên nhân gốc và yếu tố góp phần

- **Nguyên nhân trực tiếp của lỗi khách thấy**: v2.14 đặt pool kết nối 5, overflow 0; traffic tối vượt khả năng của pool. Canary 5 phút
  với traffic thấp không bộc lộ.
- **Nguyên nhân gốc của việc không ai bị page**: luật inhibit `source_matchers: [alertname="MaintenanceMode"]`,
  `target_matchers: [severity=~"page|ticket"]` không có `equal`. Không có `equal`, Alertmanager coi mọi alert khớp target là "cùng nhóm"
  với nguồn, nên một alert bảo trì của `olist-search` chặn alert của mọi service. `inhibitedBy` của `OlistApiHighErrorRate` trỏ đúng
  fingerprint `3f1c9a7e52b0d6a4` của `MaintenanceMode`.
- **Bảo trì mô hình hoá sai công cụ**: "đừng làm phiền trong lúc bảo trì" là việc của silence (có matcher, có người tạo, có hạn), không phải
  một luật inhibit thường trực kích hoạt bằng metric.
- **CI và review chỉ kiểm cú pháp**: `amtool check-config` qua; `amtool config routes test` không mô phỏng inhibit; không có test gửi alert
  giả tới một Alertmanager thật. Người duyệt cùng team Search, không ai của team sở hữu routing chung xem PR.
- **Giám sát hệ thống alert không phủ bước inhibit**: Watchdog đi route riêng và không khớp target (`severity="none"`), nên heartbeat vẫn
  đều. Không có alert về số alert bị suppress.

## 5. Phát hiện và xử lý

- Con người biết sau 36 phút kể từ khi lỗi bắt đầu (21:02 tới 21:38), qua khách hàng, không qua alert. Alert đã bắn đúng sau 7 phút
  (21:09); nếu page tới, người trực có thể biết sớm hơn khoảng 29 phút.
- Từ lúc biết tới khi hết ảnh hưởng: 20 phút (21:38 tới 21:58). Thứ tự xử lý: xác nhận trên Grafana, rollback API (giảm thiểu trước), rồi
  mới tìm vì sao alert im lặng.
- Sửa luật inhibit trong lúc `MaintenanceMode` vẫn bắn: thay bằng silence có phạm vi `service="olist-search"` để team Search vẫn không bị
  làm phiền, rồi gửi alert thử để chứng minh đường page đã thông.

## 6. Điều chạy tốt và chưa tốt

- Tốt: rule Prometheus đúng và bắn nhanh; dashboard và log cho thấy nguyên nhân trong vài phút; rollback một lệnh.
- Tốt: CSKH có kênh báo nhanh vào #olist-ops.
- Chưa tốt: Watchdog và heartbeat cho cảm giác an toàn sai: chúng chứng minh Alertmanager sống, không chứng minh alert của Olist Shop tới
  được người trực.
- Chưa tốt: đợt bảo trì ngày 2026-10-08 đã chặn một ticket mà không ai thấy; tín hiệu cảnh báo sớm bị bỏ lỡ.
- Chưa tốt: cấu hình Alertmanager dùng chung không có chủ sở hữu rõ ràng.

## 7. Bài học

- Một alert bị chặn trông giống hệt một hệ thống khoẻ; phải đo cả alert bị suppress, không chỉ alert đang bắn.
- Cú pháp đúng không phải hành vi đúng: inhibit và route phải được kiểm bằng alert giả trên Alertmanager thật.
- Cấu hình dùng chung cần chủ sở hữu và người duyệt từ team bị ảnh hưởng.
- Bảo trì là silence có hạn, không phải luật thường trực.

## 8. Action items

| Việc | Người phụ trách | Hạn | Loại |
| --- | --- | --- | --- |
| Bỏ luật inhibit `MaintenanceMode`; bảo trì dùng silence có matcher `service`, người tạo, hạn (script `amtool silence add` trong runbook bảo trì) | Platform (An) | 2026-10-24 | phòng ngừa |
| Lint CI: mọi `inhibit_rules` phải có `equal` chứa `service` | Platform (An) | 2026-10-28 | phòng ngừa |
| Test CI dựng Alertmanager thật, gửi alert giả và kiểm route, inhibit (như bài Advanced 01) | Platform (Bình) | 2026-11-07 | phát hiện |
| Alert khi số alert page bị suppress khác 0 quá 10 phút (`alertmanager_alerts{state="suppressed"}`) | SRE (Chi) | 2026-10-31 | phát hiện |
| CODEOWNERS cho cấu hình Alertmanager chung: team Platform duyệt bắt buộc | Platform (An) | 2026-10-24 | quy trình |
| Diễn tập page hằng tuần lúc bàn giao: `amtool alert add` một alert page thử, xác nhận pager rung | On-call (luân phiên) | 2026-10-27 | phát hiện |
| Pool kết nối theo số worker uvicorn và canary đủ 30 phút hay theo số request | Olist Shop (Dũng) | 2026-11-04 | phòng ngừa |
