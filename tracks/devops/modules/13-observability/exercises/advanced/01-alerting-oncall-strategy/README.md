---
title: Thiết kế chiến lược alert và on-call cho Olist Shop
level: advanced
services: []
files:
  - path: starter/ALERTING.md
    note: Tài liệu thiết kế, 6 phần
  - path: starter/alertmanager.yml
    note: Routing, inhibition, receiver
  - path: tests/test_alerting.py
    note: Kiểm khung tài liệu, đối chiếu bảng với amtool, inhibition trên Alertmanager thật; không sửa
  - path: tests/fixtures/ALERTING.good.md
    note: Ví dụ đạt (hệ thống khác)
run:
  - uv run pytest tracks/devops/modules/13-observability/exercises/advanced/01-alerting-oncall-strategy -q -rs
---

## Mục tiêu

Thiết kế bộ alert và quy trình trực cho Olist Shop như một tech lead: alert nào page, alert nào chỉ là ticket, gộp và chặn thông báo thế
nào để một sự cố không thành hai mươi tin nhắn, ai trực, leo thang ra sao, và đo xem bộ alert có tốt lên không. Tài liệu và cấu hình
Alertmanager phải nói cùng một điều.

## Đề bài

Bối cảnh: Olist Shop có API, worker, Postgres, Redis (metric như các bài trước: `http_requests_total`, `http_request_duration_seconds`,
`jobs_enqueued_total`, `jobs_processed_total`, `jobs_failed_total`, `up`). Team 6 kỹ sư ở một múi giờ, khách đặt hàng cả ngày lẫn đêm.
Hiện tại mọi alert vào một kênh chat, người trực bỏ qua kênh đó vì mỗi đêm có vài chục tin. Tháng trước API trả lỗi 40 phút mà không ai
biết. SLO và burn-rate để dành cho module 16; ở đây dùng ngưỡng và `for`.

**1. `starter/ALERTING.md`**, giữ sáu tiêu đề `## 1.` tới `## 6.`:

| Phần | Nội dung | Test kiểm |
| --- | --- | --- |
| 1. Nguyên tắc | Bối cảnh, nguyên tắc chọn alert | ≥3 gạch đầu dòng; nhắc triệu chứng/symptom và hành động/actionable/runbook |
| 2. Danh mục alert | Bảng cột `Alert`, `Service`, `Tín hiệu`, `Severity`, `Receiver`, `Runbook` | ≥6 dòng, tên không trùng; severity chỉ `page`, `ticket`, `none`; ≥2 page, ≥2 ticket; page và ticket có runbook `https://`; alert page không dựa trên CPU, RAM, đĩa, `node_`; có `Watchdog` (`none`, Service `-`) và `OlistServiceDown` (`page`) |
| 3. Routing, grouping, inhibition | Cách gộp, định tuyến, chặn | ≥3 gạch đầu dòng; nhắc group_by/gộp, inhibit, Watchdog/deadman |
| 4. On-call | Lịch, leo thang, bàn giao | ≥4 gạch đầu dòng; nhắc leo thang/escalation, bàn giao/handoff, lịch/rotation/luân phiên |
| 5. Đo chất lượng alert | Chỉ số và nhịp xem lại | ≥3 gạch đầu dòng; nhắc page, tuần/tháng, actionable/nhiễu |
| 6. Rủi ro và giới hạn | Điều thiết kế này chưa giải quyết | ≥3 gạch đầu dòng |

**2. `starter/alertmanager.yml`**:

- `amtool check-config` qua.
- Với mỗi dòng trong bảng phần 2, `amtool config routes test` với nhãn `alertname`, `severity` và `service` (khi cột Service khác `-`)
  ra **đúng** receiver ghi trong bảng. Receiver đó có ít nhất một `*_configs` (webhook giả là đủ).
- Alert có nhãn lạ (thiếu `severity`, hay `severity="Page"` viết hoa) không đi tới receiver page nào.
- Inhibition, kiểm trên một Alertmanager thật (test gửi alert giả qua API rồi đọc `status.inhibitedBy`): khi `OlistServiceDown` đang bắn
  cho một service, mọi alert khác của cùng service bị chặn; alert của service khác vẫn đi; `OlistServiceDown` không tự chặn mình.

Test còn chạy bộ kiểm tài liệu trên ba fixture (khung, bản yếu, bản đạt của hệ thống khác) để chứng minh bắt được lỗi. Rubric trong
`SOLUTION.md` chấm nội dung. `amtool` chạy trong container image `prom/alertmanager` ghim (không cần cài); Alertmanager thật chạy trong
`DockerLab`, khoảng 10 giây.

## Tiêu chí đạt

- Test pass.
- Rubric trong `SOLUTION.md` đạt từ 7/10.
- Trả lời được: "Đêm nay có bao nhiêu khả năng bạn bị đánh thức vì một thứ không cần làm gì?", "Nếu Alertmanager chết thì ai biết?",
  "Một alert mới do team khác thêm, quên nhãn `severity`, sẽ đi đâu?".

## Gợi ý

### Gợi ý 1

Viết bảng trước, cấu hình sau. Với mỗi dòng hỏi: khách có thấy không, người trực làm gì trong 5 phút đầu, chờ tới sáng có sao không. Trả
lời "không làm gì" thì không phải page.

### Gợi ý 2

Route con khớp theo `matchers: [severity="page"]`; route gốc là chỗ rơi về cho mọi thứ không khớp. Inhibit cần ba phần: `source_matchers`,
`target_matchers` và `equal`. Thử bằng tay: chạy Alertmanager theo `setup/DEVOPS-TOOLS.md`, gửi alert bằng
`amtool alert add alertname=OlistServiceDown service=olist-api --alertmanager.url=http://127.0.0.1:19093`, rồi `amtool alert query -i`.
