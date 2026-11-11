# Chiến lược alert và on-call cho Olist Shop

## 1. Nguyên tắc

Olist Shop có API (đặt hàng, tra đơn), worker (tính lại doanh thu từ hàng đợi Redis), Postgres và Redis. Team 6 kỹ sư, giờ làm việc
08:00-18:00, khách đặt hàng cả ngày lẫn đêm. Mục tiêu của bộ alert: người trực chỉ bị đánh thức khi khách đang bị ảnh hưởng hoặc sắp bị
trong vài chục phút, và mỗi lần bị đánh thức đều có việc cụ thể để làm.

- Page theo triệu chứng người dùng thấy (lỗi, chậm, không đặt được hàng, job tồn đọng làm số liệu sai), không page theo nguyên nhân
  (CPU, RAM, đĩa). Nguyên nhân nằm trên dashboard và trong ticket.
- Mỗi alert page phải hành động được và có runbook: alert nào người trực nhận xong chỉ "xem rồi để đó" thì hạ xuống ticket hay xoá.
- Ba mức: `page` đánh thức người trực, `ticket` tạo việc trong giờ làm, `none` chỉ cho Watchdog. Không có mức "warning gửi vào kênh chat"
  vì kênh chat bị bỏ qua sau một tuần.
- `for` đủ dài để lọc dao động ngắn (5 phút cho page, 10 tới 30 phút cho ticket) nhưng không dài tới mức khách phát hiện trước.
- Alert của chính hệ thống alert (Watchdog, Prometheus không scrape được) là bắt buộc: một hệ thống alert im lặng trông giống hệt một hệ
  thống khoẻ.

## 2. Danh mục alert

| Alert | Service | Tín hiệu | Severity | Receiver | Runbook |
| --- | --- | --- | --- | --- | --- |
| OlistServiceDown | olist-api | `up{job="olist-api"} == 0` trên mọi instance, hoặc probe `/healthz` thất bại, 2 phút | page | oncall-pager | https://runbooks.olist-shop.example/service-down |
| OlistApiHighErrorRate | olist-api | `job:http_requests_errors:ratio_rate5m{job="olist-api"} > 0.05`, 5 phút | page | oncall-pager | https://runbooks.olist-shop.example/api-high-error-rate |
| OlistCheckoutLatencyHigh | olist-api | p95 của route đặt hàng trên 1 giây, 10 phút | page | oncall-pager | https://runbooks.olist-shop.example/checkout-latency |
| OlistWorkerJobsFailing | olist-worker | `rate(jobs_failed_total[10m]) / (rate(jobs_processed_total[10m]) + rate(jobs_failed_total[10m])) > 0.2`, 10 phút | page | oncall-pager | https://runbooks.olist-shop.example/worker-jobs-failing |
| OlistApiSlowOrders | olist-api | p95 của `/orders/{order_id}` trên 0,5 giây, 10 phút | ticket | shop-tickets | https://runbooks.olist-shop.example/api-slow-orders |
| OlistWorkerNoProgress | olist-worker | Có job được đẩy (`increase(jobs_enqueued_total[30m]) > 0`) mà `increase(jobs_processed_total[30m]) == 0` | ticket | shop-tickets | https://runbooks.olist-shop.example/worker-no-progress |
| OlistPostgresDiskFillingUp | olist-postgres | `predict_linear(...[6h], 3 * 86400) < 0` trên volume của Postgres | ticket | shop-tickets | https://runbooks.olist-shop.example/postgres-disk |
| OlistScrapeFailing | prometheus | `up == 0` cho bất kỳ target nào khác API, 15 phút | ticket | shop-tickets | https://runbooks.olist-shop.example/scrape-failing |
| Watchdog | - | `vector(1)`, luôn bắn | none | deadman | https://runbooks.olist-shop.example/watchdog |

Ghi chú: `OlistPostgresDiskFillingUp` là alert theo nguyên nhân nhưng có thời gian báo trước ba ngày, nên chỉ là ticket. SLO và burn-rate
alert thay cho các ngưỡng cố định ở trên là việc của module 16.

## 3. Routing, grouping, inhibition

