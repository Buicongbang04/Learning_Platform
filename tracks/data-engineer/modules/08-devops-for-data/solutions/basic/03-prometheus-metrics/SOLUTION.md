# Lời giải: metric Prometheus

## Cách làm

- **Escape**: thay `\` trước, sau đó `"` và `\n`. Nếu escape `"` trước thành `\"` rồi mới thay `\`,
  dấu `\` vừa thêm bị nhân đôi thành `\\"` và sai.
- **Render**: lặp theo family bên ngoài, theo pipeline bên trong, để HELP/TYPE xuất hiện đúng một
  lần và đứng trước mọi mẫu của family đó (chuẩn exposition yêu cầu các mẫu của một family nằm
  liền nhau). Counter có hậu tố `_total`, đơn vị nằm trong tên (`_seconds`) theo naming convention.
- **Freshness**: `now - last_success`, đổi `datetime` sang Unix seconds bằng `.timestamp()`, chặn
  dưới bằng 0. `None` trả `inf` để cảnh báo "chưa bao giờ thành công" luôn bắn.

## Trong thực tế

Dùng thư viện `prometheus_client` thay vì tự render:

```python
from prometheus_client import CollectorRegistry, Counter, Gauge, push_to_gateway

reg = CollectorRegistry()
rows = Counter("pipeline_rows_processed", "Rows processed by the pipeline.", ["pipeline"], registry=reg)
last_ok = Gauge("pipeline_last_success_timestamp_seconds", "Unix time of the last successful run.",
                ["pipeline"], registry=reg)
rows.labels("orders").inc(98666)
last_ok.labels("orders").set_to_current_time()
push_to_gateway("localhost:9091", job="olist_orders", registry=reg)
```

Cảnh báo freshness tính ở phía Prometheus:
`time() - pipeline_last_success_timestamp_seconds > 7200`.
