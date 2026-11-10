# Lời giải: từ log tới trace bằng LogQL

```yaml
request_logs: '{service_name="olist-shop-api"} | json | request_id = "$request_id"'
trace_id_of_request: '{service_name="olist-shop-api"} | json | request_id = "$request_id" and msg = "request" | line_format "{{.trace_id}}"'
worker_logs_of_trace: '{service_name="olist-shop-worker"} | trace_id = "$trace_id"'
errors_by_path: 'sum by (path) (count_over_time({service_name="olist-shop-api"} | json | msg = "request" and status >= 500 [5m]))'
```

## Vì sao

- **`request_logs`**: `|= "chk-7"` là so chuỗi con, khớp cả `chk-77` và `chk-7b`. Parser `json` tách `request_id` thành label, rồi
  `request_id = "..."` so đúng giá trị. Muốn nhanh hơn trên khối log lớn: thêm line filter trước parser,
  `|= "$request_id" | json | request_id = "$request_id"`; line filter loại phần lớn dòng mà không phải parse.
- **`trace_id_of_request`**: `line_format "{{.trace_id}}"` viết lại dòng thành đúng một trường. `msg = "request"` giữ một dòng mỗi request
  (`POST /jobs/recompute` còn dòng `job enqueued` cùng trace). `trace_id` ở đây đọc từ structured metadata (Loki gắn khi nhận log OTLP);
  parser `json` cũng tách được nhưng vì tên trùng, label từ JSON thành `trace_id_extracted`.
- **`worker_logs_of_trace`**: lọc thẳng trên structured metadata, không cần parser: rẻ hơn `| json | trace_id = ...`. `request_id` không
  dùng được vì worker đặt nó là `job_id`: request id là khái niệm của HTTP, còn trace context (W3C `traceparent`) đi theo message qua
  Redis nhờ code app ghi nó vào payload job.
- **`errors_by_path`**: `count_over_time(... [5m])` biến log thành chuỗi số. `sum by (path)` gộp mọi stream (mỗi instance là một stream)
  và chỉ giữ `path`. `status >= 500` so số dù giá trị trong log là số hay chuỗi.

## Trong Grafana

Datasource Loki của stack có derived field `trace_id`: trong Explore hay panel log, mở một dòng log rồi bấm link ở trường `trace_id` để
nhảy sang trace trong Jaeger. Chiều ngược lại (từ span sang log) cấu hình bằng "trace to logs" ở datasource Jaeger, dùng query giống
`worker_logs_of_trace`.

## Khi nào metric từ log là đúng chỗ

`errors_by_path` hữu ích khi app không có metric (hệ thống cũ, log của nginx). Khi đã có `http_requests_total`, alert nên dựa trên metric:
rẻ hơn, giữ lâu hơn, không phụ thuộc mức log hay sampling log. Loki ruler chạy được alert trên LogQL, dùng cho các mẫu chỉ log mới có
(stack trace lạ, lỗi xác thực).
