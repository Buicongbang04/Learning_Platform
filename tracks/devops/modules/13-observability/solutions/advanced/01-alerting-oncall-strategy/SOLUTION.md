# Lời giải: chiến lược alert và on-call cho Olist Shop

Bài không có một đáp án duy nhất. `ALERTING.md` và `alertmanager.yml` trong thư mục này là một lời giải qua test; rubric bên dưới chấm
nội dung.

## Hướng làm

1. Liệt kê hành trình của khách: xem đơn, đặt hàng, nhận số liệu đúng. Mỗi hành trình một hai tín hiệu triệu chứng (lỗi, chậm, không có
   tiến triển). Đó là ứng viên page.
2. Liệt kê nguyên nhân hay gặp (đĩa, CPU, pool kết nối, scrape lỗi). Cái nào báo trước được đủ lâu thì thành ticket; còn lại để trên
   dashboard.
3. Thêm alert về chính hệ thống alert: Watchdog có heartbeat ra ngoài, scrape lỗi.
4. Viết route theo `severity`, route gốc là chỗ rơi về an toàn, Watchdog route riêng với `repeat_interval` ngắn.
5. Viết inhibit cho trường hợp "cả service chết" với `equal: [service]`, rồi kiểm trên Alertmanager thật.
6. Viết quy trình trực, cách đo, và giới hạn.

## Các quyết định cần cân nhắc

| Quyết định | Lựa chọn trong lời giải mẫu | Đánh đổi |
| --- | --- | --- |
| Số mức severity | 3: `page`, `ticket`, `none` | Thêm `warning` vào chat thường thành kênh không ai đọc; ít mức thì mỗi mức có hành động rõ |
| Page theo triệu chứng | Lỗi, chậm, worker lỗi, service down | Không page theo CPU: tránh nhiễu, nhưng phát hiện muộn hơn những sự cố do tài nguyên cạn dần |
| `group_by` | `[alertname, service]` | Gộp theo instance mất thông tin pod nào; không gộp thì một sự cố mười pod thành mười page |
| Nơi rơi về | Receiver `default` là kênh triage | Không bỏ mất alert do nhãn sai, nhưng phải có người xem kênh mỗi sáng |
| Inhibit | `OlistServiceDown` chặn alert khác cùng `service` | `equal` quá rộng thì im cả hệ thống; quá hẹp thì không chặn được gì. Phải kiểm trên Alertmanager thật |
| Deadman | Watchdog tới heartbeat bên ngoài | Thêm một dịch vụ phụ thuộc, nhưng là cách duy nhất biết Alertmanager hay Prometheus đã chết |
| Lịch trực | Tuần, có người dự phòng, leo thang 10/25 phút | Team 6 người nên tải trực cao; cần giới hạn số page và nghỉ bù |

## Rubric (10 điểm)

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Alert page theo triệu chứng | 2 | Mọi page gắn với điều khách thấy hay sắp thấy; giải thích được vì sao từng alert nguyên nhân chỉ là ticket hay dashboard |
| Mỗi page hành động được | 1 | Có runbook, nói được việc đầu tiên người trực làm; `for` và cửa sổ hợp lý (không page vì một lần lỗi) |
| Routing và nơi rơi về | 1 | Nhãn lạ không page và không bị bỏ mất; `group_by` có lý do |
| Inhibition đúng phạm vi | 1,5 | Inhibit có `equal`, giải thích được điều gì xảy ra nếu bỏ `equal`; đã thử trên Alertmanager thật |
| Giám sát chính hệ thống alert | 1 | Watchdog/deadman ra bên ngoài, alert khi scrape lỗi; nói được giới hạn (heartbeat không chứng minh pager hoạt động) |
| Quy trình on-call | 1,5 | Lịch, người dự phòng, leo thang có số phút, bàn giao có nội dung cụ thể, chế độ bù cho người trực |
| Đo chất lượng | 1 | Có chỉ số đo được (page/tuần, tỉ lệ actionable, alert bỏ sót) và nhịp xem lại, kèm hành động khi chỉ số xấu |
| Nhận biết giới hạn | 1 | Nêu được ít nhất ba điểm yếu thật (ngưỡng cố định khi ít traffic, rule không khớp dữ liệu, điểm lỗi đơn ở pager...) và hướng xử lý |

Trừ điểm khi: page theo CPU/RAM/đĩa mà không có lý do; tài liệu và `alertmanager.yml` nói hai điều khác nhau; "ai thấy thì xử lý" thay cho
lịch trực; không có cách biết hệ thống alert đã chết.

## Câu hỏi để tự kiểm

- Đêm nay có bao nhiêu khả năng bị đánh thức vì một thứ không cần làm gì? Nhìn danh mục: alert page nào có thể bắn khi khách không bị gì?
- Alertmanager chết thì ai biết? Với lời giải mẫu: dịch vụ heartbeat ngừng nhận ping, sau 5 phút nó page qua kênh riêng.
- Team khác thêm alert quên `severity`: rơi về `default`, có người xem mỗi sáng. Tốt hơn nữa: `promtool check rules` trong CI kèm kiểm có
  nhãn `severity` và `runbook_url`.
