# Lời giải: Alertmanager routing và inhibit

## Ý chính

- **Cây route.** Gốc là mặc định (`default`, bắt mọi thứ không khớp), hai route con loại trừ nhau theo `severity`. Cảnh báo
  thiếu nhãn `severity` không được biến mất: nó rơi về `default`, nơi ai đó nên đọc và sửa rule thiếu nhãn.
- **Thời gian theo mức độ khẩn.** Critical: `group_wait: 10s` (người trực cần biết ngay), `repeat_interval: 1h` (nhắc lại cho
  tới khi xử lý). Warning: `group_wait: 5m` gom nhiều cảnh báo vào một ticket, `repeat_interval: 24h` để ticket không bị
  spam.
- **Inhibit có `equal`.** Khi `ETAHighErrorRate` (critical) đang bắn thì `ETAHighLatency` (warning) cùng service chỉ là hệ quả,
  im nó. `equal: ["service"]` giới hạn việc im trong đúng service; bỏ `equal` thì một critical của bất kỳ service nào làm im mọi
  warning của mọi service, và bạn sẽ không thấy warning thật của team khác đúng lúc hệ thống đang yếu nhất.
- **Đánh đổi của inhibit.** `ETAMetricsAbsent` là warning nên cũng bị im khi cùng service có critical; chấp nhận được vì người
  trực đã đang xử lý service đó, nhưng hãy viết ra để mọi người biết.
- **`send_resolved`.** Oncall cần biết khi sự cố tự hết để khỏi chờ vô ích; ticket thì không cần thông báo "đã hết".
- **Vì sao mô phỏng.** Ngữ nghĩa route đủ nhỏ để một bộ mô phỏng 30 dòng kiểm được; kiểm bằng Alertmanager thật cần dựng
  tiến trình và gửi alert qua API, chậm và dễ flake. `amtool check-config` và `amtool config routes test --config.file=...
  severity=critical` là cách làm thật ngoài đời; chạy chúng trong container của stack để đối chiếu.

## Lỗi hay gặp

- `matchers` sai cú pháp (`severity=critical` không có dấu nháy vẫn được ở bản mới, nhưng giá trị có dấu cách hay ký tự đặc
  biệt thì cần nháy); luôn dùng dạng có nháy.
- `continue: true` thêm "cho chắc" làm một cảnh báo gửi hai nơi (đánh thức người trực và mở ticket), tăng nhiễu.
- `group_by: [...]` thiếu `alertname` gom mọi cảnh báo khác nhau vào một thông báo.
- Không test route: một dấu cách trong nhãn đủ làm critical rơi về `default` và không ai được đánh thức.
