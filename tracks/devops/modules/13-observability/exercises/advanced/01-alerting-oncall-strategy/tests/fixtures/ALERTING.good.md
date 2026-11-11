# Chiến lược alert và on-call cho Olist Seller Portal

## 1. Nguyên tắc

Seller Portal là web app cho người bán của Olist cập nhật tồn kho, giá và xem đơn. Hai service (`seller-web`, `seller-sync` đồng bộ tồn kho
sang marketplace), một Postgres. Người bán dùng chủ yếu 07:00-23:00. Team 4 người, trực theo tuần.

- Page chỉ khi người bán không làm được việc chính (đăng nhập, cập nhật tồn kho) hoặc tồn kho lệch với marketplace: đó là triệu chứng.
- Mỗi page có runbook và một hành động đầu tiên rõ ràng; alert không hành động được thì thành ticket.
- Ngoài 07:00-23:00, chỉ page khi đồng bộ tồn kho dừng, vì đơn vẫn đổ về từ marketplace.

## 2. Danh mục alert

| Alert | Service | Tín hiệu | Severity | Receiver | Runbook |
| --- | --- | --- | --- | --- | --- |
| OlistServiceDown | seller-web | probe `/healthz` thất bại từ hai vùng, 3 phút | page | seller-oncall | https://runbooks.seller.example/down |
| SellerLoginErrors | seller-web | tỉ lệ đăng nhập lỗi 5xx trên 10%, 10 phút | page | seller-oncall | https://runbooks.seller.example/login |
| SellerSyncStalled | seller-sync | `time() - seller_sync_last_success_timestamp_seconds > 1800` | page | seller-oncall | https://runbooks.seller.example/sync |
| SellerSlowPages | seller-web | p95 trang tồn kho trên 2 giây, 30 phút | ticket | seller-backlog | https://runbooks.seller.example/slow |
| SellerSyncRetries | seller-sync | tỉ lệ retry khi gọi marketplace trên 20%, 1 giờ | ticket | seller-backlog | https://runbooks.seller.example/retries |
| Watchdog | - | `vector(1)` | none | heartbeat | https://runbooks.seller.example/watchdog |

## 3. Routing, grouping, inhibition

- `group_by: [alertname, service]` ở route gốc; route theo `severity` tới `seller-oncall` hay `seller-backlog`; nhãn lạ về `default`.
- Inhibit: `OlistServiceDown` chặn alert khác của cùng service (`equal: [service]`).
- Watchdog tới `heartbeat` mỗi phút; dịch vụ heartbeat bên ngoài page khi im 5 phút (deadman switch).

## 4. On-call

- Lịch luân phiên tuần, bàn giao thứ Ba 09:30, có người dự phòng.
- Leo thang sau 15 phút không ack: người dự phòng, rồi engineering manager.
- Handoff ghi lại alert trong tuần, silence đang bật, runbook cần sửa.
- Nghỉ bù sau đêm bị page.

## 5. Đo chất lượng alert

- Số page mỗi tuần, tách trong giờ và ngoài giờ.
- Tỉ lệ page actionable, xem lại mỗi tháng; dưới 75% thì sửa hay xoá alert nhiễu.
- Sự cố người bán báo trước alert được tính là alert bỏ sót.

## 6. Rủi ro và giới hạn

- Probe từ hai vùng tốn tiền và có thể cùng lỗi khi DNS lỗi.
- Ngưỡng tỉ lệ lỗi không hợp khi ít người dùng ban đêm.
- Heartbeat không chứng minh pager hoạt động; thử page mỗi lần bàn giao.