- Route gốc `group_by: [alertname, service]`: mười pod cùng lỗi thành một thông báo, nhưng hai service khác nhau không bị gộp.
- Route `severity="page"` tới `oncall-pager`, `group_wait: 30s`, `repeat_interval: 2h`; `severity="ticket"` tới `shop-tickets`,
  `group_wait: 5m`, `repeat_interval: 24h`. Mọi thứ khác (thiếu `severity`, viết sai hoa thường) rơi về `default`, một kênh triage được
  xem mỗi sáng: không mất alert, cũng không đánh thức ai vì một nhãn gõ sai.
- Inhibit: khi `OlistServiceDown` bắn cho một service, mọi alert khác của **cùng** service (`equal: [service]`) bị chặn; người trực nhận
  một thông báo "API chết" thay vì năm thông báo về lỗi, độ trễ, worker. Alert của service khác vẫn đi bình thường.
- Inhibit thứ hai: page chặn ticket cùng `alertname` và `service`, để một sự cố không vừa page vừa tạo ticket trùng.
- Watchdog đi route riêng tới `deadman`, `repeat_interval: 1m`, gửi heartbeat tới dịch vụ bên ngoài (Healthchecks.io, Dead Man's Snitch,
  tính năng heartbeat của PagerDuty/Opsgenie). Heartbeat ngừng 5 phút thì dịch vụ đó page người trực: đường Prometheus → Alertmanager →
  receiver đã đứt.
- Bảo trì có kế hoạch dùng silence có matcher hẹp và thời hạn, tạo bằng `amtool silence add` kèm người tạo và lý do, không sửa routing.

## 4. On-call

- Lịch luân phiên tuần, thứ Hai 10:00 bàn giao; 6 người nên mỗi người trực một tuần mỗi tháng rưỡi. Có người trực chính và người dự phòng.
- Leo thang: page không được ack trong 10 phút thì gọi người dự phòng; thêm 15 phút thì gọi tech lead. Pager gọi điện, không chỉ push.
- Bàn giao (handoff) 15 phút: alert đã bắn trong tuần, silence còn hiệu lực, việc dở dang, runbook cần sửa. Ghi lại trong kênh on-call.
- Người trực được bù: nghỉ bù sau đêm bị page, không nhận việc tính năng trong tuần trực để sửa alert nhiễu và runbook.
- Page ngoài giờ chỉ cho mức `page`; ticket chờ tới giờ làm.
- Mỗi sự cố mức cao có postmortem không đổ lỗi trong 5 ngày làm việc.

## 5. Đo chất lượng alert

- Đếm số page mỗi tuần và mỗi ca trực; mục tiêu dưới 2 page ngoài giờ mỗi tuần (Google SRE gợi ý tối đa khoảng 2 sự cố mỗi ca 12 giờ).
- Mỗi page được gắn nhãn khi đóng: actionable hay không, có đúng runbook không. Tỉ lệ page actionable dưới 80% trong một tháng thì xem lại
  ngưỡng hay hạ mức.
- Alert bắn rồi tự hết dưới 5 phút nhiều lần (flapping) là nhiễu: tăng `for`, đổi cửa sổ, hay xoá.
- Mỗi sự cố khách báo trước khi alert bắn được tính là một "alert bỏ sót" và phải có action item thêm hay sửa alert.
- Review bộ alert mỗi tháng trong buổi họp vận hành: alert nào không bắn 6 tháng thì kiểm lại bằng test hay xoá.

## 6. Rủi ro và giới hạn

- Ngưỡng cố định (5% lỗi, p95 1 giây) không biết lượng traffic: đêm ít request, vài lỗi đã quá 5%. Burn-rate theo SLO (module 16) xử lý
  việc này tốt hơn.
- `amtool config routes test` không mô phỏng inhibit; mỗi thay đổi `inhibit_rules` phải được kiểm trên Alertmanager thật với alert giả
  (như test của bài này) trước khi lên production.
- Rule có thể không khớp dữ liệu thật (sai tên label) và im lặng mãi; cần test rule trên dữ liệu thật trong CI và alert về rule không trả
  series nào.
- Webhook pager là điểm lỗi đơn; Watchdog chỉ chứng minh Alertmanager gửi được tới dịch vụ heartbeat, không chứng minh pager hoạt động. Thử
  page thật mỗi tuần lúc bàn giao.
- Team nhỏ: một người nghỉ phép làm lịch trực dày lên; cần người dự phòng từ team khác hay giảm phạm vi page.
