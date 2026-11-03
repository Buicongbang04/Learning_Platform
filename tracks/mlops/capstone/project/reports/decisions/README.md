# Quyết định sau phát lại (M10)

Mỗi tệp `<YYYY-MM>.yaml` ở đây là một quyết định cho tháng đó, viết sau khi chạy `eta.cli replay` và đọc
`reports/replay/summary.parquet`. Cần `2020-03.yaml` và ít nhất một tháng khác. Mẫu (thay số bằng số đo của bạn):

```yaml
decision: keep
reasons:
  - "Câu thứ nhất, có số liệu từ summary.parquet"
  - "Câu thứ hai, có số liệu"
evidence:
  psi_trip_distance: 0.0
  mae_before: 0.0
  mae_after: 0.0
  as_of: "YYYY-MM"
```

Luật đầy đủ ở [M10](../../../milestones/m10-drift-replay.md).
