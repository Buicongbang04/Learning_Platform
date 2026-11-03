# Monitoring của M09

Các tệp bạn viết ở [M09](../../milestones/m09-monitoring.md):

- `prometheus.yml`: scrape job `eta-api`, nạp `rules/eta.rules.yml`.
- `rules/eta.rules.yml`: bốn alert `EtaHighErrorRate`, `EtaHighLatencyP95`, `EtaMetricsAbsent`, `EtaPredictionShift`.
- `rules/eta.rules.test.yml`: test cho `promtool test rules`, có ca không traffic.
- `grafana/dashboards/eta.json`: dashboard RED, phân phối dự đoán và version đang chạy.
