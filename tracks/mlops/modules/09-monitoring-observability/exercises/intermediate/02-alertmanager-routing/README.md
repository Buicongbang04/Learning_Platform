---
title: Alertmanager - routing theo severity và inhibit
level: intermediate
services: []
files:
  - path: starter/alertmanager.yml
    note: Cấu hình Alertmanager, chỉ có receiver default
  - path: tests/test_routing.py
    note: Không sửa
  - path: quiz.yaml
    note: Câu hỏi ôn về alert, cardinality và histogram
run:
  - uv run pytest tracks/mlops/modules/09-monitoring-observability/exercises/intermediate/02-alertmanager-routing -q
---

## Mục tiêu

Alert đúng mà đến sai người thì cũng như không có alert. Bài này viết cấu hình Alertmanager để cảnh báo `critical` đánh thức
người trực, `warning` chỉ mở ticket, và một sự cố lớn không kéo theo cả chục thông báo phụ.

## Đề bài

Viết `starter/alertmanager.yml`. Test chạy `amtool` thật (image `prom/alertmanager`, qua `mlopskit.amtool`, không cần stack): `amtool check-config` kiểm cấu hình hợp lệ và `amtool config routes test` cho biết cảnh báo với tập nhãn cho trước đi tới receiver nào. `amtool` không mô phỏng được `inhibit_rules`, nên phần inhibit chỉ kiểm hình dạng của luật trong YAML.

Luật mà test kiểm:

- Có ba receiver `default`, `oncall`, `ticket`, tên không trùng. Route gốc có `receiver: default`. Dùng `matchers`
  (cú pháp `severity="critical"`); không dùng `match`/`match_re` đã cũ. Mọi receiver nhắc tới phải tồn tại.
- Cảnh báo `severity="critical"` (có hay không có nhãn khác như `team`) đi tới **đúng một** receiver: `oncall`.
  `severity="warning"` đi tới đúng một receiver: `ticket`. Mọi thứ khác (`info`, thiếu nhãn `severity`, viết sai hoa thường
  như `Critical`) rơi về `default`, không bị bỏ rơi.
- Route gốc `group_by` chứa `alertname` và `service`; route con nếu đặt `group_by` riêng thì vẫn chứa `alertname`.
- Route critical: `group_wait` tối đa 30s, `repeat_interval` tối đa 4h. Route warning: `group_wait` từ 1m, `repeat_interval` từ
  12h. Cả hai route có `group_interval` từ 1m và `repeat_interval` không nhỏ hơn `group_interval`. Thời lượng viết dạng `30s`, `5m`, `4h`.
- `oncall` và `ticket` mỗi receiver có ít nhất một `webhook_configs` với `url` bắt đầu `http://` hoặc `https://`; webhook của
  `oncall` có `send_resolved: true`.
- Có `inhibit_rules`, mỗi luật phải có `equal`; có ít nhất một luật với nguồn `severity="critical"`, đích `severity="warning"` và `equal` chứa `service` (critical của một service chỉ im warning của đúng service đó).
- `amtool check-config` báo thành công.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/09-monitoring-observability/exercises/intermediate/02-alertmanager-routing -q` pass.
- Hoàn thành `quiz.yaml` (trả lời từ trang bài tập trong ứng dụng; đáp án nằm ở `solutions/`).
- Bạn nêu được chuyện gì xảy ra nếu bỏ `equal` khỏi luật inhibit, và vì sao `group_wait` của critical ngắn còn của warning dài.

## Gợi ý

### Gợi ý 1

Route con khớp đầu tiên thắng, nên hai route `critical` và `warning` loại trừ nhau và thứ tự không quan trọng; nhưng nếu
bạn thêm `continue: true` vào route critical thì cảnh báo sẽ đi tiếp và có thể trúng cả route warning khác. Test đòi đúng một receiver.

### Gợi ý 2

`group_wait` là thời gian chờ gom các cảnh báo cùng nhóm trước lần gửi đầu tiên: ngắn thì người trực biết sớm, dài thì gom
được nhiều cảnh báo vào một ticket. Chọn theo việc người nhận có cần phản ứng ngay hay không.
