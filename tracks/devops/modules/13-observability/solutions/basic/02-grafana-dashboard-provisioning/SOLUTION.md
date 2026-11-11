# Lời giải: dashboard RED provision từ Git

## Provider

```yaml
providers:
  - name: olist
    folder: Olist Shop
    folderUid: olist-shop
    type: file
    disableDeletion: true
    allowUiUpdates: false
    updateIntervalSeconds: 30
    options:
      path: /etc/grafana/dashboards
```

- Provider `file` quét thư mục mỗi `updateIntervalSeconds` giây, tạo hay cập nhật dashboard theo `uid`. Đổi JSON trong Git, deploy lại
  thư mục, Grafana tự nạp.
- `allowUiUpdates: false`: ai sửa trên UI cũng không lưu được, nên không có thay đổi nào sống ngoài Git rồi bị ghi đè lần provision sau.
  `disableDeletion: true`: xoá trên UI không được; muốn xoá thì xoá tệp.
- `folderUid` cố định giúp link và quyền theo folder không đổi khi dựng lại Grafana.
- Tệp này **thay** provider mặc định của stack, nên dashboard `devops-obs-stack` có sẵn cũng vào folder `Olist Shop`. Muốn giữ riêng thì
  khai hai provider trỏ hai thư mục con khác nhau; không để hai provider cùng quét một thư mục, Grafana sẽ báo trùng `uid`.

## Dashboard

Năm panel, đúng RED cộng worker và log:

| Panel | Query |
| --- | --- |
| Rate | `sum by (path) (rate(http_requests_total{job="olist-api"}[$__rate_interval]))` |
| Errors | `sum(rate(...{status=~"5.."}[$__rate_interval])) / sum(rate(...[$__rate_interval]))`, unit `percentunit` |
| Duration | `histogram_quantile(0.95, sum by (path, le) (rate(http_request_duration_seconds_bucket{job="olist-api"}[$__rate_interval])))`, unit `s` |
| Worker | `sum(rate(jobs_processed_total{job="olist-worker"}[$__rate_interval])) * 60` và tương tự cho `jobs_failed_total` |
| Log lỗi | `{service_name="olist-shop-api"} \| json \| status >= 500`, panel `logs` |

Quyết định đáng chú ý:

- **Datasource theo uid đã provision.** JSON export từ UI để "chia sẻ ra ngoài" chứa `${DS_PROMETHEUS}`; placeholder đó chỉ được thay khi
  import bằng tay, provisioning để nguyên nên panel báo "datasource not found". Stack này cố định `uid: prometheus` nên ghi thẳng. Khi một
  dashboard phải chạy trên nhiều Grafana có uid khác nhau, dùng biến kiểu `datasource` (cách track MLOps làm).
- **`$__rate_interval`**: Grafana tính bằng `max(4 × scrape interval, $__interval + scrape interval)`. Zoom ra 7 ngày thì cửa sổ lớn lên
  theo bước vẽ, không bỏ sót mẫu; zoom vào thì không nhỏ hơn 4 lần scrape, nên `rate` luôn có đủ điểm. `[5m]` ghi cứng làm đồ thị 7 ngày
  chỉ lấy mẫu 5 phút mỗi bước (răng cưa, mất đỉnh) và đồ thị 1 phút trống.
- **Counter không vẽ thô**: một đường tăng mãi không cho biết gì, và tụt về 0 mỗi lần restart.
- **Panel log lọc theo trường của JSON**, không theo chuỗi (`|= "503"` khớp cả `duration_ms` có chữ số 503). Log của API có `trace_id`, và
  datasource Loki đã khai derived field, nên trong panel log bấm vào `trace_id` sẽ mở trace trong Jaeger.
- `editable: false` trong JSON nhắc người xem đây là dashboard từ Git.

## Dashboard tốt khác dashboard nhiều panel

- Hàng trên trả lời "người dùng có ổn không" (RED), hàng dưới mới tới nguyên nhân (worker, log). Người trực mở dashboard lúc 3 giờ sáng
  đọc từ trên xuống.
- Mỗi panel có đơn vị (`reqps`, `percentunit`, `s`) để không ai đọc nhầm 0.05 là 0.05 giây.
- Test kiểm mọi query trả dữ liệu thật vì lỗi phổ biến nhất của dashboard là panel "No data" do sai tên metric hay label, chỉ lộ ra khi
  sự cố xảy ra.
